"""Loan-related activities"""

from temporalio import activity
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import VotingPeriod, VotingRecord, Loan
from services.loan_service import LoanService
from services.voting_period_service import VotingPeriodService
from services.movement_service import MovementService
from services.repayment_schedule_service import RepaymentScheduleService
from datetime import datetime, timezone, timedelta
import logging
import uuid

logger = logging.getLogger(__name__)


@activity.defn
async def open_voting(dao_id: str, loan_id: str) -> dict:
    """Open voting on loan request
    
    Args:
        dao_id: On-chain DAO address
        loan_id: Loan ID
        
    Returns:
        Voting period details
    """
    db = SessionLocal()
    try:
        # Create voting period
        proposal_id = str(uuid.uuid4())
        voting_period = VotingPeriodService.create_voting_period(
            db=db,
            dao_id=dao_id,
            proposal_id=proposal_id,
            duration_days=7,
        )

        logger.info(
            f"Opened voting for loan {loan_id} in DAO {dao_id}, proposal {proposal_id}"
        )

        return {
            "proposal_id": proposal_id,
            "voting_period_id": voting_period.id,
            "voting_opened": True,
            "expires_at": voting_period.expires_at.isoformat(),
        }

    finally:
        db.close()


@activity.defn
async def count_votes(dao_id: str, proposal_id: str) -> dict:
    """Count votes and determine supermajority
    
    Args:
        dao_id: On-chain DAO address
        proposal_id: Proposal ID
        
    Returns:
        Vote count and supermajority status
    """
    db = SessionLocal()
    try:
        # Get voting period
        voting_period = VotingPeriodService.get_voting_period_by_proposal(
            db, dao_id, proposal_id
        )
        if not voting_period:
            raise ValueError(f"Voting period not found for proposal {proposal_id}")

        # Count votes
        yes_votes = (
            db.query(VotingRecord)
            .filter(
                VotingRecord.dao_id == dao_id,
                VotingRecord.proposal_id == proposal_id,
                VotingRecord.vote == True,
            )
            .count()
        )

        no_votes = (
            db.query(VotingRecord)
            .filter(
                VotingRecord.dao_id == dao_id,
                VotingRecord.proposal_id == proposal_id,
                VotingRecord.vote == False,
            )
            .count()
        )

        total_votes = yes_votes + no_votes
        supermajority_reached = yes_votes > total_votes / 2 if total_votes > 0 else False

        logger.info(
            f"Vote count for proposal {proposal_id}: yes={yes_votes}, no={no_votes}, supermajority={supermajority_reached}"
        )

        return {
            "proposal_id": proposal_id,
            "yes_votes": yes_votes,
            "no_votes": no_votes,
            "total_votes": total_votes,
            "supermajority_reached": supermajority_reached,
        }

    finally:
        db.close()


@activity.defn
async def disburse_funds(
    loan_id: str, borrower_address: str, amount: int, dao_id: str
) -> str:
    """Disburse loan funds to borrower via Movement Network
    
    Args:
        loan_id: Loan ID
        borrower_address: Borrower wallet address
        amount: Amount in tokens
        dao_id: DAO address (treasury source)
        
    Returns:
        Transaction hash
    """
    db = SessionLocal()
    try:
        # Call Movement Network to transfer funds
        movement_service = MovementService()
        tx_hash = await movement_service.transfer_funds(
            from_address=dao_id,
            to_address=borrower_address,
            amount=amount,
        )

        # Mark loan as disbursed
        LoanService.disburse_loan(db, loan_id)

        logger.info(f"Disbursed loan {loan_id}: {amount} tokens to {borrower_address}")

        return tx_hash

    finally:
        db.close()


@activity.defn
async def reject_loan_and_update_risk(
    loan_id: str, borrower_id: str
) -> dict:
    """Reject loan and update borrower risk profile
    
    Args:
        loan_id: Loan ID
        borrower_id: Borrower user ID
        
    Returns:
        Updated loan and risk profile
    """
    db = SessionLocal()
    try:
        # Reject loan
        loan = LoanService.reject_loan(db, loan_id, borrower_id)

        # Risk profile update already done in reject_loan
        logger.info(f"Rejected loan {loan_id} and updated risk profile")

        return {
            "loan_id": loan.id,
            "status": loan.status,
            "updated_at": loan.created_at.isoformat(),
        }

    finally:
        db.close()


@activity.defn
async def approve_loan_on_chain(
    loan_id: str, dao_id: str, borrower_address: str, amount: int
) -> str:
    """Approve loan on-chain via Lending contract
    
    Args:
        loan_id: Loan ID
        dao_id: DAO address
        borrower_address: Borrower wallet address
        amount: Loan amount
        
    Returns:
        Transaction hash
    """
    db = SessionLocal()
    try:
        # Get loan to access interest rate and duration
        loan = LoanService.get_loan(db, loan_id)
        if not loan:
            raise ValueError(f"Loan {loan_id} not found")

        # Call Movement Network to approve loan on-chain
        movement_service = MovementService()
        tx_hash = await movement_service.call_contract(
            contract_address=dao_id,
            function_name="approve_loan",
            args=[borrower_address, amount],
        )

        # Mark loan as approved
        LoanService.approve_loan(db, loan_id)

        # Create repayment schedule (12 monthly payments)
        RepaymentScheduleService.create_repayment_schedule(
            db=db,
            loan_id=loan_id,
            principal=loan.amount,
            interest_rate=loan.interest_rate,
            duration_seconds=loan.duration_seconds,
            num_payments=12,
        )

        logger.info(f"Approved loan {loan_id} on-chain and created repayment schedule")

        return tx_hash

    finally:
        db.close()


@activity.defn
async def distribute_loan_interest(
    loan_id: str, dao_id: str, member_addresses: list[str], member_investments: list[int]
) -> dict:
    """Distribute loan interest to DAO members proportionally
    
    Args:
        loan_id: Loan ID
        dao_id: DAO address
        member_addresses: List of member wallet addresses
        member_investments: List of member investment amounts (corresponding to addresses)
        
    Returns:
        Distribution details with transaction hashes
    """
    db = SessionLocal()
    try:
        from services.interest_distribution_service import InterestDistributionService
        
        # Calculate total interest earned
        total_interest = InterestDistributionService.calculate_total_interest(db, loan_id)
        
        if total_interest == 0:
            logger.info(f"No interest to distribute for loan {loan_id}")
            return {
                "loan_id": loan_id,
                "total_interest": 0,
                "distributions": [],
                "transaction_hashes": [],
            }
        
        # Calculate total investment
        total_investment = sum(member_investments)
        if total_investment == 0:
            raise ValueError("Total investment is zero, cannot distribute interest")
        
        # Calculate distributions for each member
        distributions = {}
        transaction_hashes = []
        
        for member_address, member_investment in zip(member_addresses, member_investments):
            # Calculate voting power percentage
            voting_power_pct = InterestDistributionService.get_member_voting_power_percentage(
                member_investment, total_investment
            )
            
            # Calculate member's interest share
            member_share = InterestDistributionService.calculate_member_interest_share(
                voting_power_pct, total_interest
            )
            
            if member_share > 0:
                distributions[member_address] = member_share
                
                # Transfer interest to member via Movement Network
                movement_service = MovementService()
                tx_hash = await movement_service.transfer_funds(
                    from_address=dao_id,
                    to_address=member_address,
                    amount=member_share,
                )
                
                transaction_hashes.append(tx_hash)
                
                # Record distribution
                InterestDistributionService.record_interest_distribution(
                    db=db,
                    loan_id=loan_id,
                    dao_id=dao_id,
                    member_address=member_address,
                    distribution_amount=member_share,
                )
                
                logger.info(
                    f"Distributed {member_share} tokens to {member_address} "
                    f"(voting power: {voting_power_pct}%)"
                )
        
        # Validate distribution sum
        if not InterestDistributionService.validate_distribution_sum(
            distributions, total_interest
        ):
            logger.warning(
                f"Distribution sum validation failed for loan {loan_id}, "
                f"but continuing with distribution"
            )
        
        logger.info(
            f"Completed interest distribution for loan {loan_id}: "
            f"total_interest={total_interest}, members={len(distributions)}"
        )
        
        return {
            "loan_id": loan_id,
            "dao_id": dao_id,
            "total_interest": total_interest,
            "distributions": distributions,
            "transaction_hashes": transaction_hashes,
            "members_paid": len(distributions),
        }

    finally:
        db.close()



@activity.defn
async def dissolve_dao_on_chain(dao_id: str) -> str:
    """Dissolve DAO on-chain via DAO contract
    
    Args:
        dao_id: DAO address
        
    Returns:
        Transaction hash
    """
    db = SessionLocal()
    try:
        # Call Movement Network to dissolve DAO
        movement_service = MovementService()
        tx_hash = await movement_service.call_contract(
            contract_address=dao_id,
            function_name="dissolve_dao",
            args=[],
        )

        logger.info(f"Dissolved DAO {dao_id} on-chain")

        return tx_hash

    finally:
        db.close()


@activity.defn
async def distribute_liquidation_funds(
    dao_id: str, member_addresses: list[str], member_investments: list[int], treasury_balance: int
) -> dict:
    """Distribute DAO treasury funds to members on liquidation
    
    Args:
        dao_id: DAO address
        member_addresses: List of member wallet addresses
        member_investments: List of member investment amounts
        treasury_balance: Current treasury balance
        
    Returns:
        Distribution details with transaction hashes
    """
    db = SessionLocal()
    try:
        from services.dao_liquidation_service import DAOLiquidationService
        
        # Calculate total available funds
        total_available_funds = DAOLiquidationService.calculate_total_available_funds(
            db, dao_id, treasury_balance
        )
        
        if total_available_funds == 0:
            logger.info(f"No funds to distribute for DAO {dao_id}")
            return {
                "dao_id": dao_id,
                "total_available_funds": 0,
                "distributions": {},
                "transaction_hashes": [],
            }
        
        # Calculate total investment
        total_investment = sum(member_investments)
        if total_investment == 0:
            raise ValueError("Total investment is zero, cannot distribute funds")
        
        # Calculate distributions for each member
        distributions = {}
        transaction_hashes = []
        
        for member_address, member_investment in zip(member_addresses, member_investments):
            # Calculate voting power percentage
            voting_power_pct = DAOLiquidationService.get_member_voting_power_percentage(
                member_investment, total_investment
            )
            
            # Calculate member's liquidation share
            member_share = DAOLiquidationService.calculate_member_liquidation_share(
                voting_power_pct, total_available_funds
            )
            
            if member_share > 0:
                distributions[member_address] = member_share
                
                # Transfer funds to member via Movement Network
                movement_service = MovementService()
                tx_hash = await movement_service.transfer_funds(
                    from_address=dao_id,
                    to_address=member_address,
                    amount=member_share,
                )
                
                transaction_hashes.append(tx_hash)
                
                # Record distribution
                DAOLiquidationService.record_liquidation_distribution(
                    db=db,
                    dao_id=dao_id,
                    member_address=member_address,
                    distribution_amount=member_share,
                )
                
                logger.info(
                    f"Distributed {member_share} tokens to {member_address} "
                    f"(voting power: {voting_power_pct}%)"
                )
        
        # Validate distribution sum
        if not DAOLiquidationService.validate_distribution_sum(
            distributions, total_available_funds
        ):
            logger.warning(
                f"Distribution sum validation failed for DAO {dao_id}, "
                f"but continuing with distribution"
            )
        
        logger.info(
            f"Completed liquidation distribution for DAO {dao_id}: "
            f"total_available_funds={total_available_funds}, members={len(distributions)}"
        )
        
        return {
            "dao_id": dao_id,
            "total_available_funds": total_available_funds,
            "distributions": distributions,
            "transaction_hashes": transaction_hashes,
            "members_paid": len(distributions),
        }

    finally:
        db.close()
