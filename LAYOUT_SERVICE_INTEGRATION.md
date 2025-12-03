# Layout Service Integration - Image Builder v2.1

**Documentation File:** `/Users/pk1980/Documents/Software/deckster-backend/deckster-w-content-strategist/agents/image_builder/v2.0/LAYOUT_SERVICE_INTEGRATION.md`

## Overview

This document describes the new Layout Service integration endpoint added to Image Builder v2.1. This endpoint allows the Layout Service orchestrator to request AI-generated images with style presets, quality tiers, and credit tracking.

---

## Implementation Summary

**Base Path:** `/Users/pk1980/Documents/Software/deckster-backend/deckster-w-content-strategist/agents/image_builder/v2.0`

### Files Created

| File | Full Path | Purpose |
|------|-----------|---------|
| `layout_service_models.py` | `/Users/pk1980/Documents/Software/deckster-backend/deckster-w-content-strategist/agents/image_builder/v2.0/src/models/layout_service_models.py` | Pydantic request/response models for Layout Service |
| `style_engine.py` | `/Users/pk1980/Documents/Software/deckster-backend/deckster-w-content-strategist/agents/image_builder/v2.0/src/services/style_engine.py` | Style-to-prompt mapping with 5 visual styles |
| `thumbnail_service.py` | `/Users/pk1980/Documents/Software/deckster-backend/deckster-w-content-strategist/agents/image_builder/v2.0/src/services/thumbnail_service.py` | 256px thumbnail generation using PIL |
| `credits_service.py` | `/Users/pk1980/Documents/Software/deckster-backend/deckster-w-content-strategist/agents/image_builder/v2.0/src/services/credits_service.py` | Per-presentation credit tracking |
| `layout_generation_service.py` | `/Users/pk1980/Documents/Software/deckster-backend/deckster-w-content-strategist/agents/image_builder/v2.0/src/services/layout_generation_service.py` | Main orchestration service |
| `001_add_credits_tracking.sql` | `/Users/pk1980/Documents/Software/deckster-backend/deckster-w-content-strategist/agents/image_builder/v2.0/database/migrations/001_add_credits_tracking.sql` | PostgreSQL schema for credits |

### Files Modified

| File | Full Path | Changes |
|------|-----------|---------|
| `main.py` | `/Users/pk1980/Documents/Software/deckster-backend/deckster-w-content-strategist/agents/image_builder/v2.0/src/main.py` | Added 3 new endpoints, updated version to 2.1.0 |
| `settings.py` | `/Users/pk1980/Documents/Software/deckster-backend/deckster-w-content-strategist/agents/image_builder/v2.0/src/config/settings.py` | Added Layout Service settings |
| `storage_service.py` | `/Users/pk1980/Documents/Software/deckster-backend/deckster-w-content-strategist/agents/image_builder/v2.0/src/services/storage_service.py` | Added `upload_with_thumbnail()` method |

---

## New API Endpoints

### 1. Generate Image - `POST /api/ai/image/generate`

Main endpoint for Layout Service to request AI-generated images.

**Base URL:** `http://your-image-service:8000/api/ai/image/generate`

### 2. List Styles - `GET /api/ai/image/styles`

Returns available visual styles with descriptions.

### 3. Get Credits - `GET /api/ai/image/credits/{presentation_id}`

Returns credit balance for a presentation.

---

## Request/Response Schema

### Request Body

```json
{
  "prompt": "A team collaborating in a modern office space",
  "presentationId": "pres-abc123",
  "slideId": "slide-001",
  "elementId": "img-hero-001",
  "context": {
    "title": "Q4 Business Review",
    "theme": "corporate",
    "slideTitle": "Team Collaboration",
    "slideIndex": 3,
    "brandColors": ["#1a73e8", "#ffffff", "#4285f4"]
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
    "lighting": "natural",
    "negativePrompt": "text, watermark"
  }
}
```

### Success Response

```json
{
  "success": true,
  "data": {
    "generationId": "550e8400-e29b-41d4-a716-446655440000",
    "images": [{
      "id": "img-550e8400",
      "url": "https://your-supabase.storage.co/layout-images/550e8400.../original.png",
      "thumbnailUrl": "https://your-supabase.storage.co/layout-images/550e8400.../thumbnail.png",
      "width": 1536,
      "height": 864,
      "format": "png",
      "sizeBytes": 2457600
    }],
    "metadata": {
      "prompt": "A team collaborating in a modern office space",
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

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_CREDITS",
    "message": "Not enough credits. Required: 4, Available: 2",
    "retryable": false,
    "suggestion": "Upgrade your plan or use a lower quality tier"
  }
}
```

---

## Configuration Options

### Styles

| Style | Description | Best For |
|-------|-------------|----------|
| `realistic` | Photorealistic with natural lighting | Business, corporate, professional |
| `illustration` | Digital art with clean vector graphics | Creative, educational, infographics |
| `abstract` | Artistic interpretation of concepts | Creative, backgrounds, conceptual |
| `minimal` | Clean design with simple shapes | Tech, startup, modern, icons |
| `photo` | Professional stock photography style | Business, corporate, marketing |

### Quality Tiers

| Quality | Resolution | Credits | Use Case |
|---------|------------|---------|----------|
| `draft` | 512px | 1 | Previews, quick iterations |
| `standard` | 1024px | 2 | Most presentations |
| `high` | 1536px | 4 | High-quality exports |
| `ultra` | 2048px | 8 | Print, large displays |

### Aspect Ratios

Standard ratios: `1:1`, `4:3`, `3:2`, `16:9`, `9:16`, `3:4`, `2:3`

Custom ratios: Set `aspectRatio: "custom"` and use `gridWidth`/`gridHeight` constraints.

### Color Schemes

| Scheme | Effect |
|--------|--------|
| `warm` | Orange/golden tones |
| `cool` | Blue/cyan tones |
| `neutral` | Grayscale/earth tones |
| `vibrant` | Bold, saturated colors |

### Lighting

| Lighting | Effect |
|----------|--------|
| `natural` | Daylight, outdoor feel |
| `studio` | Professional, even lighting |
| `dramatic` | High contrast, shadows |
| `soft` | Diffused, gentle illumination |

---

## Error Codes

| Code | Retryable | Description |
|------|-----------|-------------|
| `INSUFFICIENT_CREDITS` | No | Presentation has run out of credits |
| `INVALID_STYLE` | No | Unknown style specified |
| `GENERATION_FAILED` | Yes | AI generation error (retry may help) |
| `STORAGE_ERROR` | Yes | Upload to storage failed |
| `INTERNAL_ERROR` | Yes | Unexpected server error |

---

## Layout Service Orchestrator Integration

### Python Integration Example

```python
import httpx
from typing import Optional, Dict, Any

class ImageServiceClient:
    """Client for calling the Image AI Service from Layout Service."""

    def __init__(self, base_url: str = "http://image-service:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def generate_image(
        self,
        prompt: str,
        presentation_id: str,
        slide_id: str,
        element_id: str,
        style: str = "realistic",
        aspect_ratio: str = "16:9",
        quality: str = "standard",
        grid_width: Optional[int] = None,
        grid_height: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate an AI image for a layout element.

        Args:
            prompt: Description of the image to generate
            presentation_id: ID of the presentation
            slide_id: ID of the slide
            element_id: ID of the image element
            style: Visual style (realistic, illustration, abstract, minimal, photo)
            aspect_ratio: Target aspect ratio (16:9, 4:3, 1:1, etc.) or "custom"
            quality: Quality tier (draft, standard, high, ultra)
            grid_width: Grid width for custom aspect ratios (1-12)
            grid_height: Grid height for custom aspect ratios (1-8)
            context: Optional presentation context (title, theme, brandColors)
            options: Optional generation options (colorScheme, lighting, negativePrompt)

        Returns:
            Response dict with success, data, or error
        """
        payload = {
            "prompt": prompt,
            "presentationId": presentation_id,
            "slideId": slide_id,
            "elementId": element_id,
            "context": context or {},
            "config": {
                "style": style,
                "aspectRatio": aspect_ratio,
                "quality": quality
            },
            "constraints": {
                "gridWidth": grid_width or 12,
                "gridHeight": grid_height or 8
            }
        }

        if options:
            payload["options"] = options

        response = await self.client.post(
            f"{self.base_url}/api/ai/image/generate",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    async def get_styles(self) -> Dict[str, Any]:
        """Get available image styles."""
        response = await self.client.get(f"{self.base_url}/api/ai/image/styles")
        response.raise_for_status()
        return response.json()

    async def get_credits(self, presentation_id: str) -> Dict[str, Any]:
        """Get credit balance for a presentation."""
        response = await self.client.get(
            f"{self.base_url}/api/ai/image/credits/{presentation_id}"
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Usage in Layout Service Orchestrator
async def generate_hero_image(orchestrator, slide_data):
    """Example: Generate hero image for a slide."""

    client = ImageServiceClient(base_url="http://image-service:8000")

    try:
        # Check credits first
        credits = await client.get_credits(slide_data["presentation_id"])
        if credits["remainingCredits"] < 4:  # High quality needs 4 credits
            quality = "standard"  # Fall back to standard (2 credits)
        else:
            quality = "high"

        # Generate the image
        result = await client.generate_image(
            prompt=slide_data["image_prompt"],
            presentation_id=slide_data["presentation_id"],
            slide_id=slide_data["slide_id"],
            element_id=f"hero-img-{slide_data['slide_id']}",
            style="realistic",
            aspect_ratio="16:9",
            quality=quality,
            context={
                "title": slide_data.get("presentation_title"),
                "theme": slide_data.get("theme", "corporate"),
                "slideTitle": slide_data.get("slide_title"),
                "slideIndex": slide_data.get("slide_index", 0),
                "brandColors": slide_data.get("brand_colors", [])
            },
            options={
                "colorScheme": "warm",
                "lighting": "natural"
            }
        )

        if result["success"]:
            image_data = result["data"]["images"][0]
            return {
                "success": True,
                "image_url": image_data["url"],
                "thumbnail_url": image_data["thumbnailUrl"],
                "width": image_data["width"],
                "height": image_data["height"],
                "credits_used": result["data"]["usage"]["creditsUsed"],
                "credits_remaining": result["data"]["usage"]["creditsRemaining"]
            }
        else:
            return {
                "success": False,
                "error": result["error"]["message"],
                "retryable": result["error"]["retryable"]
            }

    finally:
        await client.close()
```

### TypeScript Integration Example

```typescript
interface ImageGenerationRequest {
  prompt: string;
  presentationId: string;
  slideId: string;
  elementId: string;
  context?: {
    title?: string;
    theme?: string;
    slideTitle?: string;
    slideIndex?: number;
    brandColors?: string[];
  };
  config: {
    style: 'realistic' | 'illustration' | 'abstract' | 'minimal' | 'photo';
    aspectRatio: string;
    quality: 'draft' | 'standard' | 'high' | 'ultra';
  };
  constraints: {
    gridWidth: number;
    gridHeight: number;
  };
  options?: {
    colorScheme?: 'warm' | 'cool' | 'neutral' | 'vibrant';
    lighting?: 'natural' | 'studio' | 'dramatic' | 'soft';
    negativePrompt?: string;
  };
}

interface ImageGenerationResponse {
  success: boolean;
  data?: {
    generationId: string;
    images: Array<{
      id: string;
      url: string;
      thumbnailUrl: string;
      width: number;
      height: number;
      format: string;
      sizeBytes: number;
    }>;
    metadata: {
      prompt: string;
      style: string;
      aspectRatio: string;
      dimensions: { width: number; height: number };
      provider: string;
      model: string;
      generationTime: number;
    };
    usage: {
      creditsUsed: number;
      creditsRemaining: number;
    };
  };
  error?: {
    code: string;
    message: string;
    retryable: boolean;
    suggestion?: string;
  };
}

class ImageServiceClient {
  constructor(private baseUrl: string = 'http://image-service:8000') {}

  async generateImage(request: ImageGenerationRequest): Promise<ImageGenerationResponse> {
    const response = await fetch(`${this.baseUrl}/api/ai/image/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return response.json();
  }

  async getStyles(): Promise<{ styles: any[]; default: string }> {
    const response = await fetch(`${this.baseUrl}/api/ai/image/styles`);
    return response.json();
  }

  async getCredits(presentationId: string): Promise<{
    presentationId: string;
    totalCredits: number;
    usedCredits: number;
    remainingCredits: number;
  }> {
    const response = await fetch(`${this.baseUrl}/api/ai/image/credits/${presentationId}`);
    return response.json();
  }
}

// Usage example
const imageClient = new ImageServiceClient('http://localhost:8000');

const result = await imageClient.generateImage({
  prompt: 'A team meeting in a modern office',
  presentationId: 'pres-123',
  slideId: 'slide-001',
  elementId: 'hero-img',
  config: {
    style: 'realistic',
    aspectRatio: '16:9',
    quality: 'high',
  },
  constraints: {
    gridWidth: 12,
    gridHeight: 6,
  },
});

if (result.success) {
  console.log('Image URL:', result.data.images[0].url);
  console.log('Thumbnail:', result.data.images[0].thumbnailUrl);
  console.log('Credits remaining:', result.data.usage.creditsRemaining);
}
```

### cURL Examples

```bash
# Generate an image
curl -X POST "http://localhost:8000/api/ai/image/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A modern tech startup workspace",
    "presentationId": "pres-test-001",
    "slideId": "slide-1",
    "elementId": "hero-img",
    "context": {
      "title": "Quarterly Review",
      "theme": "modern"
    },
    "config": {
      "style": "realistic",
      "aspectRatio": "16:9",
      "quality": "standard"
    },
    "constraints": {
      "gridWidth": 12,
      "gridHeight": 6
    }
  }'

# List available styles
curl "http://localhost:8000/api/ai/image/styles"

# Check credits for a presentation
curl "http://localhost:8000/api/ai/image/credits/pres-test-001"

# Health check
curl "http://localhost:8000/api/v2/health"
```

---

## Database Setup (Required)

Before using credits tracking, run the migration in your Supabase PostgreSQL:

```bash
# File: database/migrations/001_add_credits_tracking.sql
# Execute this in your Supabase SQL Editor
```

This creates:
- `image_generation_credits` table - tracks each generation
- `presentation_credits` table - tracks credit allocations
- Helper functions for atomic credit operations
- Indexes for performance

---

## Environment Variables

Add these to your `.env` file:

```bash
# Layout Service Settings (already in v2.0)
LAYOUT_IMAGES_BUCKET=layout-images
DEFAULT_CREDITS_PER_PRESENTATION=100
ENABLE_CREDITS_TRACKING=true
THUMBNAIL_SIZE=256
```

---

## Version History

| Version | Changes |
|---------|---------|
| v2.0.0 | Original image builder with v2 API |
| v2.1.0 | Added Layout Service integration endpoint |

---

## Support

For issues or questions, contact the Image Builder team or check the `/docs` endpoint on the running service for interactive API documentation.
