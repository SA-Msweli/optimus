"""x402 payment protocol activities for BNPL"""

from temporalio import activity
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta, timezone
from database.connection import get_db
from database.models import BNPLPayment, DAOMetadata, BNPLAccess
from sqlalchemy.orm import Session
from services.movement_service import MovementService
from config import settings
import httpx
import json

logger = logging.getLogger(__name__)

# Import x402 library for protocol operations
try:
    from x402plus import TransactionBuilder, FacilitatorClient, TransactionValidator
    HAS_X402 = True
except ImportError:
    HAS_X402 = False
    logger.warning("x402plus library not available")


@activity.defn
async def validate_x402_transactions(
    signed_transactions: List[str],
    num_installments: int,
    payer_address: str,
    dao_treasury_address: str,
    expected_amount_per_installment: int,
) -> Dict[str, Any]:
    """Validate N pre-signed x402 transactions per x402 spec
    
    Validates per x402 protocol specification:
    - Correct number of transactions
    - All transactions are properly signed and valid
    - Correct sender (payer_address)
    - Correct recipient (dao_treasury_address)
    - Correct amount per transaction
    - Transaction format complies with x402 spec
    
    Args:
        signed_transactions: List of BCS-serialized signed transactions
        num_installments: Expected number of installments
        payer_address: User's wallet address (sender)
        dao_treasury_address: DAO treasury address (recipient)
        expected_amount_per_installment: Amount per installment in tokens
    
    Returns:
        Dict with validation result
    
    Raises:
        ValueError: If validation fails
    """
    logger.info(
        f"Validating {len(signed_transactions)} x402 transactions for {payer_address}"
    )

    # Validate correct number of transactions
    if len(signed_transactions) != num_installments:
        raise ValueError(
            f"Expected {num_installments} transactions, got {len(signed_transactions)}"
        )

    if not HAS_X402:
        raise RuntimeError("x402plus library not available - cannot validate transactions")

    # Use x402 library to validate each transaction
    validator = TransactionValidator()
    validated_transactions = []
    
    for idx, signed_tx_hex in enumerate(signed_transactions):
        if not signed_tx_hex or not isinstance(signed_tx_hex, str):
            raise ValueError(f"Transaction {idx + 1} is invalid or empty")
        
        try:
            # Parse BCS-serialized transaction
            tx_bytes = bytes.fromhex(signed_tx_hex.replace("0x", ""))
            
            # Validate transaction per x402 spec using x402 library
            validation_result = validator.validate(
                transaction_bytes=tx_bytes,
                expected_sender=payer_address,
                expected_recipient=dao_treasury_address,
                expected_amount=expected_amount_per_installment,
            )
            
            if not validation_result.is_valid:
                raise ValueError(
                    f"Transaction {idx + 1} failed x402 validation: {validation_result.error_message}"
                )
            
            # Verify signature is valid
            if not validation_result.signature_valid:
                raise ValueError(f"Transaction {idx + 1} has invalid signature")
            
            logger.info(
                f"Transaction {idx + 1}: Valid x402 transaction, "
                f"sender={validation_result.sender}, "
                f"recipient={validation_result.recipient}, "
                f"amount={validation_result.amount}"
            )
            
            validated_transactions.append({
                "index": idx,
                "signed_tx": signed_tx_hex,
                "valid": True,
                "size_bytes": len(tx_bytes),
                "sender": validation_result.sender,
                "recipient": validation_result.recipient,
                "amount": validation_result.amount,
                "signature_valid": validation_result.signature_valid,
            })
            
        except Exception as e:
            logger.error(f"Transaction {idx + 1} validation failed: {str(e)}")
            raise ValueError(f"Transaction {idx + 1} failed validation: {str(e)}")
    
    logger.info(f"All {num_installments} transactions validated successfully per x402 spec")
    
    return {
        "valid": True,
        "num_transactions": num_installments,
        "payer_address": payer_address,
        "dao_treasury_address": dao_treasury_address,
        "amount_per_installment": expected_amount_per_installment,
        "validated_transactions": validated_transactions,
    }


@activity.defn
async def submit_x402_transaction(
    signed_transaction_bcs: str,
    facilitator_url: str = None,
) -> Dict[str, Any]:
    """Submit pre-signed x402 transaction via facilitator
    
    Uses x402 facilitator to submit transaction:
    1. Verify transaction format per x402 spec
    2. Submit to facilitator
    3. Facilitator validates and submits to blockchain
    4. Wait for confirmation
    5. Return transaction hash
    
    Args:
        signed_transaction_bcs: BCS-serialized signed transaction
        facilitator_url: Facilitator endpoint (defaults to config or Stableyard)
    
    Returns:
        Dict with transaction hash and status
    
    Raises:
        Exception: If submission fails
    """
    if facilitator_url is None:
        facilitator_url = settings.x402_facilitator_url or "https://facilitator.stableyard.fi"
    
    logger.info(f"Submitting x402 transaction via facilitator: {facilitator_url}")
    
    if not HAS_X402:
        raise RuntimeError("x402plus library not available - cannot submit transactions")
    
    try:
        # Use x402 library's facilitator client
        facilitator_client = FacilitatorClient(facilitator_url)
        
        # Submit signed transaction to facilitator
        result = await facilitator_client.submit_transaction(
            signed_transaction_bcs=signed_transaction_bcs,
            network=settings.movement_network,
        )
        
        transaction_hash = result.get("transaction_hash") or result.get("hash")
        
        if not transaction_hash:
            raise Exception(f"No transaction hash in facilitator response: {result}")
        
        logger.info(f"Transaction submitted successfully: {transaction_hash}")
        
        return {
            "success": True,
            "transaction_hash": transaction_hash,
            "facilitator": facilitator_url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
            
    except Exception as e:
        logger.error(f"Transaction submission failed: {str(e)}")
        raise Exception(f"Failed to submit x402 transaction: {str(e)}")


@activity.defn
async def store_x402_installment(
    payment_request_id: str,
    dao_id: str,
    user_id: str,
    installment_number: int,
    amount_token: int,
    due_date: datetime,
    signed_transaction_bcs: str,
    transaction_hash: str = None,
) -> Dict[str, Any]:
    """Store x402 BNPL installment payment in database
    
    Creates BNPLPayment record with:
    - Pre-signed transaction (for future execution)
    - Due date (when to execute)
    - Transaction hash (if already executed)
    - Status (Pending for future, Paid for executed)
    
    Args:
        payment_request_id: Related payment request
        dao_id: DAO providing BNPL
        user_id: User making installment payment
        installment_number: 1, 2, 3, etc.
        amount_token: Amount in tokens
        due_date: When payment should be executed
        signed_transaction_bcs: Pre-signed transaction
        transaction_hash: Hash if already executed (optional)
    
    Returns:
        Dict with created BNPL payment details
    """
    logger.info(
        f"Storing x402 installment {installment_number} for payment request {payment_request_id}"
    )
    
    db: Session = next(get_db())
    try:
        # Determine status based on transaction_hash
        status = "Paid" if transaction_hash else "Pending"
        paid_at = datetime.now(timezone.utc) if transaction_hash else None
        
        # Create BNPL payment record
        bnpl_payment = BNPLPayment(
            payment_request_id=payment_request_id,
            dao_id=dao_id,
            payer_id=user_id,
            installment_number=installment_number,
            amount_token=amount_token,
            due_date=due_date,
            status=status,
            signed_transaction_bcs=signed_transaction_bcs,
            transaction_hash=transaction_hash,
            paid_at=paid_at,
        )
        
        db.add(bnpl_payment)
        db.commit()
        db.refresh(bnpl_payment)
        
        logger.info(
            f"Installment {installment_number} stored successfully: ID={bnpl_payment.id}"
        )
        
        return {
            "success": True,
            "bnpl_payment_id": bnpl_payment.id,
            "installment_number": installment_number,
            "amount_token": amount_token,
            "due_date": due_date.isoformat(),
            "status": status,
            "transaction_hash": transaction_hash,
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to store installment: {str(e)}")
        raise
    finally:
        db.close()


@activity.defn
async def execute_dao_merchant_payment(
    dao_id: str,
    merchant_address: str,
    amount_token: int,
    user_id: str,
    payment_request_id: str,
) -> Dict[str, Any]:
    """Execute DAO treasury → merchant payment
    
    Uses pre-signed DAO treasury operation to pay merchant.
    The DAO pre-signed this operation during BNPL access approval.
    
    Args:
        dao_id: DAO providing BNPL
        merchant_address: Merchant receiving payment
        amount_token: Full payment amount
        user_id: User ID (for audit trail)
        payment_request_id: Payment request ID (for audit trail)
    
    Returns:
        Dict with transaction hash and status
    
    Raises:
        Exception: If payment fails
    """
    logger.info(
        f"Executing DAO → merchant payment: DAO={dao_id}, merchant={merchant_address}, amount={amount_token}"
    )
    
    db: Session = next(get_db())
    try:
        # Get BNPLAccess record with pre-signed treasury operation
        bnpl_access = db.query(BNPLAccess).filter(
            BNPLAccess.dao_id == dao_id,
            BNPLAccess.user_id == user_id,
            BNPLAccess.status == "Approved"
        ).first()
        
        if not bnpl_access:
            raise ValueError(
                f"No approved BNPL access found for user {user_id} and DAO {dao_id}"
            )
        
        if not bnpl_access.treasury_operation_bcs:
            raise ValueError(
                f"No pre-signed treasury operation found for BNPL access {bnpl_access.id}"
            )
        
        logger.info(f"Found pre-signed treasury operation: {bnpl_access.id}")
        
        # Submit pre-signed treasury operation to Movement Network
        movement_service = MovementService()
        result = await movement_service.submit_signed_transaction(
            bnpl_access.treasury_operation_bcs
        )
        
        transaction_hash = result.get("hash")
        
        if not transaction_hash:
            raise Exception("No transaction hash returned from Movement Network")
        
        logger.info(f"DAO → merchant payment executed: {transaction_hash}")
        
        return {
            "success": True,
            "transaction_hash": transaction_hash,
            "dao_id": dao_id,
            "merchant_address": merchant_address,
            "amount_token": amount_token,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Failed to execute DAO → merchant payment: {str(e)}")
        raise
    finally:
        db.close()


@activity.defn
async def get_dao_payment_terms(dao_id: str) -> Dict[str, Any]:
    """Get DAO's BNPL payment terms
    
    Retrieves:
    - bnpl_payment_period_days: Total payment period (e.g., 28 days)
    - bnpl_num_installments: Number of installments (e.g., 4)
    
    Args:
        dao_id: DAO ID
    
    Returns:
        Dict with payment terms
    
    Raises:
        ValueError: If DAO not found or payment terms not configured
    """
    logger.info(f"Getting payment terms for DAO {dao_id}")
    
    db: Session = next(get_db())
    try:
        dao_metadata = db.query(DAOMetadata).filter_by(dao_id=dao_id).first()
        if not dao_metadata:
            raise ValueError(f"DAO metadata not found for DAO {dao_id}")
        
        if not dao_metadata.bnpl_payment_period_days or not dao_metadata.bnpl_num_installments:
            raise ValueError(f"DAO {dao_id} has not configured BNPL payment terms")
        
        # Calculate days between installments
        days_between_installments = dao_metadata.bnpl_payment_period_days // dao_metadata.bnpl_num_installments
        
        logger.info(
            f"Payment terms retrieved: period={dao_metadata.bnpl_payment_period_days} days, "
            f"installments={dao_metadata.bnpl_num_installments}"
        )
        
        return {
            "dao_id": dao_id,
            "payment_period_days": dao_metadata.bnpl_payment_period_days,
            "num_installments": dao_metadata.bnpl_num_installments,
            "days_between_installments": days_between_installments,
        }
    
    except Exception as e:
        logger.error(f"Failed to get payment terms: {str(e)}")
        raise
    finally:
        db.close()


@activity.defn
async def check_installment_balance(payer_address: str, amount_token: int) -> Dict[str, Any]:
    """Check if user has sufficient balance for installment
    
    Queries Movement Network to get actual wallet balance and verifies
    user has sufficient funds for the installment payment.
    
    Args:
        payer_address: User's wallet address
        amount_token: Amount needed in tokens
    
    Returns:
        Dict with balance check result
    
    Raises:
        ValueError: If insufficient balance
    """
    logger.info(f"Checking balance for {payer_address}: need {amount_token} tokens")
    
    movement_service = MovementService()
    
    try:
        # Get account resources from Movement Network
        resources = await movement_service.get_account_resources(payer_address)
        
        # Parse resources to find MOVE token balance
        # MOVE token is typically at 0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>
        move_balance = 0
        
        if "resources" in resources:
            for resource in resources["resources"]:
                resource_type = resource.get("type", "")
                # Look for MOVE coin store
                if "CoinStore" in resource_type and "AptosCoin" in resource_type:
                    data = resource.get("data", {})
                    coin = data.get("coin", {})
                    move_balance = int(coin.get("value", 0))
                    logger.info(f"Found MOVE balance: {move_balance} tokens")
                    break
        
        # Check if sufficient balance
        if move_balance < amount_token:
            raise ValueError(
                f"Insufficient balance: have {move_balance} tokens, need {amount_token} tokens"
            )
        
        logger.info(f"Balance check passed for {payer_address}: {move_balance} >= {amount_token}")
        
        return {
            "payer_address": payer_address,
            "required_amount": amount_token,
            "available_balance": move_balance,
            "sufficient_balance": True,
        }
    
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Balance check failed: {str(e)}")
        raise ValueError(f"Failed to check balance: {str(e)}")


@activity.defn
async def collect_dao_treasury_operation(
    dao_id: str,
    user_id: str,
    max_amount: int,
) -> Dict[str, Any]:
    """Collect pre-signed DAO treasury operation for merchant payment
    
    When DAO approves BNPL access for a user, DAO also pre-signs a treasury operation:
    "DAO treasury can pay merchants up to X amount for BNPL purchases by this user"
    
    This activity retrieves that pre-signed operation from the DAO contract on Movement Network.
    
    Args:
        dao_id: DAO providing BNPL (on-chain address)
        user_id: User getting BNPL access
        max_amount: Maximum amount DAO will pre-sign for
    
    Returns:
        Dict with pre-signed treasury operation (BCS format)
    
    Raises:
        Exception: If DAO doesn't provide pre-signed operation
    """
    logger.info(
        f"Collecting pre-signed treasury operation from DAO {dao_id} for user {user_id}"
    )
    
    movement_service = MovementService()
    
    try:
        # Call DAO contract to get the pre-signed treasury operation
        # The DAO contract should have a view function like:
        # get_treasury_operation(user_address: address, max_amount: u64) -> vector<u8>
        
        result = await movement_service.call_contract(
            contract_address=dao_id,
            function_name="get_treasury_operation",
            args=[user_id, max_amount],
            type_args=[],
        )
        
        treasury_operation_bcs = result.get("treasury_operation_bcs")
        
        if not treasury_operation_bcs:
            raise Exception(
                f"DAO {dao_id} did not return pre-signed treasury operation for user {user_id}"
            )
        
        logger.info(f"Pre-signed treasury operation collected for DAO {dao_id}")
        
        return {
            "dao_id": dao_id,
            "user_id": user_id,
            "max_amount": max_amount,
            "treasury_operation_bcs": treasury_operation_bcs,
            "collected": True,
        }
    
    except Exception as e:
        logger.error(f"Failed to collect treasury operation: {str(e)}")
        raise Exception(
            f"Failed to collect pre-signed treasury operation from DAO {dao_id}: {str(e)}"
        )


@activity.defn
async def store_treasury_operation(
    application_id: str,
    dao_id: str,
    user_id: str,
    treasury_operation_bcs: str,
) -> Dict[str, Any]:
    """Store pre-signed DAO treasury operation in BNPLAccess record
    
    Args:
        application_id: BNPLAccess application ID
        dao_id: DAO providing BNPL
        user_id: User getting BNPL access
        treasury_operation_bcs: Pre-signed operation (BCS format)
    
    Returns:
        Dict with storage result
    """
    logger.info(f"Storing treasury operation for application {application_id}")
    
    db: Session = next(get_db())
    try:
        # Get BNPLAccess record
        bnpl_access = db.query(BNPLAccess).filter(
            BNPLAccess.id == application_id,
            BNPLAccess.dao_id == dao_id,
            BNPLAccess.user_id == user_id,
        ).first()
        
        if not bnpl_access:
            raise ValueError(
                f"BNPLAccess record not found: app={application_id}, dao={dao_id}, user={user_id}"
            )
        
        # Store pre-signed operation
        bnpl_access.treasury_operation_bcs = treasury_operation_bcs
        db.commit()
        
        logger.info(f"Treasury operation stored for application {application_id}")
        
        return {
            "application_id": application_id,
            "dao_id": dao_id,
            "user_id": user_id,
            "stored": True,
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to store treasury operation: {str(e)}")
        raise
    finally:
        db.close()
