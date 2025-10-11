# Image Build Agent v2.0

AI-powered image generation microservice with custom aspect ratio support, cloud storage, and REST API.

## 🌟 Key Features

### 1. **Custom Aspect Ratios**
Generate images in **any aspect ratio** (2:7, 21:9, 3:5, etc.) using intelligent cropping:
- Automatically selects optimal Imagen source ratio
- Smart cropping with multiple anchor points (center, top, bottom, smart)
- Preserves image quality while achieving target dimensions

### 2. **Cloud Storage with PostgreSQL Database**
Images automatically uploaded to **Supabase Storage** with metadata in **PostgreSQL**:
- Public URLs for easy sharing
- Multiple versions (original, cropped, transparent)
- Organized folder structure
- Full metadata tracking in database
- Query and filter generated images

### 3. **REST API Microservice**
Production-ready FastAPI application:
- `/api/v2/generate` - Generate images
- `/api/v2/health` - Health check
- Full OpenAPI documentation at `/docs`
- Deploy to Railway with one command

### 4. **Powered by Vertex AI Imagen 3**
- High-quality AI image generation
- Fast generation (7-10 seconds)
- Professional-grade results

---

## 🚀 Quick Start

### Prerequisites

1. **Google Cloud Project** with Vertex AI enabled
2. **Supabase Project** with Storage configured
3. **Python 3.11+**

### Installation

```bash
# Clone and navigate
cd /path/to/image_builder/v2.0

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
```

### Configuration

Edit `.env` file:

```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
VERTEX_AI_LOCATION=us-central1

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key  # Required for backend operations
SUPABASE_KEY=your-anon-key                  # Fallback key
SUPABASE_BUCKET=generated-images

# API (optional)
API_KEYS=your-secret-key-1,your-secret-key-2
```

### Run Locally

```bash
# Development mode with auto-reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Visit http://localhost:8000/docs for interactive API documentation.

---

## 📖 Usage Examples

### Generate Image with Custom Aspect Ratio

```bash
curl -X POST "http://localhost:8000/api/v2/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "prompt": "A modern tech startup logo with blue gradient",
    "aspect_ratio": "2:7",
    "archetype": "minimalist_vector_art",
    "options": {
      "remove_background": true,
      "crop_anchor": "center",
      "store_in_cloud": true
    }
  }'
```

**Response:**
```json
{
  "success": true,
  "image_id": "123e4567-e89b-12d3-a456-426614174000",
  "urls": {
    "original": "https://your-project.supabase.co/storage/v1/object/public/generated-images/generated/123e4567_original.png",
    "cropped": "https://your-project.supabase.co/storage/v1/object/public/generated-images/generated/123e4567_cropped.png",
    "transparent": "https://your-project.supabase.co/storage/v1/object/public/generated-images/generated/123e4567_transparent.png"
  },
  "metadata": {
    "model": "imagen-3.0-generate-002",
    "source_aspect_ratio": "9:16",
    "target_aspect_ratio": "2:7",
    "cropped": true,
    "background_removed": true,
    "generation_time_ms": 8500
  }
}
```

### Python SDK Usage

```python
import httpx
import asyncio

async def generate_image():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v2/generate",
            json={
                "prompt": "Beautiful mountain landscape at sunset",
                "aspect_ratio": "21:9",
                "options": {
                    "crop_anchor": "center"
                }
            },
            headers={"X-API-Key": "your-api-key"}
        )
        return response.json()

result = asyncio.run(generate_image())
print(f"Image URL: {result['urls']['cropped']}")
```

---

## 🏗️ Architecture

### Custom Aspect Ratio Strategy

1. **Parse Target Ratio**: Extract dimensions (e.g., "2:7" → width=2, height=7)
2. **Select Source Ratio**: Choose best Imagen-supported ratio
   - Portrait targets → 9:16 or 3:4
   - Landscape targets → 16:9 or 4:3
   - Square targets → 1:1
3. **Generate at Source**: Use Vertex AI Imagen 3 at optimal ratio
4. **Intelligent Crop**: Crop to exact target ratio using selected anchor
5. **Upload to Cloud**: Store all versions in Supabase

### Component Architecture

```
┌─────────────────────────────────────────┐
│         FastAPI Application             │
│  (main.py - REST API Endpoints)         │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
┌───────▼────────┐  ┌────────▼──────────┐
│  Image         │  │  Aspect Ratio     │
│  Generation    │  │  Engine           │
│  Service       │  │  (Cropping Logic) │
└───────┬────────┘  └───────────────────┘
        │
   ┌────┴────┬──────────┐
   │         │          │
┌──▼───┐ ┌──▼──────┐ ┌─▼────────┐
│Vertex│ │Supabase │ │PostgreSQL│
│ AI   │ │Storage  │ │Database  │
└──────┘ └─────────┘ └──────────┘
```

---

## 🎨 Supported Aspect Ratios

### Natively Supported (No Cropping Needed)
- `1:1` - Square
- `3:4` - Portrait
- `4:3` - Landscape
- `9:16` - Mobile portrait
- `16:9` - Widescreen

### Custom Ratios (Intelligent Cropping)
- `2:7` - Tall portrait (for slides)
- `21:9` - Ultrawide
- `3:5` - Portrait
- `5:3` - Landscape
- `9:21` - Extra tall
- **Any ratio you need!**

---

## 🔧 API Reference

### POST `/api/v2/generate`

Generate an AI image.

**Request Body:**
```typescript
{
  prompt: string;              // Required: Image description
  aspect_ratio?: string;       // Default: "16:9"
  archetype?: string;          // Default: "spot_illustration"
  negative_prompt?: string;    // What to avoid
  options?: {
    remove_background?: boolean;  // Default: false
    crop_anchor?: "center" | "top" | "bottom" | "left" | "right" | "smart";
    store_in_cloud?: boolean;     // Default: true
    quality?: "high" | "medium";
  };
  metadata?: Record<string, any>;
}
```

**Response:**
```typescript
{
  success: boolean;
  image_id: string;
  urls?: {
    original?: string;
    cropped?: string;
    transparent?: string;
  };
  metadata: {
    model: string;
    source_aspect_ratio: string;
    target_aspect_ratio: string;
    cropped: boolean;
    background_removed: boolean;
    generation_time_ms: number;
    file_sizes: {...};
  };
  error?: string;
}
```

### GET `/api/v2/health`

Health check endpoint.

**Response:**
```typescript
{
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  services: {
    vertex_ai: boolean;
    supabase: boolean;
    image_service: boolean;
  };
  timestamp: string;
}
```

---

## 🚢 Deployment

### Deploy to Railway

1. **Connect Repository**:
   ```bash
   railway login
   railway link
   ```

2. **Set Environment Variables** in Railway dashboard:
   - `GOOGLE_CLOUD_PROJECT`
   - `GOOGLE_APPLICATION_CREDENTIALS` (base64 encoded service account JSON)
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY` ⚠️ **Required** - Service role key for backend operations
   - `SUPABASE_KEY` (optional fallback - anon key)
   - `SUPABASE_BUCKET`
   - `API_KEYS` (comma-separated, optional)

3. **Deploy**:
   ```bash
   railway up
   ```

4. **Access**:
   - Your API will be live at `https://your-app.up.railway.app`
   - Docs at `https://your-app.up.railway.app/docs`

### Environment Setup for Railway

For `GOOGLE_APPLICATION_CREDENTIALS`, encode your service account JSON:

```bash
# On macOS/Linux
base64 -i service-account-key.json | pbcopy

# On Windows (PowerShell)
[Convert]::ToBase64String([IO.File]::ReadAllBytes("service-account-key.json")) | clip
```

Paste the base64 string as the environment variable value in Railway.

---

## 🗄️ Database & Storage Setup

### Supabase PostgreSQL Database

1. **Create Images Table**:
   - Open Supabase SQL Editor
   - Run the SQL from `archive/sql_scripts/create_images_table.sql`
   - This creates the `generated_images` table with all metadata fields
   - Includes indexes for fast querying

2. **Configure Storage Bucket**:
   - Go to Storage in Supabase dashboard
   - Create bucket named `generated-images`
   - Set to **Public** for URL access

3. **Set Row-Level Security Policies**:
   - Run the SQL from `archive/sql_scripts/disable_rls_for_bucket.sql`
   - This enables proper access control for storage operations
   - See `docs/SUPABASE_STORAGE_SETUP.md` for detailed guidance

4. **Get Service Role Key**:
   - Project Settings → API
   - Copy **service_role** key (NOT anon key)
   - Add to `.env` as `SUPABASE_SERVICE_KEY`

### 📚 Detailed Setup Documentation

For complete setup instructions and troubleshooting:
- **Storage Configuration**: See `docs/SUPABASE_STORAGE_SETUP.md`
- **Deployment Guide**: See `docs/DEPLOYMENT_NOTES.md`

---

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/test_aspect_ratio_engine.py -v

# Unit tests only
pytest -m unit
```

### Live API Tests

Test the complete pipeline with actual image generation:

```bash
# Run comprehensive live tests (requires server running)
python archive/test_files/test_api_live.py
```

This will:
- Test multiple aspect ratios (1:1, 2:7, 21:9)
- Generate actual images with Vertex AI
- Upload to Supabase Storage
- Save metadata to PostgreSQL
- Return public URLs
- Generate HTML report with images

### Test Individual Components

```bash
# Test aspect ratio engine
python src/services/aspect_ratio_engine.py

# Test Vertex AI connection
python src/services/vertex_ai_service.py

# Test Supabase storage
python archive/setup_scripts/verify_supabase_config.py
```

---

## 📊 Performance

### Benchmarks

- **Generation Time**: 7-12 seconds average
- **Upload Time**: 1-2 seconds to Supabase
- **Total API Response**: <15 seconds
- **Image Quality**: High (Imagen 3 1024x1024 base)

### Scaling

- **Concurrent Requests**: Handles 10-20 concurrent generations
- **Rate Limits**: Vertex AI quota dependent
- **Storage**: Unlimited (Supabase scales automatically)

---

## 💰 Cost Estimation

### Monthly Costs (1000 images)

- **Vertex AI Imagen**: ~$30-40 (varies by region)
- **Supabase Storage**: ~$0-5 (first 1GB free)
- **Railway Hosting**: ~$5-10 (Starter plan)

**Total**: ~$35-55/month for 1000 images

---

## 🔒 Security

### API Key Authentication

Set `API_KEYS` in environment:
```bash
API_KEYS=key1,key2,key3
```

Include in requests:
```bash
curl -H "X-API-Key: key1" ...
```

### Best Practices

- Use service accounts for production
- Rotate API keys regularly
- Enable Supabase RLS policies
- Use HTTPS in production
- Monitor quota usage

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🆘 Troubleshooting

### "GOOGLE_CLOUD_PROJECT not configured"

**Solution**: Set environment variable
```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
```

### "Permission denied" from Vertex AI

**Solution**: Enable Vertex AI API
```bash
gcloud services enable aiplatform.googleapis.com
```

### "Supabase upload failed" or "row violates row-level security policy"

**Solution**: Check RLS policies and service key
- Use `SUPABASE_SERVICE_KEY` (NOT anon key) for backend operations
- Verify RLS policies allow storage operations
- Run SQL from `archive/sql_scripts/disable_rls_for_bucket.sql`
- See detailed guide: `docs/SUPABASE_STORAGE_SETUP.md`

### "No module named 'src'"

**Solution**: Run from project root
```bash
cd /path/to/v2.0
python -m uvicorn src.main:app --reload
```

---

## 📁 Project Structure

```
v2.0/
├── src/                        # Core application code
│   ├── main.py                # FastAPI entry point
│   ├── models/                # Pydantic models
│   └── services/              # Business logic services
├── docs/                       # Comprehensive documentation
│   ├── SUPABASE_STORAGE_SETUP.md  # Storage configuration guide
│   └── DEPLOYMENT_NOTES.md    # Production deployment guide
├── archive/                    # Development files (NOT for production)
│   ├── test_files/            # Test scripts and results
│   ├── sql_scripts/           # Database setup SQL
│   ├── logs/                  # Development logs
│   ├── html_reports/          # Test reports
│   └── setup_scripts/         # Setup utilities
├── tests/                      # Unit tests
├── examples/                   # Usage examples
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
└── README.md                 # This file
```

**Note**: The `archive/` folder contains development and testing files that should **NOT** be deployed to production. It's excluded via `.dockerignore`.

---

## 🤝 Support

For issues, questions, or feature requests:
- **Storage Setup**: Check `docs/SUPABASE_STORAGE_SETUP.md` for comprehensive Supabase configuration
- **Deployment**: Review `docs/DEPLOYMENT_NOTES.md` for production deployment guide
- **Architecture**: See `IMPLEMENTATION_SUMMARY.md` for system design details
- **Quick Start**: Follow `QUICKSTART.md` for rapid setup
- **Setup Guide**: Read `SETUP_GUIDE.md` for detailed installation

---

**Built with ❤️ using FastAPI, Vertex AI Imagen 3, Supabase Storage, and PostgreSQL**
