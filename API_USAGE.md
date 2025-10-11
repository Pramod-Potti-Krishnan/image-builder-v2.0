# Image Builder v2.0 API Documentation

## Base URL
```
https://web-production-1b5df.up.railway.app
```

## Overview
AI-powered image generation API using Google Vertex AI Imagen 3. Generates high-quality images with custom aspect ratios, automatic cloud storage, and background removal capabilities.

---

## Authentication

### API Key (Optional)
If API keys are configured, include in request headers:
```http
X-API-Key: your-api-key-here
```

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
  "version": "2.0.0",
  "services": {
    "vertex_ai": true,
    "supabase": true,
    "image_service": true
  },
  "timestamp": "2025-10-11T03:17:35.935636"
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
                                 // Supported: "1:1", "3:4", "4:3", "9:16", "16:9"
                                 // Custom: "2:7", "21:9", "3:5", etc.

  // Optional - Style
  "archetype": string,           // Default: "spot_illustration"
                                 // Options: "minimalist_vector_art",
                                 //          "symbolic_representation",
                                 //          "spot_illustration",
                                 //          "photorealistic",
                                 //          "icon", "logo"

  // Optional - Negative Prompt
  "negative_prompt": string,     // What to avoid in the image

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
    "model": "imagen-3.0-generate-002",
    "platform": "vertex-ai",
    "source_aspect_ratio": "1:1",
    "target_aspect_ratio": "1:1",
    "cropped": false,
    "background_removed": true,
    "generation_time_ms": 8384,
    "prompt": "A simple blue circle on white background",
    "archetype": "minimalist_vector_art",
    "file_sizes": {
      "original": 312509,
      "cropped": null,
      "transparent": 260049
    }
  },

  "error": null,
  "created_at": "2025-10-11T03:18:00.218676"
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
  "created_at": "2025-10-11T03:18:00.218676"
}
```

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
- 1:1 square image
- Transparent PNG (background removed)
- Two versions: original and transparent

---

### Example 3: Ultra-Wide Image for Slides

**Request**:
```bash
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Beautiful mountain landscape at sunset",
    "aspect_ratio": "21:9",
    "options": {
      "crop_anchor": "center"
    }
  }'
```

**What You Get**:
- Ultra-wide 21:9 image
- Intelligently cropped from 16:9 source
- Perfect for presentation slides

---

### Example 4: Tall Portrait for Mobile

**Request**:
```bash
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Modern smartphone app interface design",
    "aspect_ratio": "9:16",
    "negative_prompt": "blurry, low quality"
  }'
```

**What You Get**:
- Mobile-friendly 9:16 portrait
- High quality AI-generated image
- No blurry or low-quality elements

---

### Example 5: With Custom Metadata

**Request**:
```bash
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Corporate office interior",
    "aspect_ratio": "4:3",
    "metadata": {
      "project_id": "proj_123",
      "user_id": "user_456",
      "campaign": "office_refresh"
    }
  }'
```

**What You Get**:
- 4:3 landscape image
- Custom metadata saved in database
- Easy to query later by project/user

---

## Language-Specific Examples

### Python
```python
import httpx
import asyncio

async def generate_image():
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://web-production-1b5df.up.railway.app/api/v2/generate",
            json={
                "prompt": "A futuristic city skyline",
                "aspect_ratio": "16:9",
                "options": {
                    "store_in_cloud": True
                }
            }
        )
        return response.json()

result = asyncio.run(generate_image())
print(f"Image URL: {result['urls']['original']}")
print(f"Generation time: {result['metadata']['generation_time_ms']}ms")
```

---

### JavaScript/TypeScript (Node.js)
```typescript
import fetch from 'node-fetch';

async function generateImage() {
  const response = await fetch(
    'https://web-production-1b5df.up.railway.app/api/v2/generate',
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt: 'A futuristic city skyline',
        aspect_ratio: '16:9',
        options: {
          store_in_cloud: true
        }
      })
    }
  );

  const result = await response.json();
  console.log('Image URL:', result.urls.original);
  console.log('Generation time:', result.metadata.generation_time_ms, 'ms');
  return result;
}

generateImage();
```

---

### JavaScript (Browser/React)
```javascript
async function generateImage() {
  try {
    const response = await fetch(
      'https://web-production-1b5df.up.railway.app/api/v2/generate',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: 'A futuristic city skyline',
          aspect_ratio: '16:9',
          options: {
            store_in_cloud: true
          }
        })
      }
    );

    const result = await response.json();

    if (result.success) {
      // Display image
      document.getElementById('generated-image').src = result.urls.original;
      console.log('Image generated in', result.metadata.generation_time_ms, 'ms');
    } else {
      console.error('Generation failed:', result.error);
    }
  } catch (error) {
    console.error('Request failed:', error);
  }
}
```

---

### cURL
```bash
# Basic generation
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A futuristic city skyline","aspect_ratio":"16:9"}'

# Save response to file
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A futuristic city skyline"}' \
  -o response.json

# Pretty print with jq
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A futuristic city skyline"}' | jq .
```

---

## Supported Aspect Ratios

### Native Ratios (No Cropping)
- `1:1` - Square (1024x1024)
- `3:4` - Portrait (768x1024)
- `4:3` - Landscape (1024x768)
- `9:16` - Mobile Portrait (576x1024)
- `16:9` - Widescreen (1024x576)

### Custom Ratios (Intelligent Cropping)
- `2:7` - Tall portrait (292x1024) - great for slides
- `21:9` - Ultrawide (1024x439)
- `3:5` - Portrait (614x1024)
- `5:3` - Landscape (1024x614)
- **Any ratio you need!** - The system intelligently selects the best source ratio and crops

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

## Response Fields Explained

### URLs Object
- `original` - The base generated image (at Imagen's native ratio)
- `cropped` - Image cropped to your exact aspect ratio (if custom)
- `transparent` - PNG with white background removed (if applicable)

### Metadata Object
- `model` - AI model used (imagen-3.0-generate-002)
- `platform` - Generation platform (vertex-ai)
- `source_aspect_ratio` - Imagen's native generation ratio
- `target_aspect_ratio` - Your requested aspect ratio
- `cropped` - Whether cropping was applied
- `background_removed` - Whether background removal was applied
- `generation_time_ms` - Total processing time in milliseconds
- `file_sizes` - File sizes in bytes for each version

---

## Performance

### Generation Times
- **Average**: 7-12 seconds
- **Upload**: 1-2 seconds
- **Total API Response**: ~10-15 seconds

### Rate Limits
- Depends on your Vertex AI quota
- Contact us for higher quotas

### Image Quality
- Base resolution: 1024x1024 (Imagen 3 native)
- High-quality PNG format
- Transparent PNGs when background removed

---

## Error Handling

### Common Errors

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
  "error": "Vertex AI error: Quota exceeded"
}
```

**503 Service Unavailable**
```json
{
  "success": false,
  "error": "Supabase storage unavailable"
}
```

### Error Response Structure
All errors return JSON with:
- `success: false`
- `error: string` - Human-readable error message
- `image_id: null`
- `urls: null`

---

## Best Practices

### 1. Prompt Engineering
✅ **Good Prompts**:
- "A minimalist icon of a rocket ship with clean lines and blue color scheme"
- "Modern tech startup office interior with natural lighting and plants"
- "Abstract geometric pattern in teal and purple gradients"

❌ **Poor Prompts**:
- "logo" (too vague)
- "something cool" (not descriptive)
- "asdfasdf" (nonsensical)

### 2. Aspect Ratio Selection
- Use native ratios when possible (faster, no cropping)
- For presentations: `16:9` or `4:3`
- For social media: `1:1` or `9:16`
- For slides/posters: `2:7` or custom

### 3. Background Removal
- Automatically applied for: `minimalist_vector_art`, `icon`, `logo`
- Manually enable for other archetypes if needed
- Works best with solid/simple backgrounds

### 4. Error Handling
```javascript
// Always check success field
if (result.success) {
  // Use result.urls
} else {
  // Handle result.error
}

// Implement retry logic for transient errors
async function generateWithRetry(payload, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      const result = await response.json();
      if (result.success) return result;

      // Retry on specific errors
      if (result.error.includes('quota') || result.error.includes('timeout')) {
        await sleep(2000 * (i + 1)); // Exponential backoff
        continue;
      }

      return result; // Don't retry on other errors
    } catch (error) {
      if (i === maxRetries - 1) throw error;
    }
  }
}
```

### 5. Timeout Handling
- Set client timeout to at least 120 seconds
- Image generation can take 10-15 seconds
- Don't use default 30-second timeouts

---

## Database Integration

All generated images are automatically saved to PostgreSQL with:
- Image URLs (original, cropped, transparent)
- Storage paths
- Generation metadata
- Performance metrics
- Custom metadata (if provided)
- Timestamps

You can query the database directly via Supabase API if needed.

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

Includes:
- Full API specification
- Try-it-out functionality
- Request/response schemas
- Example payloads

---

## Support & Issues

For issues or questions:
- Check health endpoint first: `/api/v2/health`
- Review error messages carefully
- Verify request format matches examples
- Check timeout settings in your client

---

## Changelog

### v2.0.0 (Current)
- Custom aspect ratio support with intelligent cropping
- Background removal for transparent PNGs
- PostgreSQL database integration
- Supabase cloud storage
- Enhanced metadata tracking
- Multiple image versions (original, cropped, transparent)

---

**Built with ❤️ using FastAPI, Vertex AI Imagen 3, Supabase Storage, and PostgreSQL**
