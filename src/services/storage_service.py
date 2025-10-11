"""
Supabase Storage Service
========================

Handles uploading images to Supabase Storage and generating public URLs.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

logger = logging.getLogger(__name__)


class SupabaseStorageService:
    """
    Service for uploading and managing images in Supabase Storage.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        bucket: Optional[str] = None
    ):
        """
        Initialize Supabase storage service.

        Args:
            url: Supabase project URL (defaults to SUPABASE_URL env var)
            key: Supabase API key (defaults to SUPABASE_KEY env var)
            bucket: Bucket name (defaults to SUPABASE_BUCKET env var or 'generated-images')
        """
        if not SUPABASE_AVAILABLE:
            raise ImportError("supabase not installed. Run: pip install supabase")

        self.url = url or os.getenv("SUPABASE_URL")
        # Use service key for storage operations (has full permissions)
        # Falls back to regular key if service key not available
        self.key = key or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and either SUPABASE_SERVICE_KEY or SUPABASE_KEY must be set")

        self.bucket = bucket or os.getenv("SUPABASE_BUCKET", "generated-images")

        # Initialize Supabase client
        self.client: Client = create_client(self.url, self.key)

        logger.info(f"Initialized Supabase Storage (bucket: {self.bucket})")

    def upload_image(
        self,
        image_bytes: bytes,
        filename: Optional[str] = None,
        folder: Optional[str] = None,
        content_type: str = "image/png",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload image to Supabase Storage.

        Args:
            image_bytes: Image data
            filename: Filename (auto-generated if None)
            folder: Optional folder path
            content_type: MIME type
            metadata: Optional metadata

        Returns:
            Dictionary with:
            - success: bool
            - path: str (storage path)
            - url: str (public URL)
            - error: str (if failed)
        """
        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                unique_id = str(uuid.uuid4())[:8]
                filename = f"image_{timestamp}_{unique_id}.png"

            # Build full path
            if folder:
                path = f"{folder}/{filename}"
            else:
                path = filename

            logger.info(f"Uploading image to Supabase: {path}")

            # Upload to Supabase Storage
            response = self.client.storage.from_(self.bucket).upload(
                path=path,
                file=image_bytes,
                file_options={"content-type": content_type}
            )

            # Get public URL
            public_url = self.client.storage.from_(self.bucket).get_public_url(path)

            logger.info(f"Successfully uploaded image: {public_url}")

            return {
                "success": True,
                "path": path,
                "url": public_url,
                "bucket": self.bucket,
                "size_bytes": len(image_bytes)
            }

        except Exception as e:
            logger.error(f"Supabase upload failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def upload_multiple_versions(
        self,
        image_id: str,
        images: Dict[str, bytes],
        folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload multiple versions of an image (original, cropped, transparent).

        Args:
            image_id: Unique identifier for this image set
            images: Dictionary mapping version names to image bytes
                    e.g., {"original": bytes, "cropped": bytes, "transparent": bytes}
            folder: Optional folder path

        Returns:
            Dictionary with:
            - success: bool
            - urls: Dict mapping version names to public URLs
            - paths: Dict mapping version names to storage paths
            - error: str (if failed)
        """
        try:
            urls = {}
            paths = {}

            for version_name, image_bytes in images.items():
                filename = f"{image_id}_{version_name}.png"

                result = self.upload_image(
                    image_bytes=image_bytes,
                    filename=filename,
                    folder=folder
                )

                if result["success"]:
                    urls[version_name] = result["url"]
                    paths[version_name] = result["path"]
                else:
                    logger.error(f"Failed to upload {version_name}: {result.get('error')}")

            if urls:
                return {
                    "success": True,
                    "urls": urls,
                    "paths": paths
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to upload any images"
                }

        except Exception as e:
            logger.error(f"Multiple upload failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def delete_image(self, path: str) -> Dict[str, Any]:
        """
        Delete an image from Supabase Storage.

        Args:
            path: Storage path

        Returns:
            Dictionary with success status
        """
        try:
            self.client.storage.from_(self.bucket).remove([path])

            logger.info(f"Deleted image: {path}")

            return {"success": True}

        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return {"success": False, "error": str(e)}

    def get_public_url(self, path: str) -> str:
        """Get public URL for a storage path."""
        return self.client.storage.from_(self.bucket).get_public_url(path)


# For testing purposes
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # This would require actual Supabase credentials
    print("Supabase Storage Service initialized")
    print("To test, provide SUPABASE_URL and SUPABASE_KEY environment variables")
