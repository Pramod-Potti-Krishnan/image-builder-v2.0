# Image Builder v2.0 API Documentation

## Base URL
```
https://web-production-1b5df.up.railway.app
```

## Overview
AI-powered image generation API using Google Vertex AI. Supports two generation backends:

| Generator | Model | Status | Aspect Ratios |
|-----------|-------|--------|---------------|
| **Gemini 2.5 Flash Image** | `gemini-2.5-flash-image` | **Default** | 10 native ratios |
| Imagen 3 | `imagen-3.0-fast-generate-001` | Fallback | 5 native ratios |

Generates high-quality images with custom aspect ratios, automatic cloud storage, and background removal capabilities.

---

## Authentication

**No authentication required** for authorized services. Access is controlled via IP allowlist at the network level.

Your service IP has been pre-authorized - simply make requests directly to the API endpoints.

---

## Endpoints

### 1. Health Check

Check API status and service availability.

**Endpoint**: `GET /api/v2/health`

**Request**:
```bash
curl https://web-production-1b5df.up.railway.app/api/v2/health
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "version": "2.1.0",
  "services": {
    "vertex_ai": true,
    "supabase": true,
    "image_service": true
  },
  "generator": "gemini",
  "timestamp": "2025-12-27T15:21:45.655410"
}
```

---

### 2. Generate Image

Generate AI images with custom specifications.

**Endpoint**: `POST /api/v2/generate`

**Content-Type**: `application/json`

#### Request Body

```typescript
{
  // Required
  "prompt": string,              // Image description (what to generate)

  // Optional - Aspect Ratio
  "aspect_ratio": string,        // Default: "16:9"
                                 // Gemini native: "1:1", "2:3", "3:2", "3:4", "4:3",
                                 //                "4:5", "5:4", "9:16", "16:9", "21:9"
                                 // Custom: "2:7", "11:18", "1:3", etc. (auto-cropped)

  // Optional - Style
  "archetype": string,           // Default: "spot_illustration"
                                 // Options: "minimalist_vector_art",
                                 //          "symbolic_representation",
                                 //          "spot_illustration",
                                 //          "photorealistic",
                                 //          "icon", "logo"

  // Optional - Negative Prompt
  "negative_prompt": string,     // What to avoid in the image
                                 // Note: Merged into prompt for Gemini ("Avoid: ...")

  // Optional - Generation Options
  "options": {
    "remove_background": boolean,  // Default: false
                                   // Auto-true for: minimalist_vector_art,
                                   //                symbolic_representation,
                                   //                icon, logo

    "crop_anchor": string,         // Default: "center"
                                   // Options: "center", "top", "bottom",
                                   //          "left", "right", "smart"

    "store_in_cloud": boolean,     // Default: true
                                   // Store in Supabase & PostgreSQL

    "return_base64": boolean       // Default: false
                                   // Include base64 data in response
  },

  // Optional - Custom Metadata
  "metadata": {
    "key": "value"                 // Any custom key-value pairs
  }
}
```

#### Response Format

**Success Response** (200 OK):
```json
{
  "success": true,
  "image_id": "7cc1748b-69e3-426f-b16d-e1f181d23caa",

  "urls": {
    "original": "https://eshvntffcestlfuofwhv.supabase.co/storage/v1/object/public/generated-images/generated/xxx_original.png",
    "cropped": "https://eshvntffcestlfuofwhv.supabase.co/storage/v1/object/public/generated-images/generated/xxx_cropped.png",
    "transparent": "https://eshvntffcestlfuofwhv.supabase.co/storage/v1/object/public/generated-images/generated/xxx_transparent.png"
  },

  "base64_data": {
    "original": "base64-string...",    // Only if return_base64: true
    "cropped": "base64-string...",
    "transparent": "base64-string..."
  },

  "metadata": {
    "model": "gemini-2.5-flash-image",
    "platform": "vertex-ai-gemini",
    "generator": "gemini",
    "source_aspect_ratio": "16:9",
    "target_aspect_ratio": "16:9",
    "cropped": false,
    "background_removed": false,
    "generation_time_ms": 5420,
    "prompt": "A modern tech startup office with natural lighting",
    "archetype": "spot_illustration",
    "file_sizes": {
      "original": 312509,
      "cropped": null,
      "transparent": null
    }
  },

  "error": null,
  "created_at": "2025-12-27T03:18:00.218676"
}
```

**Error Response** (400/500):
```json
{
  "success": false,
  "image_id": null,
  "urls": null,
  "metadata": {},
  "error": "Error message here",
  "created_at": "2025-12-27T03:18:00.218676"
}
```

---

## Supported Aspect Ratios

### Gemini 2.5 Flash Image (Default) - 10 Native Ratios

| Ratio | Type | Dimensions | Use Case |
|-------|------|------------|----------|
| `1:1` | Square | 1024×1024 | Icons, avatars, social media |
| `2:3` | Portrait | 832×1248 | Mobile content, cards |
| `3:2` | Landscape | 1248×832 | Photos, thumbnails |
| `3:4` | Portrait | 768×1024 | Portraits, mobile |
| `4:3` | Landscape | 1024×768 | Classic photos |
| `4:5` | Portrait | 896×1120 | Instagram posts |
| `5:4` | Landscape | 1120×896 | Photo prints |
| `9:16` | Portrait | 768×1344 | Mobile/Stories |
| `16:9` | Landscape | 1344×768 | **Presentations, Hero slides** |
| `21:9` | Ultrawide | 1536×672 | Cinematic, panoramas |

### Imagen 3 (Fallback) - 5 Native Ratios

| Ratio | Type | Dimensions |
|-------|------|------------|
| `1:1` | Square | 1024×1024 |
| `3:4` | Portrait | 768×1024 |
| `4:3` | Landscape | 1024×768 |
| `9:16` | Portrait | 576×1024 |
| `16:9` | Landscape | 1024×576 |

### Custom Ratios (Intelligent Cropping)

Any ratio not natively supported will be generated at the closest native ratio and cropped:
- `2:7` - Tall portrait → generate at `9:16`, crop
- `11:18` - I-series wide → generate at `2:3`, crop
- `1:3` - I-series narrow → generate at `9:16`, crop
- **Any ratio you need!**

---

## 🎯 Layout-Specific Aspect Ratios Reference

Use these aspect ratios when generating images for specific Deckster layouts:

### H-Series (Hero Slides) - Full Screen Background

| Layout | Description | Aspect Ratio | Dimensions | Cropping |
|--------|-------------|--------------|------------|----------|
| `H1-generated` | AI-Generated Title | **16:9** | 1920×1080 | None ✓ |
| `H1-structured` | Manual Title Slide | **16:9** | 1920×1080 | None ✓ |
| `H2-section` | Section Divider | **16:9** | 1920×1080 | None ✓ |
| `H3-closing` | Closing Slide | **16:9** | 1920×1080 | None ✓ |
| `L29` | Hero Full-Bleed | **16:9** | 1920×1080 | None ✓ |

**Example - Hero Slide Background**:
```bash
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Abstract tech background with flowing blue gradients and geometric shapes, professional corporate style",
    "aspect_ratio": "16:9",
    "archetype": "photorealistic"
  }'
```

### I-Series (Image + Content) - Side Images

| Layout | Description | Target Size | Recommended Ratio | Generate At | Crop |
|--------|-------------|-------------|-------------------|-------------|------|
| `I1-image-left` | Wide left image | 660×1080 | `11:18` | **2:3** | 8% width |
| `I2-image-right` | Wide right image | 660×1080 | `11:18` | **2:3** | 8% width |
| `I3-image-left-narrow` | Narrow left image | 360×1080 | `1:3` | **9:16** | 41% width ⚠️ |
| `I4-image-right-narrow` | Narrow right image | 360×1080 | `1:3` | **9:16** | 41% width ⚠️ |

**Example - I1/I2 Wide Side Image**:
```bash
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Professional business person in modern office, natural lighting, centered composition with space on sides for cropping",
    "aspect_ratio": "2:3",
    "options": {
      "crop_anchor": "center"
    }
  }'
```

**⚠️ Note for I3/I4 Narrow Images**: These require 41% width cropping. For better results:
- Frame subjects centrally in the prompt
- Mention "vertical composition, centered subject"
- Expect significant edge cropping

**Example - I3/I4 Narrow Side Image**:
```bash
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Tall vertical abstract pattern, centered design element, geometric shapes flowing vertically",
    "aspect_ratio": "9:16",
    "options": {
      "crop_anchor": "center"
    }
  }'
```

### V-Series (Visual + Text)

| Layout | Description | Target Size | Recommended Ratio | Generate At | Crop |
|--------|-------------|-------------|-------------------|-------------|------|
| `V1-image-text` | Image left, text right | 1080×840 | `9:7` | **5:4** | 3% height |

**Example - V1 Visual**:
```bash
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Modern data visualization concept, abstract chart elements, professional business style",
    "aspect_ratio": "5:4"
  }'
```

### Quick Reference Table

| Layout Type | Use Case | Aspect Ratio | Native? |
|-------------|----------|--------------|---------|
| **H-series** | Hero/Title backgrounds | `16:9` | ✅ Yes |
| **I1/I2** | Wide side images | `2:3` | ✅ Yes |
| **I3/I4** | Narrow side images | `9:16` | ✅ Yes (heavy crop) |
| **V1** | Visual + text | `5:4` | ✅ Yes |
| **C-series** | Content backgrounds | `16:9` | ✅ Yes |

---

## Usage Examples

### Example 1: Simple Image Generation

**Request**:
```bash
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A modern tech startup logo with blue gradient"
  }'
```

**What You Get**:
- Image generated at 16:9 aspect ratio (default)
- Uses Gemini 2.5 Flash Image
- Stored in cloud storage
- Public URL returned

---

### Example 2: Custom Aspect Ratio with Background Removal

**Request**:
```bash
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Minimalist icon of a rocket ship",
    "aspect_ratio": "1:1",
    "archetype": "minimalist_vector_art",
    "options": {
      "remove_background": true
    }
  }'
```

**What You Get**:
- 1:1 square image (native, no cropping)
- Transparent PNG (background removed)
- Two versions: original and transparent

---

### Example 3: Ultra-Wide Image (Gemini Native)

**Request**:
```bash
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Beautiful mountain landscape at sunset, cinematic panoramic view",
    "aspect_ratio": "21:9"
  }'
```

**What You Get**:
- Ultra-wide 21:9 image (native with Gemini - no cropping!)
- Perfect for cinematic presentations
- 1536×672 resolution

---

### Example 4: Portrait for I-Series Layouts

**Request**:
```bash
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Professional team collaboration in modern office, vertical composition",
    "aspect_ratio": "2:3",
    "negative_prompt": "blurry, low quality, cropped faces"
  }'
```

**What You Get**:
- 2:3 portrait image (native with Gemini)
- Perfect for I1/I2 layouts (660×1080 after slight crop)
- High quality, centered composition

---

### Example 5: With Custom Metadata for Tracking

**Request**:
```bash
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Corporate office interior with modern design",
    "aspect_ratio": "16:9",
    "metadata": {
      "presentation_id": "pres_123",
      "slide_id": "slide_001",
      "layout": "H1-structured",
      "slide_type": "title_slide"
    }
  }'
```

**What You Get**:
- 16:9 hero background image
- Custom metadata saved in database
- Easy to query/track by presentation or slide

---

## Language-Specific Examples

### Python
```python
import httpx
import asyncio

async def generate_hero_image(prompt: str, layout: str = "H1-structured"):
    """Generate image for a specific layout."""

    # Layout to aspect ratio mapping
    LAYOUT_RATIOS = {
        "H1-generated": "16:9",
        "H1-structured": "16:9",
        "H2-section": "16:9",
        "H3-closing": "16:9",
        "L29": "16:9",
        "I1-image-left": "2:3",
        "I2-image-right": "2:3",
        "I3-image-left-narrow": "9:16",
        "I4-image-right-narrow": "9:16",
        "V1-image-text": "5:4",
    }

    aspect_ratio = LAYOUT_RATIOS.get(layout, "16:9")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://web-production-1b5df.up.railway.app/api/v2/generate",
            json={
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "metadata": {
                    "layout": layout
                }
            }
        )
        return response.json()

# Usage
result = asyncio.run(generate_hero_image(
    "Abstract tech background with blue gradients",
    layout="H1-structured"
))
print(f"Image URL: {result['urls']['original']}")
print(f"Generator: {result['metadata']['generator']}")
```

---

### JavaScript/TypeScript (Node.js)
```typescript
import fetch from 'node-fetch';

// Layout to aspect ratio mapping
const LAYOUT_RATIOS: Record<string, string> = {
  'H1-generated': '16:9',
  'H1-structured': '16:9',
  'H2-section': '16:9',
  'H3-closing': '16:9',
  'L29': '16:9',
  'I1-image-left': '2:3',
  'I2-image-right': '2:3',
  'I3-image-left-narrow': '9:16',
  'I4-image-right-narrow': '9:16',
  'V1-image-text': '5:4',
};

async function generateForLayout(prompt: string, layout: string) {
  const aspectRatio = LAYOUT_RATIOS[layout] || '16:9';

  const response = await fetch(
    'https://web-production-1b5df.up.railway.app/api/v2/generate',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        aspect_ratio: aspectRatio,
        metadata: { layout }
      })
    }
  );

  return response.json();
}

// Usage
const result = await generateForLayout(
  'Professional corporate background',
  'H1-structured'
);
console.log('Image URL:', result.urls.original);
console.log('Generator:', result.metadata.generator);
```

---

## Image Archetypes

| Archetype | Description | Auto Background Removal |
|-----------|-------------|------------------------|
| `spot_illustration` | Spot illustrations for content | No |
| `minimalist_vector_art` | Clean, minimal vector style | Yes |
| `symbolic_representation` | Abstract symbolic images | Yes |
| `photorealistic` | Realistic photo-like images | No |
| `icon` | Icon-style graphics | Yes |
| `logo` | Logo designs | Yes |

---

## Crop Anchor Options

When using custom aspect ratios, you can control which part of the image to keep:

- `center` (default) - Keep the center of the image
- `top` - Keep the top portion
- `bottom` - Keep the bottom portion
- `left` - Keep the left portion
- `right` - Keep the right portion
- `smart` - AI-based intelligent cropping (experimental)

---

## Generator Selection

The service automatically selects the image generator based on configuration:

| Environment Variable | Values | Default |
|---------------------|--------|---------|
| `IMAGE_GENERATOR` | `gemini`, `imagen` | `gemini` |
| `GEMINI_MODEL` | Model ID | `gemini-2.5-flash-image` |

### Gemini vs Imagen Comparison

| Feature | Gemini 2.5 Flash | Imagen 3 |
|---------|------------------|----------|
| Native Ratios | 10 | 5 |
| 21:9 Ultrawide | ✅ Native | ❌ Crop from 16:9 |
| 2:3 Portrait | ✅ Native | ❌ Crop from 9:16 |
| Negative Prompt | Merged into prompt | Direct support |
| Generation Speed | ~5-8 seconds | ~7-12 seconds |
| Rate Limits | ~2-3 req/min | Higher quota |

---

## Response Fields Explained

### URLs Object
- `original` - The base generated image
- `cropped` - Image cropped to your exact aspect ratio (if custom)
- `transparent` - PNG with white background removed (if applicable)

### Metadata Object
- `model` - AI model used (`gemini-2.5-flash-image` or `imagen-3.0-*`)
- `platform` - Generation platform (`vertex-ai-gemini` or `vertex-ai`)
- `generator` - Generator type (`gemini` or `imagen`)
- `source_aspect_ratio` - Native generation ratio used
- `target_aspect_ratio` - Your requested aspect ratio
- `cropped` - Whether cropping was applied
- `background_removed` - Whether background removal was applied
- `generation_time_ms` - Total processing time in milliseconds
- `file_sizes` - File sizes in bytes for each version

---

## Performance

### Generation Times
- **Gemini**: 5-8 seconds average
- **Imagen**: 7-12 seconds average
- **Upload**: 1-2 seconds
- **Total API Response**: ~8-15 seconds

### Rate Limits
- **Gemini**: ~2-3 requests per minute (burst limit)
- **Imagen**: Higher quota (depends on Vertex AI settings)
- Implement retry with exponential backoff for 429 errors

### Image Quality
- Gemini: 1024px base, varies by aspect ratio
- Imagen: 1024×1024 native, scaled for aspect ratios
- High-quality PNG format
- Transparent PNGs when background removed

---

## Error Handling

### Common Errors

**429 Rate Limited** (Gemini)
```json
{
  "success": false,
  "error": "Rate limit exceeded. Please try again in a minute."
}
```

**400 Bad Request**
```json
{
  "success": false,
  "error": "Invalid aspect ratio format. Use format like '16:9' or '1:1'"
}
```

**500 Internal Server Error**
```json
{
  "success": false,
  "error": "Gemini error: [details]"
}
```

### Retry Logic
```javascript
async function generateWithRetry(payload, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    const result = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(r => r.json());

    if (result.success) return result;

    // Retry on rate limit
    if (result.error?.includes('Rate limit')) {
      await new Promise(r => setTimeout(r, 30000 * (i + 1))); // 30s, 60s, 90s
      continue;
    }

    return result; // Don't retry on other errors
  }
}
```

---

## Best Practices

### 1. Use Layout-Specific Ratios
```python
# ✅ Good - Use correct ratio for layout
generate_image(prompt, aspect_ratio="16:9")  # For H-series
generate_image(prompt, aspect_ratio="2:3")   # For I1/I2

# ❌ Bad - Wrong ratio for layout
generate_image(prompt, aspect_ratio="1:1")   # For H-series (will be cropped)
```

### 2. Account for Cropping in Prompts
```python
# For I3/I4 (heavy cropping), mention centered composition
prompt = "Professional headshot, subject centered, vertical composition, simple background"
```

### 3. Handle Rate Limits
- Implement exponential backoff
- Space requests 30+ seconds apart for batch operations
- Use batch endpoint for multiple images

### 4. Timeout Handling
- Set client timeout to at least 120 seconds
- Don't use default 30-second timeouts

---

## Storage

Images are stored in Supabase Storage:
- **Bucket**: `generated-images`
- **Path**: `generated/{image_id}_{version}.png`
- **Access**: Public URLs (no authentication required)
- **Retention**: Permanent (until manually deleted)

---

## API Documentation

Interactive API documentation available at:
```
https://web-production-1b5df.up.railway.app/docs
```

---

## Changelog

### v2.1.0 (Current - 2025-12-27)
- **New**: Gemini 2.5 Flash Image as default generator
- **New**: 10 native aspect ratios (vs 5 with Imagen)
- **New**: Native 21:9 ultrawide support
- **New**: Native 2:3, 3:2, 4:5, 5:4 portrait/landscape ratios
- **New**: Layout-specific aspect ratio documentation
- **New**: Generator selection via `IMAGE_GENERATOR` env var
- **Improved**: Faster generation times (~5-8s vs ~7-12s)
- **Changed**: Negative prompts merged into main prompt for Gemini

### v2.0.1 (2025-11-26)
- **Security**: Migrated to Service Account authentication for Vertex AI
- **Security**: Implemented IP allowlist for network-level access control
- **Fixed**: Resolved 500 errors from authentication failures

### v2.0.0 (2024-10-11)
- Custom aspect ratio support with intelligent cropping
- Background removal for transparent PNGs
- PostgreSQL database integration
- Supabase cloud storage

---

**Built with ❤️ using FastAPI, Vertex AI (Gemini + Imagen), Supabase Storage, and PostgreSQL**
