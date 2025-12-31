"""Risk profile-related activities"""

from temporalio import activity
from database.connection import SessionLocal
from services.risk_profile_service import RiskProfileService
import logging

logger = logging.getLogger(__name__)


@activity.defn
async def check_inactive_users(days_inactive: int = 30) -> list[str]:
    """
    Activity: Check for users with no transactions for specified days
    
    Requirement 7.7: Find users with no transactions for 1+ month
    """
    logger.info(f"Checking for users inactive for {days_inactive} days")

    db = SessionLocal()
    try:
        service = RiskProfileService(db)
        inactive_users = service.get_inactive_users(days_inactive)
        logger.info(f"Found {len(inactive_users)} inactive users")
        return inactive_users
    finally:
        db.close()


@activity.defn
async def apply_decay(user_ids: list[str]) -> dict:
    """
    Activity: Apply risk profile decay to users
    
    Requirement 7.7: Apply -2 point decay to inactive users
    Requirement 7.8: Ensure decay only applies if profile > 0
    """
    logger.info(f"Applying decay to {len(user_ids)} users")

    db = SessionLocal()
    try:
        service = RiskProfileService(db)
        affected_count = 0
        total_decay = 0

        for user_id in user_ids:
            profile = service.apply_decay(user_id)
            affected_count += 1
            # Track total decay applied
            total_decay += 2  # DECAY_AMOUNT

        logger.info(
            f"Applied decay to {affected_count} users, "
            f"total decay points: {total_decay}"
        )

        return {
            "users_affected": affected_count,
            "total_decay_points": total_decay,
            "completed": True,
        }
    finally:
        db.close()
