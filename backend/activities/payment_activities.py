"""Payment-related activities"""

from temporalio import activity
from dataclasses import dataclass
from sqlalchemy.orm import Session
from database.database import SessionLocal
from database.models import PaymentRequest, User, Account
from backend.services.payments.payment_request_service import PaymentRequestService
from services.pyth_service import PythService
from services.movement_service import MovementService
from services.risk_profile_service import RiskProfileService
import logging

logger = logging.getLogger(__name__)


@activity.defn
async def validate_payment_request(payment_request_id: str) -> dict:
    """Validate payment request exists and is not expired
    
    Requirement: 11.1, 11.2
    
    Checks:
    - Payment request exists
    - Payment request has not expired
    - Payment request status is "Created"
    - Both payer and recipient exist
    """
    logger.info(f"Validating payment request {payment_request_id}")
    
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
        
        logger.info(f"Payment request {payment_request_id} validated successfully")
        
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
async def fetch_pyth_price(fiat_amount: float, currency: str = "USD") -> int:
    """Fetch Pyth price and convert fiat to token
    
    Requirement: 11.2, 23.2
    
    Uses Pyth Oracle to get current MOVE/USD price and converts fiat to token amount.
    """
    logger.info(f"Fetching Pyth price for {fiat_amount} {currency}")
    
    pyth_service = PythService()
    
    try:
        # Convert fiat to token using Pyth Oracle
        amount_token = await pyth_service.convert_fiat_to_token(
            amount_fiat=fiat_amount,
            fiat_currency=currency,
            token_symbol="MOVE"
        )
        
        logger.info(f"Converted {fiat_amount} {currency} to {amount_token} MOVE")
        
        return amount_token
    except Exception as e:
        logger.error(f"Failed to fetch Pyth price: {str(e)}")
        raise


@activity.defn
async def call_movement_contract(
    payer_address: str,
    recipient_address: str,
    amount_token: int,
) -> str:
    """Call Movement payment contract via 0x1::coin::transfer
    
    Requirement: 11.1, 11.2, 11.3
    
    Uses Movement SDK to execute coin transfer on Movement Network.
    """
    logger.info(f"Calling Movement contract for payment from {payer_address} to {recipient_address}")
    
    movement_service = MovementService()
    
    try:
        # Call Movement contract to transfer MOVE tokens
        # Using 0x1::coin::transfer from Aptos framework
        result = await movement_service.call_contract(
            contract_address="0x1",
            function_name="coin::transfer",
            args=[recipient_address, amount_token],
            type_args=["0x1::aptos_coin::AptosCoin"],  # MOVE token
        )
        
        transaction_hash = result.get("hash", "")
        logger.info(f"Movement contract call successful: {transaction_hash}")
        
        return transaction_hash
    except Exception as e:
        logger.error(f"Failed to call Movement contract: {str(e)}")
        raise


@activity.defn
async def update_risk_profiles(payer_id: str, recipient_id: str) -> dict:
    """Update risk profiles for both payer and recipient (+1 each)
    
    Requirement: 11.4, 20.4
    
    Increments risk profile by 1 point for both payer and recipient
    to reward successful payment participation.
    """
    logger.info(f"Updating risk profiles for {payer_id} and {recipient_id}")
    
    db = SessionLocal()
    try:
        risk_service = RiskProfileService(db=db)
        
        # Update payer risk profile (+1 for transaction)
        payer_profile = risk_service.record_transaction(payer_id)
        logger.info(f"Updated payer {payer_id} risk profile to {payer_profile.score}")
        
        # Update recipient risk profile (+1 for transaction)
        recipient_profile = risk_service.record_transaction(recipient_id)
        logger.info(f"Updated recipient {recipient_id} risk profile to {recipient_profile.score}")
        
        return {
            "payer_id": payer_id,
            "payer_new_score": payer_profile.score,
            "recipient_id": recipient_id,
            "recipient_new_score": recipient_profile.score,
            "updated": True,
        }
    except Exception as e:
        logger.error(f"Failed to update risk profiles: {str(e)}")
        # Don't fail the workflow if risk profile update fails
        # Payment already succeeded, this is just a bonus
        logger.warning("Risk profile update failed, but payment succeeded")
        return {
            "payer_id": payer_id,
            "recipient_id": recipient_id,
            "updated": False,
            "error": str(e),
        }
    finally:
        db.close()


@activity.defn
async def mark_payment_completed(payment_request_id: str) -> dict:
    """Mark payment request as completed
    
    Requirement: 11.1, 11.2
    
    Updates payment request status to "Completed" after successful payment.
    """
    logger.info(f"Marking payment {payment_request_id} as completed")
    
    db = SessionLocal()
    try:
        pyth_service = PythService()
        service = PaymentRequestService(db=db, pyth_service=pyth_service)
        
        payment_request = service.mark_payment_request_completed(payment_request_id)
        
        logger.info(f"Payment {payment_request_id} marked as completed")
        
        return {
            "payment_request_id": payment_request_id,
            "status": "completed",
            "updated_at": payment_request.updated_at.isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to mark payment completed: {str(e)}")
        raise
    finally:
        db.close()
