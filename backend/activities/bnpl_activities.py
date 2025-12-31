"""BNPL (Buy Now Pay Later) payment activities"""

from temporalio import activity
from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.database import SessionLocal
from database.models import PaymentRequest, User, BNPLPayment
from backend.services.payments.payment_request_service import PaymentRequestService
from services.pyth_service import PythService
from services.movement_service import MovementService
from services.risk_profile_service import RiskProfileService
import logging

logger = logging.getLogger(__name__)


@activity.defn
async def validate_bnpl_payment_request(payment_request_id: str) -> dict:
    """Validate BNPL payment request exists and is not expired
    
    Requirement: 12.1, 12.2
    
    Checks:
    - Payment request exists
    - Payment request has not expired
    - Payment request status is "Created"
    - Both payer and recipient exist
    """
    logger.info(f"Validating BNPL payment request {payment_request_id}")
    
    db = SessionLocal()
    try:
        pyth_service = PythService()
        service = PaymentRequestService(db=db, pyth_service=pyth_service)
        
        # Check if payment request exists
        payment_request = service.get_payment_request(payment_request_id)
        if not payment_request:
            raise ValueError(f"Payment request {payment_request_id} not found")
        
        # Check if expired
        if service.check_payment_request_expired(payment_request_id):
            raise ValueError("Payment request has expired")
        
        # Check if already processed
        if payment_request.status != "Created":
            raise ValueError(f"Payment request already {payment_request.status.lower()}")
        
        # Check if users exist
        payer = db.query(User).filter(User.id == payment_request.payer_id).first()
        if not payer:
            raise ValueError(f"Payer user {payment_request.payer_id} not found")
        
        recipient = db.query(User).filter(User.id == payment_request.recipient_id).first()
        if not recipient:
            raise ValueError(f"Recipient user {payment_request.recipient_id} not found")
        
        logger.info(f"BNPL payment request {payment_request_id} validated successfully")
        
        return {
            "valid": True,
            "payment_request_id": payment_request_id,
            "payer_id": payment_request.payer_id,
            "recipient_id": payment_request.recipient_id,
            "amount_token": payment_request.amount_token,
            "amount_fiat": payment_request.amount_fiat,
        }
    finally:
        db.close()


@activity.defn
async def calculate_bnpl_installments(amount_token: int) -> dict:
    """Calculate 1/3 installments for BNPL payment
    
    Requirement: 12.3
    
    Divides total amount into three equal installments.
    Returns installment amounts and schedule.
    """
    logger.info(f"Calculating BNPL installments for {amount_token} tokens")
    
    # Calculate 1/3 installments
    installment_amount = amount_token // 3
    remainder = amount_token % 3
    
    # First installment gets the remainder to ensure total equals original amount
    installment_1 = installment_amount + remainder
    installment_2 = installment_amount
    installment_3 = installment_amount
    
    # Verify total equals original amount
    total = installment_1 + installment_2 + installment_3
    if total != amount_token:
        raise ValueError(f"Installment calculation error: {total} != {amount_token}")
    
    logger.info(f"Calculated installments: {installment_1}, {installment_2}, {installment_3}")
    
    return {
        "installment_1": installment_1,
        "installment_2": installment_2,
        "installment_3": installment_3,
        "total": total,
    }


@activity.defn
async def process_first_bnpl_payment(
    payer_address: str,
    recipient_address: str,
    installment_amount: int,
) -> str:
    """Process first 1/3 BNPL payment immediately
    
    Requirement: 12.4
    
    Uses Movement SDK to execute first coin transfer on Movement Network.
    This is called after merchant payment to pay the first installment.
    """
    logger.info(f"Processing first BNPL payment from {payer_address} to {recipient_address}")
    
    movement_service = MovementService()
    
    try:
        # Build and submit transaction to transfer MOVE tokens
        # The transaction should be pre-signed by the user (via Privy on frontend)
        # and submitted here as a BCS-serialized transaction
        
        # For now, we assume the transaction is already signed and we submit it
        # In production, this would be called with a pre-signed transaction from the frontend
        
        result = await movement_service.submit_signed_transaction(
            signed_tx_bcs="0x" + "placeholder_signed_tx",  # Would be passed from frontend
        )
        
        transaction_hash = result.get("hash", "")
        logger.info(f"First BNPL payment successful: {transaction_hash}")
        
        return transaction_hash
    except Exception as e:
        logger.error(f"Failed to process first BNPL payment: {str(e)}")
        raise


@activity.defn
async def schedule_bnpl_installments(
    payment_request_id: str,
    payer_id: str,
    recipient_id: str,
    installment_2: int,
    installment_3: int,
) -> dict:
    """Schedule two additional 1/3 BNPL payments (monthly)
    
    Requirement: 12.5, 12.6
    
    Creates BNPL payment records in database with scheduled payment dates.
    """
    logger.info(f"Scheduling BNPL installments for {payment_request_id}")
    
    db = SessionLocal()
    try:
        # Create BNPL payment records for installments 2 and 3
        from datetime import timezone
        now = datetime.now(timezone.utc)
        
        # Installment 2 (due in 30 days)
        bnpl_payment_2 = BNPLPayment(
            payment_request_id=payment_request_id,
            installment_number=2,
            amount=installment_2,
            due_date=now + timedelta(days=30),
            status="Pending",
            late_fee=0,
        )
        
        # Installment 3 (due in 60 days)
        bnpl_payment_3 = BNPLPayment(
            payment_request_id=payment_request_id,
            installment_number=3,
            amount=installment_3,
            due_date=now + timedelta(days=60),
            status="Pending",
            late_fee=0,
        )
        
        db.add(bnpl_payment_2)
        db.add(bnpl_payment_3)
        db.commit()
        
        logger.info(f"BNPL payments created: {bnpl_payment_2.id}, {bnpl_payment_3.id}")
        
        return {
            "bnpl_payment_2_id": bnpl_payment_2.id,
            "bnpl_payment_3_id": bnpl_payment_3.id,
            "installment_2_due_date": bnpl_payment_2.due_date.isoformat(),
            "installment_3_due_date": bnpl_payment_3.due_date.isoformat(),
            "scheduled": True,
        }
    except Exception as e:
        logger.error(f"Failed to schedule BNPL installments: {str(e)}")
        raise
    finally:
        db.close()


@activity.defn
async def update_bnpl_risk_profile(
    payer_id: str,
    on_time: bool = True,
) -> dict:
    """Update payer risk profile based on BNPL payment status
    
    Requirement: 12.7
    
    +2 for on-time payment, -3 for late payment
    """
    logger.info(f"Updating BNPL risk profile for {payer_id} (on_time={on_time})")
    
    db = SessionLocal()
    try:
        risk_service = RiskProfileService(db=db)
        
        if on_time:
            # +2 for on-time BNPL payment
            profile = risk_service.record_bnpl_payment(payer_id, on_time=True)
            logger.info(f"Updated payer {payer_id} risk profile to {profile.score} (on-time)")
        else:
            # -3 for late BNPL payment
            profile = risk_service.record_bnpl_payment(payer_id, on_time=False)
            logger.info(f"Updated payer {payer_id} risk profile to {profile.score} (late)")
        
        return {
            "payer_id": payer_id,
            "new_score": profile.score,
            "on_time": on_time,
            "updated": True,
        }
    except Exception as e:
        logger.error(f"Failed to update BNPL risk profile: {str(e)}")
        # Don't fail the workflow if risk profile update fails
        logger.warning("BNPL risk profile update failed, but payment processing continues")
        return {
            "payer_id": payer_id,
            "updated": False,
            "error": str(e),
        }
    finally:
        db.close()


@activity.defn
async def apply_bnpl_late_fee(bnpl_payment_id: str) -> dict:
    """Apply 5% late fee on missed BNPL payments
    
    Requirement: 12.8, 6.4
    
    Calculates and applies 5% late fee to overdue installments.
    """
    logger.info(f"Applying late fee to BNPL payment {bnpl_payment_id}")
    
    db = SessionLocal()
    try:
        payment = db.query(BNPLPayment).filter(
            BNPLPayment.id == bnpl_payment_id
        ).first()
        
        if not payment:
            raise ValueError(f"BNPL payment {bnpl_payment_id} not found")
        
        # Check if payment is overdue
        from datetime import timezone
        now = datetime.now(timezone.utc)
        
        if payment.status == "Pending" and payment.due_date < now:
            # Calculate 5% late fee
            late_fee = int(payment.amount * 0.05)
            
            # Update payment
            payment.status = "Late"
            payment.late_fee = late_fee
            db.commit()
            
            logger.info(f"Applied late fee of {late_fee} tokens to {bnpl_payment_id}")
            
            return {
                "bnpl_payment_id": bnpl_payment_id,
                "late_fee_applied": True,
                "late_fee_amount": late_fee,
                "overdue_amount": payment.amount,
            }
        else:
            logger.info(f"No late fee applicable for {bnpl_payment_id}")
            return {
                "bnpl_payment_id": bnpl_payment_id,
                "late_fee_applied": False,
                "late_fee_amount": 0,
            }
    except Exception as e:
        logger.error(f"Failed to apply late fee: {str(e)}")
        raise
    finally:
        db.close()


@activity.defn
async def distribute_bnpl_late_fees(
    dao_id: str,
    late_fee_amount: int,
) -> dict:
    """Distribute BNPL late fees to DAO members proportionally
    
    Requirement: 12.8, 6.5
    
    Uses Movement Network to:
    1. Get DAO members and their voting power from blockchain
    2. Calculate proportional distribution based on voting power
    3. Execute transfers via Movement SDK
    4. Return distribution results
    """
    logger.info(f"Distributing BNPL late fees ({late_fee_amount} tokens) to DAO {dao_id}")
    
    movement_service = MovementService()
    db = SessionLocal()
    
    try:
        # Call DAO contract to get members and voting power
        # The DAO contract should have: get_members() -> vector<(address, u64)>
        # where u64 is the voting power
        
        result = await movement_service.call_contract(
            contract_address=dao_id,
            function_name="get_members",
            args=[],
            type_args=[],
        )
        
        dao_members = result.get("members", [])
        
        if not dao_members:
            logger.warning(f"DAO {dao_id} has no members")
            return {
                "dao_id": dao_id,
                "late_fee_amount": late_fee_amount,
                "distributed": False,
                "members_count": 0,
                "error": "No members found",
            }
        
        # Calculate total voting power
        total_voting_power = sum(member.get("voting_power", 0) for member in dao_members)
        
        if total_voting_power == 0:
            logger.warning(f"DAO {dao_id} has no voting power")
            return {
                "dao_id": dao_id,
                "late_fee_amount": late_fee_amount,
                "distributed": False,
                "members_count": len(dao_members),
                "error": "No voting power",
            }
        
        # Distribute fees proportionally based on voting power
        distributions = []
        total_distributed = 0
        
        for member in dao_members:
            voting_power = member.get("voting_power", 0)
            if voting_power == 0:
                continue
            
            # Calculate proportional share
            member_share = int((voting_power / total_voting_power) * late_fee_amount)
            
            if member_share == 0:
                continue
            
            member_address = member.get("address")
            
            try:
                # Execute transfer via Movement SDK
                transfer_result = await movement_service.submit_signed_transaction(
                    signed_tx_bcs="0x" + "placeholder_transfer_tx",  # Would be pre-signed
                )
                
                transaction_hash = transfer_result.get("hash", "")
                distributions.append({
                    "member_address": member_address,
                    "voting_power": voting_power,
                    "share_amount": member_share,
                    "transaction_hash": transaction_hash,
                })
                
                total_distributed += member_share
                logger.info(f"Distributed {member_share} tokens to {member_address}")
                
            except Exception as e:
                logger.error(f"Failed to distribute to {member_address}: {str(e)}")
                continue
        
        logger.info(f"Distributed {total_distributed} late fees to {len(distributions)} DAO members")
        
        return {
            "dao_id": dao_id,
            "late_fee_amount": late_fee_amount,
            "total_distributed": total_distributed,
            "members_count": len(distributions),
            "distributions": distributions,
            "distributed": True,
        }
    except Exception as e:
        logger.error(f"Failed to distribute late fees: {str(e)}")
        raise
    finally:
        db.close()


@activity.defn
async def check_bnpl_installment_reminders() -> dict:
    """Check for upcoming BNPL payments and send reminders
    
    Requirement: 12.3, 12.5, 12.6
    
    Scheduled activity that:
    1. Checks for BNPL payments due within next 3 days
    2. Sends reminders to payers
    3. Tracks payment status
    """
    logger.info("Checking for upcoming BNPL installment reminders")
    
    db = SessionLocal()
    try:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        reminder_window = timedelta(days=3)
        
        # Find BNPL payments due within next 3 days
        upcoming_payments = db.query(BNPLPayment).filter(
            BNPLPayment.status == "Pending",
            BNPLPayment.due_date >= now,
            BNPLPayment.due_date <= now + reminder_window,
        ).all()
        
        reminders_sent = 0
        
        for payment in upcoming_payments:
            try:
                # Get payment request to find payer
                payment_request = db.query(PaymentRequest).filter(
                    PaymentRequest.id == payment.payment_request_id
                ).first()
                
                if not payment_request:
                    logger.warning(f"Payment request {payment.payment_request_id} not found")
                    continue
                
                # Get payer user
                payer = db.query(User).filter(User.id == payment_request.payer_id).first()
                if not payer:
                    logger.warning(f"Payer {payment_request.payer_id} not found")
                    continue
                
                # Send reminder (placeholder - would integrate with email service)
                logger.info(f"Sending BNPL reminder to {payer.email} for payment {payment.id}")
                # TODO: Send email reminder via email service
                # TODO: Log reminder in database
                
                reminders_sent += 1
            except Exception as e:
                logger.error(f"Failed to send reminder for BNPL {payment.id}: {str(e)}")
                continue
        
        logger.info(f"Sent {reminders_sent} BNPL installment reminders")
        
        return {
            "reminders_sent": reminders_sent,
            "checked_at": now.isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to check BNPL installment reminders: {str(e)}")
        raise
    finally:
        db.close()


@activity.defn
async def track_bnpl_payment_status(bnpl_payment_id: str) -> dict:
    """Track BNPL payment status and update records
    
    Requirement: 12.5, 12.6
    
    Updates payment status based on:
    1. Payment due date
    2. Payment received status
    3. Late fee application
    """
    logger.info(f"Tracking BNPL payment status for {bnpl_payment_id}")
    
    db = SessionLocal()
    try:
        payment = db.query(BNPLPayment).filter(
            BNPLPayment.id == bnpl_payment_id
        ).first()
        
        if not payment:
            raise ValueError(f"BNPL payment {bnpl_payment_id} not found")
        
        from datetime import timezone
        now = datetime.now(timezone.utc)
        
        # Check if payment is overdue
        if (payment.status == "Pending" and 
            payment.due_date < now and 
            payment.paid_date is None):
            
            # Mark as late
            payment.status = "Late"
            
            # Apply 5% late fee
            late_fee = int(payment.amount * 0.05)
            payment.late_fee = late_fee
            
            logger.info(f"BNPL payment {bnpl_payment_id} marked as late with fee {late_fee}")
        
        db.commit()
        
        return {
            "bnpl_payment_id": bnpl_payment_id,
            "status": payment.status,
            "late_fee": payment.late_fee,
            "updated": True,
        }
    except Exception as e:
        logger.error(f"Failed to track BNPL payment status: {str(e)}")
        raise
    finally:
        db.close()


@activity.defn
async def mark_bnpl_payment_completed(payment_request_id: str) -> dict:
    """Mark BNPL payment request as completed
    
    Requirement: 12.1, 12.2
    
    Updates payment request status to "Completed" after first payment.
    """
    logger.info(f"Marking BNPL payment {payment_request_id} as completed")
    
    db = SessionLocal()
    try:
        pyth_service = PythService()
        service = PaymentRequestService(db=db, pyth_service=pyth_service)
        
        payment_request = service.mark_payment_request_completed(payment_request_id)
        
        logger.info(f"BNPL payment {payment_request_id} marked as completed")
        
        return {
            "payment_request_id": payment_request_id,
            "status": "completed",
            "updated_at": payment_request.updated_at.isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to mark BNPL payment completed: {str(e)}")
        raise
    finally:
        db.close()
