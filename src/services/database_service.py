"""
Database Service for Image Metadata
====================================

Handles saving and retrieving image generation metadata from Supabase PostgreSQL.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

logger = logging.getLogger(__name__)


class ImageDatabaseService:
    """
    Service for managing image metadata in Supabase PostgreSQL.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None
    ):
        """
        Initialize database service.

        Args:
            url: Supabase project URL
            key: Supabase API key (preferably service key)
        """
        if not SUPABASE_AVAILABLE:
            raise ImportError("supabase not installed. Run: pip install supabase")

        import os
        from dotenv import load_dotenv
        load_dotenv()  # Load environment variables from .env file

        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

        # Initialize Supabase client
        self.client: Client = create_client(self.url, self.key)

        logger.info("Initialized Image Database Service")

    def save_image_record(
        self,
        image_id: str,
        prompt: str,
        aspect_ratio: str,
        archetype: str,
        source_aspect_ratio: str,
        target_aspect_ratio: str,
        urls: Optional[Dict[str, str]] = None,
        paths: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Save image generation record to database.

        Args:
            image_id: Unique image identifier
            prompt: Generation prompt
            aspect_ratio: Requested aspect ratio
            archetype: Image archetype
            source_aspect_ratio: Actual generation aspect ratio
            target_aspect_ratio: Target aspect ratio after cropping
            urls: Dictionary of image URLs (original, cropped, transparent)
            paths: Dictionary of storage paths
            metadata: Additional metadata
            **kwargs: Additional fields (generation_time_ms, file sizes, etc.)

        Returns:
            Dictionary with success status and record data
        """
        try:
            # Prepare record data
            record = {
                "image_id": image_id,
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "archetype": archetype,
                "source_aspect_ratio": source_aspect_ratio,
                "target_aspect_ratio": target_aspect_ratio,
            }

            # Add URLs if provided
            if urls:
                record["original_url"] = urls.get("original")
                record["cropped_url"] = urls.get("cropped")
                record["transparent_url"] = urls.get("transparent")

            # Add paths if provided
            if paths:
                record["original_path"] = paths.get("original")
                record["cropped_path"] = paths.get("cropped")
                record["transparent_path"] = paths.get("transparent")

            # Add optional fields from kwargs
            optional_fields = [
                "negative_prompt",
                "crop_anchor",
                "model",
                "platform",
                "generation_time_ms",
                "original_size_bytes",
                "cropped_size_bytes",
                "transparent_size_bytes",
                "background_removed",
                "cropped",
                "created_by",
                "tags"
            ]

            for field in optional_fields:
                if field in kwargs and kwargs[field] is not None:
                    record[field] = kwargs[field]

            # Add metadata as JSONB
            if metadata:
                record["metadata"] = metadata

            # Insert into database
            response = self.client.table("generated_images").insert(record).execute()

            logger.info(f"Saved image record to database: {image_id}")

            return {
                "success": True,
                "record": response.data[0] if response.data else None
            }

        except Exception as e:
            logger.error(f"Failed to save image record: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_image_by_id(self, image_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve image record by image_id.

        Args:
            image_id: Unique image identifier

        Returns:
            Image record or None if not found
        """
        try:
            response = self.client.table("generated_images").select("*").eq("image_id", image_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]

            return None

        except Exception as e:
            logger.error(f"Failed to retrieve image: {e}")
            return None

    def list_images(
        self,
        limit: int = 50,
        offset: int = 0,
        archetype: Optional[str] = None,
        aspect_ratio: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List image records with optional filtering.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            archetype: Filter by archetype
            aspect_ratio: Filter by aspect ratio

        Returns:
            List of image records
        """
        try:
            query = self.client.table("generated_images").select("*")

            # Apply filters
            if archetype:
                query = query.eq("archetype", archetype)

            if aspect_ratio:
                query = query.eq("aspect_ratio", aspect_ratio)

            # Order by created_at descending
            query = query.order("created_at", desc=True)

            # Apply pagination
            query = query.range(offset, offset + limit - 1)

            response = query.execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Failed to list images: {e}")
            return []

    def delete_image_record(self, image_id: str) -> bool:
        """
        Delete image record from database.

        Args:
            image_id: Unique image identifier

        Returns:
            True if deleted successfully
        """
        try:
            self.client.table("generated_images").delete().eq("image_id", image_id).execute()

            logger.info(f"Deleted image record: {image_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete image record: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about generated images.

        Returns:
            Dictionary with statistics
        """
        try:
            # Total count
            count_response = self.client.table("generated_images").select("id", count="exact").execute()
            total_count = count_response.count if hasattr(count_response, 'count') else 0

            # Count by archetype
            archetype_response = self.client.table("generated_images").select("archetype").execute()
            archetypes = {}
            if archetype_response.data:
                for record in archetype_response.data:
                    arch = record.get("archetype", "unknown")
                    archetypes[arch] = archetypes.get(arch, 0) + 1

            return {
                "total_images": total_count,
                "by_archetype": archetypes
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_images": 0,
                "by_archetype": {}
            }


# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Image Database Service initialized")
    print("To test, provide SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables")
