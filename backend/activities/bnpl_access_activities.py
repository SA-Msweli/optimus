"""BNPL Access Activities - Atomic operations for BNPL access workflow"""

from temporalio import activity
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from database.database import SessionLocal
from database.models import User, DAOMetadata, BNPLAccess, VotingPeriod
from backend.services.bnpl.bnpl_access_service import BNPLAccessService
from services.voting_period_service import VotingPeriodService
from datetime import datetime, timezone, timedelta
import logging
import uuid

logger = logging.getLogger(__name__)


@activity.defn
async def validate_bnpl_application(user_id: str, dao_ids: List[str]) -> Dict[str, Any]:
    """
    Validate BNPL application
    
    Checks:
    - User exists
    - All DAOs exist and have BNPL goal
    - DAOs have payment terms configured
    """
    logger.info(f"Validating BNPL application for user {user_id}")
    
    db = SessionLocal()
    try:
        # Check user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check all DAOs exist and have BNPL goal
        valid_daos = []
        invalid_daos = []
        
        for dao_id in dao_ids:
            dao = db.query(DAOMetadata).filter(
                DAOMetadata.dao_id == dao_id,
                DAOMetadata.goal == "BNPL"
            ).first()
            
            if not dao:
                invalid_daos.append(dao_id)
                continue
            
            # Check DAO has payment terms configured
            # type: ignore - SQLAlchemy Column comparison
            if dao.bnpl_payment_period_days is None or dao.bnpl_num_installments is None:
                invalid_daos.append(dao_id)
                logger.warning(f"DAO {dao_id} missing BNPL payment terms")
                continue
            
            valid_daos.append(dao_id)
        
        if invalid_daos:
            raise ValueError(f"Invalid or unconfigured DAOs: {invalid_daos}")
        
        logger.info(f"Validation successful for {len(valid_daos)} DAOs")
        
        return {
            "valid": True,
            "user_id": user_id,
            "valid_daos": valid_daos,
        }
        
    finally:
        db.close()


@activity.defn
async def check_dao_membership(user_id: str, dao_ids: List[str]) -> Dict[str, Any]:
    """
    Check if user is a member of any selected DAOs
    
    Users cannot apply for BNPL access to DAOs they're members of
    
    Checks on-chain DAO membership via Movement Network
    """
    logger.info(f"Checking DAO membership for user {user_id}")
    
    db = SessionLocal()
    try:
        # Get user's wallet address
        from database.models import Wallet
        from services.movement_service import MovementService
        
        wallet = db.query(Wallet).filter_by(user_id=user_id).first()
        if not wallet:
            raise ValueError(f"No wallet found for user {user_id}")
        
        user_address = wallet.address
        member_of_daos = []
        movement_service = MovementService()
        
        # Check each DAO for membership by querying on-chain resources
        for dao_id in dao_ids:
            try:
                # Get user's account resources to check for DAO membership
                resources = await movement_service.get_account_resources(user_address)
                
                # Check if user has a MemberResource for this DAO
                # Format: {dao_address}::dao::MemberResource
                member_resource_type = f"{dao_id}::dao::MemberResource"
                
                is_member = any(
                    resource.get("type", "").startswith(member_resource_type)
                    for resource in resources.get("resources", [])
                )
                
                logger.info(f"User {user_address} membership in DAO {dao_id}: {is_member}")
                
                if is_member:
                    member_of_daos.append(dao_id)
                    
            except Exception as e:
                logger.warning(f"Failed to check membership for DAO {dao_id}: {str(e)}")
                # If we can't verify, assume not a member (fail open for availability)
                continue
        
        if member_of_daos:
            raise ValueError(
                f"User {user_id} is a member of DAOs: {member_of_daos}. "
                "Cannot apply for BNPL access to own DAOs."
            )
        
        logger.info(f"User {user_id} is not a member of any selected DAOs")
        
        return {
            "is_member": False,
            "member_of_daos": [],
            "user_address": user_address,
        }
        
    finally:
        db.close()


@activity.defn
async def create_bnpl_applications(user_id: str, dao_ids: List[str]) -> Dict[str, Any]:
    """Create BNPL access applications for user to specified DAOs"""
    logger.info(f"Creating BNPL applications for user {user_id}")
    
    db = SessionLocal()
    try:
        service = BNPLAccessService(db=db)
        applications = service.apply_for_bnpl_access(user_id, dao_ids)
        
        application_ids = [app.id for app in applications]
        
        logger.info(f"Created {len(application_ids)} BNPL applications")
        
        return {
            "application_ids": application_ids,
            "user_id": user_id,
            "dao_ids": dao_ids,
        }
        
    finally:
        db.close()


@activity.defn
async def open_voting_for_application(application_id: str, dao_id: str) -> Dict[str, Any]:
    """
    Open voting period for BNPL access application
    
    DAO members vote on whether to approve user for BNPL access
    """
    logger.info(f"Opening voting for application {application_id} in DAO {dao_id}")
    
    db = SessionLocal()
    try:
        # Get DAO metadata to determine voting duration
        dao = db.query(DAOMetadata).filter(DAOMetadata.dao_id == dao_id).first()
        if not dao:
            raise ValueError(f"DAO {dao_id} not found")
        
        # Create voting period
        # Note: This assumes DAOs have a voting_period_days configured
        # For BNPL applications, we might want a shorter voting period
        voting_duration_days = 3  # Default 3 days for BNPL applications
        
        now = datetime.now(timezone.utc)
        voting_period = VotingPeriod(
            id=str(uuid.uuid4()),
            dao_id=dao_id,
            proposal_id=f"bnpl_access_{application_id}",
            status="Active",
            started_at=now,
            expires_at=now + timedelta(days=voting_duration_days),
            created_at=now,
            updated_at=now,
        )
        
        db.add(voting_period)
        db.commit()
        
        logger.info(f"Voting period {voting_period.id} created for application {application_id}")
        
        return {
            "voting_period_id": voting_period.id,
            "proposal_id": voting_period.proposal_id,
            "expires_at": voting_period.expires_at.isoformat(),
            "voting_duration_seconds": voting_duration_days * 24 * 60 * 60,
        }
        
    finally:
        db.close()


@activity.defn
async def count_application_votes(voting_period_id: str) -> Dict[str, Any]:
    """
    Count votes for BNPL access application
    
    Determines if application is approved based on supermajority (>50%)
    """
    logger.info(f"Counting votes for voting period {voting_period_id}")
    
    db = SessionLocal()
    try:
        service = VotingPeriodService(db=db)
        
        # Get voting period
        voting_period = db.query(VotingPeriod).filter(VotingPeriod.id == voting_period_id).first()
        if not voting_period:
            raise ValueError(f"Voting period {voting_period_id} not found")
        
        # Count votes
        yes_votes = voting_period.yes_votes or 0
        no_votes = voting_period.no_votes or 0
        total_votes = int(yes_votes) + int(no_votes)
        
        # Determine if approved (supermajority > 50%)
        approved = False
        if total_votes > 0:
            yes_percentage = (int(yes_votes) / total_votes) * 100
            approved = yes_percentage > 50
        
        logger.info(f"Vote count: {yes_votes} yes, {no_votes} no, approved: {approved}")
        
        return {
            "yes_votes": yes_votes,
            "no_votes": no_votes,
            "total_votes": total_votes,
            "approved": approved,
        }
        
    finally:
        db.close()


@activity.defn
async def finalize_application_status(application_id: str, approved: bool) -> Dict[str, Any]:
    """
    Finalize BNPL access application status based on voting result
    """
    logger.info(f"Finalizing application {application_id}, approved: {approved}")
    
    db = SessionLocal()
    try:
        service = BNPLAccessService(db=db)
        
        if approved:
            _ = service.approve_application(application_id)
            status = "Approved"
        else:
            _ = service.reject_application(application_id)
            status = "Rejected"
        
        logger.info(f"Application {application_id} finalized as {status}")
        
        return {
            "application_id": application_id,
            "status": status,
            "finalized_at": datetime.now(timezone.utc).isoformat(),
        }
        
    finally:
        db.close()
