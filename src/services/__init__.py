"""Services for Image Build Agent v2.0"""

from .vertex_ai_service import VertexAIImageGenerator
from .gemini_image_service import GeminiImageGenerator
from .storage_service import SupabaseStorageService
from .image_generation_service import ImageGenerationService
from .aspect_ratio_engine import get_aspect_ratio_strategy, crop_image_to_aspect_ratio
from .illustration_processor import IllustrationProcessor
from .illustration_service import IllustrationGenerationService

__all__ = [
    "VertexAIImageGenerator",
    "GeminiImageGenerator",
    "SupabaseStorageService",
    "ImageGenerationService",
    "get_aspect_ratio_strategy",
    "crop_image_to_aspect_ratio",
    # Illustration services
    "IllustrationProcessor",
    "IllustrationGenerationService",
]
