"""
Image Build Agent v2.0 - FastAPI Application
============================================

REST API microservice for AI image generation with:
- Custom aspect ratio support
- Supabase cloud storage
- Vertex AI Imagen 3 generation
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .models.image_models import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    BatchImageGenerationRequest,
    BatchImageGenerationResponse,
    HealthCheckResponse,
    ImagenModel
)
from .services.image_generation_service import ImageGenerationService
from .services.vertex_ai_service import VertexAIImageGenerator
from .services.storage_service import SupabaseStorageService
from .config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
image_service: Optional[ImageGenerationService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes services on startup, cleans up on shutdown.
    """
    global image_service

    # Startup
    logger.info("Initializing Image Build Agent v2.0...")

    try:
        settings = get_settings()

        # Initialize services
        vertex_ai = VertexAIImageGenerator(
            project_id=settings.google_cloud_project,
            location=settings.vertex_ai_location
        )

        storage = SupabaseStorageService(
            url=settings.supabase_url,
            key=settings.supabase_key,
            bucket=settings.supabase_bucket
        )

        image_service = ImageGenerationService(
            vertex_ai_generator=vertex_ai,
            storage_service=storage
        )

        logger.info("✅ Image Build Agent v2.0 initialized successfully")

    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Image Build Agent v2.0...")


# Create FastAPI application
app = FastAPI(
    title="Image Build Agent v2.0",
    description="AI-powered image generation with custom aspect ratios and cloud storage",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Key dependency
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key if API_KEYS is configured."""
    settings = get_settings()

    if settings.api_keys_list:
        if not x_api_key or x_api_key not in settings.api_keys_list:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

    return x_api_key


# Routes

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "service": "Image Build Agent v2.0",
        "status": "running",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.get("/api/v2/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns service health status and availability of dependencies.
    """
    try:
        settings = get_settings()

        # Check services
        services_status = {
            "vertex_ai": image_service is not None and image_service.vertex_ai is not None,
            "supabase": image_service is not None and image_service.storage is not None,
            "image_service": image_service is not None
        }

        # Determine overall status
        if all(services_status.values()):
            status = "healthy"
        elif any(services_status.values()):
            status = "degraded"
        else:
            status = "unhealthy"

        return HealthCheckResponse(
            status=status,
            version="2.0.0",
            services=services_status
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            version="2.0.0",
            services={}
        )


@app.post("/api/v2/generate", response_model=ImageGenerationResponse, tags=["Generation"])
async def generate_image(
    request: ImageGenerationRequest,
    _: str = Depends(verify_api_key)
):
    """
    Generate an image using AI.

    **Features**:
    - Custom aspect ratios (2:7, 21:9, etc.)
    - Intelligent cropping to achieve non-standard ratios
    - Optional background removal
    - Cloud storage with public URLs
    - High-quality Vertex AI Imagen 3 generation

    **Example Request**:
    ```json
    {
      "prompt": "A modern tech startup logo with blue gradient",
      "aspect_ratio": "2:7",
      "archetype": "minimalist_vector_art",
      "options": {
        "remove_background": true,
        "crop_anchor": "center",
        "store_in_cloud": true
      }
    }
    ```

    **Example Response**:
    ```json
    {
      "success": true,
      "image_id": "123e4567-e89b-12d3-a456-426614174000",
      "urls": {
        "original": "https://...",
        "cropped": "https://...",
        "transparent": "https://..."
      },
      "metadata": {
        "model": "imagen-3.0-generate-002",
        "generation_time_ms": 8500,
        ...
      }
    }
    ```
    """
    if not image_service:
        raise HTTPException(status_code=503, detail="Image generation service not initialized")

    try:
        logger.info(f"Received generation request: {request.prompt[:50]}...")

        response = await image_service.generate(request)

        if not response.success:
            raise HTTPException(status_code=500, detail=response.error)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/generate-batch", response_model=BatchImageGenerationResponse, tags=["Image Generation"])
async def generate_images_batch(
    batch_request: BatchImageGenerationRequest,
    _: str = Depends(verify_api_key)
):
    """
    Generate multiple images with automatic rate limiting.

    Generates multiple images concurrently while respecting Vertex AI quota limits.
    Uses semaphore-based rate limiting to prevent concurrent request quota errors.

    **Features:**
    - Automatic rate limiting (default: 5 concurrent requests)
    - Configurable concurrency (1-10)
    - Individual error handling per image
    - Batch progress tracking

    **Example Request:**
    ```json
    {
      "requests": [
        {
          "prompt": "A beautiful sunset",
          "aspect_ratio": "16:9",
          "model": "imagen-3.0-fast-generate-001"
        },
        {
          "prompt": "A mountain landscape",
          "aspect_ratio": "1:1",
          "model": "imagen-3.0-generate-002"
        }
      ],
      "max_concurrent": 5
    }
    ```

    **Quota Management:**
    - Default concurrent limit: 5 (prevents quota errors)
    - Recommended for 6-50 images
    - Automatically batches larger requests
    """
    if not image_service:
        raise HTTPException(status_code=503, detail="Image generation service not initialized")

    try:
        logger.info(f"Received batch generation request: {len(batch_request.requests)} images")

        response = await image_service.generate_batch(batch_request)

        # Return response even if some failed (check response.success for overall status)
        return response

    except Exception as e:
        logger.error(f"Batch generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/models", tags=["Configuration"])
async def list_available_models():
    """
    List available Imagen models with details.

    Returns information about all available Imagen models including:
    - Model names and versions
    - Cost per image
    - Generation speed
    - Quality tier

    **Example Response:**
    ```json
    {
      "models": [
        {
          "name": "imagen-3.0-fast-generate-001",
          "display_name": "Imagen 3.0 Fast (Default)",
          "cost_per_image": 0.02,
          "speed": "Fast (3-5s)",
          "recommended": true
        },
        ...
      ]
    }
    ```
    """
    models = []
    for model in ImagenModel:
        models.append({
            "name": model.value,
            "display_name": model.display_name,
            "cost_per_image": model.cost_per_image,
            "speed": model.generation_speed,
            "recommended": model == ImagenModel.IMAGEN_3_FAST
        })

    return {
        "models": models,
        "default": ImagenModel.IMAGEN_3_FAST.value
    }


@app.get("/api/v2/images/{image_id}", tags=["Images"])
async def get_image(image_id: str, _: str = Depends(verify_api_key)):
    """
    Get metadata for a generated image.

    Note: In this version, we don't persist metadata to a database.
    This endpoint is a placeholder for future database integration.
    """
    # TODO: Implement database lookup
    raise HTTPException(status_code=501, detail="Database integration not yet implemented")


@app.get("/api/v2/images", tags=["Images"])
async def list_images(_: str = Depends(verify_api_key)):
    """
    List generated images.

    Note: Requires database integration (future enhancement).
    """
    # TODO: Implement database query
    raise HTTPException(status_code=501, detail="Database integration not yet implemented")


@app.delete("/api/v2/images/{image_id}", tags=["Images"])
async def delete_image(image_id: str, _: str = Depends(verify_api_key)):
    """
    Delete a generated image.

    Note: Requires database integration (future enhancement).
    """
    # TODO: Implement delete with database cleanup
    raise HTTPException(status_code=501, detail="Database integration not yet implemented")


# Error handlers

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


# Main entry point for development
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
