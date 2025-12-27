"""
Credits Service
===============

Manages credit tracking for the Layout Service image generation endpoint.
Tracks usage per presentation and enforces credit limits.
"""

import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

# Credit costs per quality tier
CREDITS_BY_QUALITY: Dict[str, int] = {
    'draft': 1,
    'standard': 2,
    'high': 4,
    'ultra': 8
}

# Default credits allocation per presentation
DEFAULT_CREDITS_PER_PRESENTATION = 100


# ============================================================================
# Credits Service Class
# ============================================================================

class CreditsService:
    """
    Service for managing image generation credits.

    Tracks credits per presentation and enforces limits.
    Uses Supabase PostgreSQL for persistence.
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        default_credits: int = DEFAULT_CREDITS_PER_PRESENTATION
    ):
        """
        Initialize credits service.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key (preferably service key)
            default_credits: Default credits for new presentations
        """
        if not SUPABASE_AVAILABLE:
            raise ImportError("supabase not installed. Run: pip install supabase")

        self.url = supabase_url or os.getenv("SUPABASE_URL")
        self.key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

        self.client: Client = create_client(self.url, self.key)
        self.default_credits = default_credits

        logger.info(f"Initialized CreditsService (default_credits={default_credits})")

    # ========================================================================
    # Credit Balance Operations
    # ========================================================================

    def get_credits(self, presentation_id: str) -> Dict[str, int]:
        """
        Get credit balance for a presentation.

        Creates default allocation if presentation doesn't exist.

        Args:
            presentation_id: Unique presentation identifier

        Returns:
            Dictionary with:
            - total_credits: Total allocated credits
            - used_credits: Credits already used
            - remaining_credits: Credits remaining
        """
        try:
            # Try to get existing record
            response = self.client.table("presentation_credits").select("*").eq(
                "presentation_id", presentation_id
            ).execute()

            if response.data and len(response.data) > 0:
                record = response.data[0]
                return {
                    "total_credits": record["total_credits"],
                    "used_credits": record["used_credits"],
                    "remaining_credits": record["total_credits"] - record["used_credits"]
                }

            # Create new record with default credits
            new_record = {
                "presentation_id": presentation_id,
                "total_credits": self.default_credits,
                "used_credits": 0
            }

            self.client.table("presentation_credits").insert(new_record).execute()

            logger.info(f"Created new credits allocation for {presentation_id}: {self.default_credits}")

            return {
                "total_credits": self.default_credits,
                "used_credits": 0,
                "remaining_credits": self.default_credits
            }

        except Exception as e:
            logger.error(f"Failed to get credits for {presentation_id}: {e}")
            # Return default values on error (fail open for now)
            return {
                "total_credits": self.default_credits,
                "used_credits": 0,
                "remaining_credits": self.default_credits
            }

    def get_remaining_credits(self, presentation_id: str) -> int:
        """
        Get remaining credits for a presentation.

        Args:
            presentation_id: Unique presentation identifier

        Returns:
            Number of remaining credits
        """
        credits = self.get_credits(presentation_id)
        return credits["remaining_credits"]

    def has_sufficient_credits(self, presentation_id: str, required: int) -> bool:
        """
        Check if presentation has enough credits.

        Args:
            presentation_id: Unique presentation identifier
            required: Number of credits needed

        Returns:
            True if sufficient credits available
        """
        remaining = self.get_remaining_credits(presentation_id)
        return remaining >= required

    def get_credits_for_quality(self, quality: str) -> int:
        """
        Get credit cost for a quality tier.

        Args:
            quality: Quality tier (draft, standard, high, ultra)

        Returns:
            Number of credits required
        """
        return CREDITS_BY_QUALITY.get(quality, 2)  # Default to 'standard' cost

    # ========================================================================
    # Credit Deduction
    # ========================================================================

    def deduct_credits(self, presentation_id: str, amount: int) -> bool:
        """
        Deduct credits from a presentation.

        Args:
            presentation_id: Unique presentation identifier
            amount: Number of credits to deduct

        Returns:
            True if deduction successful, False if insufficient credits
        """
        try:
            # Get current balance
            credits = self.get_credits(presentation_id)

            if credits["remaining_credits"] < amount:
                logger.warning(
                    f"Insufficient credits for {presentation_id}: "
                    f"required={amount}, available={credits['remaining_credits']}"
                )
                return False

            # Update used credits
            new_used = credits["used_credits"] + amount

            self.client.table("presentation_credits").update({
                "used_credits": new_used
            }).eq("presentation_id", presentation_id).execute()

            logger.info(
                f"Deducted {amount} credits from {presentation_id}: "
                f"remaining={credits['total_credits'] - new_used}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to deduct credits for {presentation_id}: {e}")
            return False

    def refund_credits(self, presentation_id: str, amount: int) -> bool:
        """
        Refund credits to a presentation (e.g., for failed generations).

        Args:
            presentation_id: Unique presentation identifier
            amount: Number of credits to refund

        Returns:
            True if refund successful
        """
        try:
            # Get current balance
            response = self.client.table("presentation_credits").select("used_credits").eq(
                "presentation_id", presentation_id
            ).execute()

            if not response.data:
                logger.warning(f"No credits record found for {presentation_id}")
                return False

            current_used = response.data[0]["used_credits"]
            new_used = max(0, current_used - amount)

            self.client.table("presentation_credits").update({
                "used_credits": new_used
            }).eq("presentation_id", presentation_id).execute()

            logger.info(f"Refunded {amount} credits to {presentation_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to refund credits for {presentation_id}: {e}")
            return False

    # ========================================================================
    # Usage Recording
    # ========================================================================

    def record_usage(
        self,
        generation_id: str,
        presentation_id: str,
        slide_id: Optional[str],
        element_id: Optional[str],
        credits_used: int,
        quality: str,
        style: str,
        prompt: str,
        enhanced_prompt: Optional[str] = None,
        image_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        generation_time_ms: Optional[int] = None,
        model: str = "imagen-3.0-fast-generate",
        provider: str = "vertex-ai",
        status: str = "completed",
        error_code: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record image generation usage.

        Args:
            generation_id: UUID of the generation
            presentation_id: Presentation identifier
            slide_id: Slide identifier
            element_id: Element identifier
            credits_used: Credits consumed
            quality: Quality tier used
            style: Style used
            prompt: Original user prompt
            enhanced_prompt: Enhanced prompt sent to model
            image_url: URL of generated image
            thumbnail_url: URL of thumbnail
            width: Image width
            height: Image height
            generation_time_ms: Generation time in milliseconds
            model: Model used
            provider: Provider used
            status: Status (completed, failed, refunded)
            error_code: Error code if failed
            error_message: Error message if failed

        Returns:
            Dictionary with success status and record data
        """
        try:
            record = {
                "generation_id": generation_id,
                "presentation_id": presentation_id,
                "slide_id": slide_id,
                "element_id": element_id,
                "credits_used": credits_used,
                "quality": quality,
                "style": style,
                "prompt": prompt,
                "enhanced_prompt": enhanced_prompt,
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "width": width,
                "height": height,
                "generation_time_ms": generation_time_ms,
                "model": model,
                "provider": provider,
                "status": status,
                "error_code": error_code,
                "error_message": error_message
            }

            # Remove None values
            record = {k: v for k, v in record.items() if v is not None}

            response = self.client.table("image_generation_credits").insert(record).execute()

            logger.info(f"Recorded usage for generation {generation_id}")

            return {
                "success": True,
                "record": response.data[0] if response.data else None
            }

        except Exception as e:
            logger.error(f"Failed to record usage: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def record_failed_generation(
        self,
        generation_id: str,
        presentation_id: str,
        slide_id: Optional[str],
        element_id: Optional[str],
        quality: str,
        style: str,
        prompt: str,
        error_code: str,
        error_message: str
    ) -> Dict[str, Any]:
        """
        Record a failed generation (no credits charged).

        Args:
            generation_id: UUID of the generation attempt
            presentation_id: Presentation identifier
            slide_id: Slide identifier
            element_id: Element identifier
            quality: Quality tier attempted
            style: Style attempted
            prompt: Original prompt
            error_code: Error code
            error_message: Error message

        Returns:
            Dictionary with success status
        """
        return self.record_usage(
            generation_id=generation_id,
            presentation_id=presentation_id,
            slide_id=slide_id,
            element_id=element_id,
            credits_used=0,  # No credits for failed generations
            quality=quality,
            style=style,
            prompt=prompt,
            status="failed",
            error_code=error_code,
            error_message=error_message
        )

    # ========================================================================
    # Analytics
    # ========================================================================

    def get_usage_summary(self, presentation_id: str) -> Dict[str, Any]:
        """
        Get usage summary for a presentation.

        Args:
            presentation_id: Presentation identifier

        Returns:
            Dictionary with usage statistics
        """
        try:
            # Get credits balance
            credits = self.get_credits(presentation_id)

            # Get generation count
            count_response = self.client.table("image_generation_credits").select(
                "id", count="exact"
            ).eq("presentation_id", presentation_id).eq("status", "completed").execute()

            generation_count = count_response.count if hasattr(count_response, 'count') else 0

            # Get breakdown by quality
            quality_response = self.client.table("image_generation_credits").select(
                "quality, credits_used"
            ).eq("presentation_id", presentation_id).eq("status", "completed").execute()

            quality_breakdown = {}
            if quality_response.data:
                for record in quality_response.data:
                    q = record.get("quality", "unknown")
                    quality_breakdown[q] = quality_breakdown.get(q, 0) + 1

            return {
                "presentation_id": presentation_id,
                "credits": credits,
                "generation_count": generation_count,
                "quality_breakdown": quality_breakdown
            }

        except Exception as e:
            logger.error(f"Failed to get usage summary: {e}")
            return {
                "presentation_id": presentation_id,
                "credits": self.get_credits(presentation_id),
                "generation_count": 0,
                "quality_breakdown": {}
            }

    def get_recent_generations(
        self,
        presentation_id: str,
        limit: int = 10
    ) -> list:
        """
        Get recent generations for a presentation.

        Args:
            presentation_id: Presentation identifier
            limit: Maximum number of records

        Returns:
            List of generation records
        """
        try:
            response = self.client.table("image_generation_credits").select("*").eq(
                "presentation_id", presentation_id
            ).order("created_at", desc=True).limit(limit).execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Failed to get recent generations: {e}")
            return []


# ============================================================================
# Helper Functions
# ============================================================================

def get_credits_for_quality(quality: str) -> int:
    """
    Get credit cost for a quality tier.

    Args:
        quality: Quality tier (draft, standard, high, ultra)

    Returns:
        Number of credits required
    """
    return CREDITS_BY_QUALITY.get(quality, 2)


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Credits Service")
    print("===============")
    print(f"Credit costs by quality: {CREDITS_BY_QUALITY}")
    print(f"Default credits per presentation: {DEFAULT_CREDITS_PER_PRESENTATION}")

    # Test quality lookup
    for quality in ['draft', 'standard', 'high', 'ultra']:
        cost = get_credits_for_quality(quality)
        print(f"  {quality}: {cost} credits")
