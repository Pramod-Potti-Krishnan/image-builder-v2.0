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

    def upload_with_thumbnail(
        self,
        generation_id: str,
        image_bytes: bytes,
        thumbnail_bytes: bytes,
        folder: str = "layout-images",
        bucket: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload image and thumbnail to Supabase Storage.

        Creates a folder structure:
        {folder}/{generation_id}/original.png
        {folder}/{generation_id}/thumbnail.png

        Args:
            generation_id: Unique generation identifier
            image_bytes: Full image bytes
            thumbnail_bytes: Thumbnail image bytes
            folder: Root folder path (default: "layout-images")
            bucket: Override bucket (uses self.bucket if None)

        Returns:
            Dictionary with:
            - success: bool
            - image_url: str (full image public URL)
            - thumbnail_url: str (thumbnail public URL)
            - image_path: str (storage path for image)
            - thumbnail_path: str (storage path for thumbnail)
            - image_size_bytes: int
            - thumbnail_size_bytes: int
            - error: str (if failed)
        """
        target_bucket = bucket or self.bucket

        try:
            # Paths for image and thumbnail
            image_path = f"{folder}/{generation_id}/original.png"
            thumbnail_path = f"{folder}/{generation_id}/thumbnail.png"

            # Upload original image
            logger.info(f"Uploading image to: {image_path}")
            image_response = self.client.storage.from_(target_bucket).upload(
                path=image_path,
                file=image_bytes,
                file_options={"content-type": "image/png"}
            )

            # Upload thumbnail
            logger.info(f"Uploading thumbnail to: {thumbnail_path}")
            thumb_response = self.client.storage.from_(target_bucket).upload(
                path=thumbnail_path,
                file=thumbnail_bytes,
                file_options={"content-type": "image/png"}
            )

            # Get public URLs
            image_url = self.client.storage.from_(target_bucket).get_public_url(image_path)
            thumbnail_url = self.client.storage.from_(target_bucket).get_public_url(thumbnail_path)

            logger.info(f"Successfully uploaded image and thumbnail for {generation_id}")

            return {
                "success": True,
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "image_path": image_path,
                "thumbnail_path": thumbnail_path,
                "image_size_bytes": len(image_bytes),
                "thumbnail_size_bytes": len(thumbnail_bytes)
            }

        except Exception as e:
            logger.error(f"Upload with thumbnail failed for {generation_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def upload_layout_image(
        self,
        generation_id: str,
        image_bytes: bytes,
        thumbnail_bytes: Optional[bytes] = None,
        folder: str = "layout-images"
    ) -> Dict[str, Any]:
        """
        Upload a Layout Service generated image.

        Convenience wrapper that handles both with and without thumbnail.

        Args:
            generation_id: Unique generation identifier
            image_bytes: Full image bytes
            thumbnail_bytes: Optional thumbnail bytes
            folder: Root folder path

        Returns:
            Upload result dictionary
        """
        if thumbnail_bytes:
            return self.upload_with_thumbnail(
                generation_id=generation_id,
                image_bytes=image_bytes,
                thumbnail_bytes=thumbnail_bytes,
                folder=folder
            )
        else:
            # Upload just the image
            image_path = f"{folder}/{generation_id}/original.png"

            result = self.upload_image(
                image_bytes=image_bytes,
                filename=f"{generation_id}/original.png",
                folder=folder
            )

            if result["success"]:
                return {
                    "success": True,
                    "image_url": result["url"],
                    "thumbnail_url": result["url"],  # Same as image if no thumbnail
                    "image_path": result["path"],
                    "thumbnail_path": result["path"],
                    "image_size_bytes": len(image_bytes),
                    "thumbnail_size_bytes": len(image_bytes)
                }
            else:
                return result


# For testing purposes
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # This would require actual Supabase credentials
    print("Supabase Storage Service initialized")
    print("To test, provide SUPABASE_URL and SUPABASE_KEY environment variables")
