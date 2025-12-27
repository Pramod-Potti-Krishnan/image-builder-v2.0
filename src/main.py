"""
Image Build Agent v2.1 - FastAPI Application
============================================

REST API microservice for AI image generation with:
- Custom aspect ratio support
- Supabase cloud storage
- Vertex AI Imagen 3 generation
- Layout Service integration with style mapping and credits
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
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
from .models.layout_service_models import (
    LayoutImageGenerateRequest,
    LayoutImageGenerateResponse,
    ErrorCodes
)
from .services.image_generation_service import ImageGenerationService
from .services.vertex_ai_service import VertexAIImageGenerator
from .services.storage_service import SupabaseStorageService
from .services.layout_generation_service import LayoutGenerationService
from .services.credits_service import CreditsService
from .services.style_engine import get_style_names, get_style_descriptions
from .config.settings import get_settings
from .middleware.ip_allowlist import IPAllowlistMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
image_service: Optional[ImageGenerationService] = None
layout_service: Optional[LayoutGenerationService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes services on startup, cleans up on shutdown.
    """
    global image_service, layout_service

    # Startup
    logger.info("Initializing Image Build Agent v2.1...")

    try:
        settings = get_settings()

        # Initialize core services
        vertex_ai = VertexAIImageGenerator(
            project_id=settings.google_cloud_project,
            location=settings.vertex_ai_location
        )

        storage = SupabaseStorageService(
            url=settings.supabase_url,
            key=settings.supabase_key,
            bucket=settings.supabase_bucket
        )

        # Initialize original image service (v2 API)
        image_service = ImageGenerationService(
            vertex_ai_generator=vertex_ai,
            storage_service=storage
        )

        # Initialize Layout Service components
        credits_service = None
        if settings.enable_credits_tracking:
            try:
                credits_service = CreditsService(
                    default_credits=settings.default_credits_per_presentation
                )
                logger.info("✅ Credits tracking enabled")
            except Exception as e:
                logger.warning(f"Credits service not available: {e}")

        # Initialize Layout Generation Service
        layout_service = LayoutGenerationService(
            vertex_ai_generator=vertex_ai,
            storage_service=storage,
            credits_service=credits_service,
            enable_credits=settings.enable_credits_tracking,
            thumbnail_size=settings.thumbnail_size
        )

        logger.info("✅ Image Build Agent v2.1 initialized successfully")
        logger.info(f"   - Layout Service: enabled")
        logger.info(f"   - Credits tracking: {settings.enable_credits_tracking}")
        logger.info(f"   - Thumbnail size: {settings.thumbnail_size}px")

    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Image Build Agent v2.1...")


# Create FastAPI application
app = FastAPI(
    title="Image Build Agent v2.1",
    description="AI-powered image generation with custom aspect ratios, cloud storage, and Layout Service integration",
    version="2.1.0",
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

# Add IP Allowlist middleware (security layer)
# This replaces API_KEYS authentication with IP-based access control
settings_for_middleware = get_settings()
app.add_middleware(
    IPAllowlistMiddleware,
    allowed_ips=settings_for_middleware.allowed_ips_list,
    allow_local=settings_for_middleware.allow_local_ips,
    enable_allowlist=settings_for_middleware.enable_ip_allowlist
)


# Note: API Key authentication has been replaced with IP Allowlist middleware
# All security is now handled at the middleware level based on allowed IPs
# This provides better security for internal service-to-service communication


# Routes

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "service": "Image Build Agent v2.1",
        "status": "running",
        "version": "2.1.0",
        "docs": "/docs",
        "endpoints": {
            "v2_generate": "/api/v2/generate",
            "v2_batch": "/api/v2/generate-batch",
            "v2_models": "/api/v2/models",
            "layout_generate": "/api/ai/image/generate",
            "layout_styles": "/api/ai/image/styles",
            "layout_credits": "/api/ai/image/credits/{presentation_id}",
            "health": "/api/v2/health"
        }
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
            "image_service": image_service is not None,
            "layout_service": layout_service is not None
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
            version="2.1.0",
            services=services_status
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            version="2.1.0",
            services={}
        )


@app.post("/api/v2/generate", response_model=ImageGenerationResponse, tags=["Generation"])
async def generate_image(request: ImageGenerationRequest):
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
async def generate_images_batch(batch_request: BatchImageGenerationRequest):
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


# ============================================================================
# Layout Service Endpoints
# ============================================================================

@app.post("/api/ai/image/generate", response_model=LayoutImageGenerateResponse, tags=["Layout Service"])
async def generate_layout_image(request: LayoutImageGenerateRequest):
    """
    Generate an image for Layout Service.

    This endpoint is optimized for the Layout Service with:
    - Style-based prompt enhancement (realistic, illustration, abstract, minimal, photo)
    - Quality tiers with credit costs (draft=1, standard=2, high=4, ultra=8)
    - Automatic thumbnail generation (256px)
    - Grid-based aspect ratio calculation
    - Credits tracking per presentation

    **Example Request:**
    ```json
    {
      "prompt": "A team meeting in a modern office",
      "presentationId": "pres-123",
      "slideId": "slide-456",
      "elementId": "img-789",
      "context": {
        "title": "Q4 Business Review",
        "theme": "corporate",
        "slideTitle": "Team Collaboration",
        "slideIndex": 3,
        "brandColors": ["#1a73e8", "#ffffff"]
      },
      "config": {
        "style": "realistic",
        "aspectRatio": "16:9",
        "quality": "high"
      },
      "constraints": {
        "gridWidth": 8,
        "gridHeight": 6
      },
      "options": {
        "colorScheme": "warm",
        "lighting": "natural"
      }
    }
    ```

    **Example Response:**
    ```json
    {
      "success": true,
      "data": {
        "generationId": "550e8400-e29b-41d4-a716-446655440000",
        "images": [{
          "id": "img-001",
          "url": "https://.../layout-images/550e8400.../original.png",
          "thumbnailUrl": "https://.../layout-images/550e8400.../thumbnail.png",
          "width": 1536,
          "height": 864,
          "format": "png",
          "sizeBytes": 2457600
        }],
        "metadata": {
          "prompt": "A team meeting in a modern office",
          "style": "realistic",
          "aspectRatio": "16:9",
          "dimensions": {"width": 1536, "height": 864},
          "provider": "vertex-ai",
          "model": "imagen-3.0-fast-generate-001",
          "generationTime": 4523
        },
        "usage": {
          "creditsUsed": 4,
          "creditsRemaining": 96
        }
      }
    }
    ```

    **Error Codes:**
    - `INSUFFICIENT_CREDITS`: Not enough credits (not retryable)
    - `INVALID_STYLE`: Unknown style specified (not retryable)
    - `GENERATION_FAILED`: AI generation error (retryable)
    - `STORAGE_ERROR`: Upload failed (retryable)
    - `INTERNAL_ERROR`: Unexpected error (retryable)
    """
    if not layout_service:
        raise HTTPException(
            status_code=503,
            detail="Layout generation service not initialized"
        )

    try:
        logger.info(
            f"Layout generation request: presentation={request.presentationId}, "
            f"style={request.config.style}, quality={request.config.quality}"
        )

        response = await layout_service.generate(request)

        if not response.success and response.error:
            # Return structured error response (don't raise HTTPException)
            # This allows the Layout Service to handle errors gracefully
            logger.warning(
                f"Layout generation failed: {response.error.code} - {response.error.message}"
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Layout generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/image/styles", tags=["Layout Service"])
async def list_available_styles():
    """
    List available image styles for Layout Service.

    Returns all available styles with descriptions and prompt modifiers.
    Use these style names in the `config.style` field of generation requests.

    **Example Response:**
    ```json
    {
      "styles": [
        {
          "name": "realistic",
          "description": "Photorealistic images with natural lighting",
          "recommended_for": ["business", "corporate", "professional"]
        },
        {
          "name": "illustration",
          "description": "Digital illustration with clean vector-style graphics",
          "recommended_for": ["creative", "educational", "playful"]
        },
        ...
      ],
      "default": "realistic"
    }
    ```
    """
    styles = []
    style_names = get_style_names()
    style_descriptions = get_style_descriptions()

    for name in style_names:
        desc = style_descriptions.get(name, {})
        styles.append({
            "name": name,
            "description": desc.get("description", ""),
            "recommended_for": desc.get("recommended_for", [])
        })

    return {
        "styles": styles,
        "default": "realistic"
    }


@app.get("/api/ai/image/credits/{presentation_id}", tags=["Layout Service"])
async def get_presentation_credits(presentation_id: str):
    """
    Get credit balance for a presentation.

    Returns the current credit status including total, used, and remaining credits.

    **Example Response:**
    ```json
    {
      "presentationId": "pres-123",
      "totalCredits": 100,
      "usedCredits": 12,
      "remainingCredits": 88
    }
    ```
    """
    if not layout_service or not layout_service.credits:
        return {
            "presentationId": presentation_id,
            "totalCredits": 100,
            "usedCredits": 0,
            "remainingCredits": 100,
            "note": "Credits tracking not enabled"
        }

    try:
        credits = layout_service.credits.get_credits(presentation_id)
        return {
            "presentationId": presentation_id,
            "totalCredits": credits["total_credits"],
            "usedCredits": credits["used_credits"],
            "remainingCredits": credits["remaining_credits"]
        }
    except Exception as e:
        logger.error(f"Failed to get credits for {presentation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Original v2 API Endpoints (Database placeholders)
# ============================================================================

@app.get("/api/v2/images/{image_id}", tags=["Images"])
async def get_image(image_id: str):
    """
    Get metadata for a generated image.

    Note: In this version, we don't persist metadata to a database.
    This endpoint is a placeholder for future database integration.
    """
    # TODO: Implement database lookup
    raise HTTPException(status_code=501, detail="Database integration not yet implemented")


@app.get("/api/v2/images", tags=["Images"])
async def list_images():
    """
    List generated images.

    Note: Requires database integration (future enhancement).
    """
    # TODO: Implement database query
    raise HTTPException(status_code=501, detail="Database integration not yet implemented")


@app.delete("/api/v2/images/{image_id}", tags=["Images"])
async def delete_image(image_id: str):
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
