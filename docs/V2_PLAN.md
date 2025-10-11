# Image Build Agent v2.0 - Master Plan

**Version**: 2.0
**Date**: 2025-10-10
**Status**: Planning Phase
**Migration From**: v1.0 (Vertex AI)

---

## 📋 Executive Summary

Image Build Agent v2.0 will transform the current standalone agent into a production-ready **cloud microservice** with three major enhancements:

1. **Custom Aspect Ratio Support** - Generate images in any aspect ratio (not limited to Imagen's 5 ratios)
2. **Cloud Storage & URL Sharing** - Store images in Supabase Storage with public URLs
3. **REST API Microservice** - Deploy as a scalable API on Railway with FastAPI

---

## 🎯 Core Requirements

### Requirement 1: Non-Traditional Aspect Ratio Support

**Problem**: Vertex AI Imagen 3 only supports 5 fixed aspect ratios (1:1, 3:4, 4:3, 9:16, 16:9)

**Solution**: Intelligent Generate + Crop Pipeline
- Generate at closest available ratio (oversized)
- Apply smart cropping to target custom ratio
- Maintain image quality and subject focus

**Target Ratios to Support**:
- Standard: 1:1, 3:4, 4:3, 9:16, 16:9 (native Imagen)
- Custom vertical: 2:7, 1:3, 2:5, 3:8 (for tall slide elements)
- Custom horizontal: 7:2, 3:1, 5:2, 8:3 (for wide banners)
- Any user-specified ratio: Custom (w:h) input

**Intelligent Cropping Strategy**:
- Center-based cropping (default)
- Subject-aware cropping (detect main subject, keep centered)
- Edge-aware cropping (avoid cutting important elements)
- Configurable crop anchor (top, center, bottom, left, right)

### Requirement 2: Cloud Storage with URL Sharing

**Storage Solution**: Supabase Storage (Object Storage)

**Why Supabase Storage**:
- ✅ S3-compatible object storage
- ✅ Built-in CDN for fast delivery
- ✅ Public URL generation
- ✅ Already integrated with your stack
- ✅ Generous free tier (1GB storage, 2GB bandwidth)
- ✅ Automatic image transformations/resizing
- ✅ Bucket-level access controls

**Storage Architecture**:
```
Supabase Storage Buckets:
├── generated-images/          # Main bucket (public)
│   ├── originals/             # Full-size generated images
│   │   └── {uuid}.png
│   ├── crops/                 # Custom aspect ratio crops
│   │   └── {uuid}_{ratio}.png
│   └── thumbnails/            # Auto-generated previews
│       └── {uuid}_thumb.png
```

**URL Format**:
```
https://{project}.supabase.co/storage/v1/object/public/generated-images/originals/{uuid}.png
```

**Storage Workflow**:
1. Generate image with Vertex AI
2. Upload to Supabase Storage (originals/)
3. If custom ratio: crop and upload to crops/
4. Generate thumbnail (optional)
5. Return public URLs for all variants

**Metadata Storage** (Supabase PostgreSQL):
```sql
CREATE TABLE generated_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_url TEXT NOT NULL,
    cropped_url TEXT,
    thumbnail_url TEXT,
    prompt TEXT NOT NULL,
    archetype VARCHAR(100),
    aspect_ratio VARCHAR(20),
    custom_aspect_ratio VARCHAR(20),
    file_size_bytes BIGINT,
    model_used VARCHAR(100),
    generation_time_ms INTEGER,
    has_transparency BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB  -- Store additional data
);
```

### Requirement 3: REST API Microservice on Railway

**Framework**: FastAPI (Python)

**Why FastAPI**:
- ✅ Modern, fast, async-first
- ✅ Automatic OpenAPI/Swagger docs
- ✅ Type validation with Pydantic (already using)
- ✅ Built-in async support (matches our agent)
- ✅ Easy Railway deployment
- ✅ WebSocket support (for future real-time updates)

**Deployment Platform**: Railway

**Why Railway**:
- ✅ Simple deployment (git push)
- ✅ Automatic HTTPS/SSL
- ✅ Environment variable management
- ✅ Auto-scaling
- ✅ Generous free tier ($5 credit/month)
- ✅ Integrated monitoring
- ✅ Zero-config deployments

**API Architecture**:
```
Image Build Microservice v2.0
├── FastAPI Application
├── Vertex AI Integration (from v1.0)
├── Supabase Storage Integration
├── Custom Cropping Engine
└── Background Removal (optional)
```

---

## 🏗️ Architecture Overview

### High-Level Flow

```
User Request (REST API)
    ↓
FastAPI Endpoint
    ↓
Image Build Agent v2.0
    ↓
1. Generate with Vertex AI (closest ratio)
    ↓
2. Apply custom cropping (if needed)
    ↓
3. Background removal (if requested)
    ↓
4. Upload to Supabase Storage
    ↓
5. Store metadata in PostgreSQL
    ↓
Return URLs to user
```

### Component Architecture

```
┌─────────────────────────────────────────┐
│         REST API Layer (FastAPI)        │
│  - Authentication                       │
│  - Rate limiting                        │
│  - Request validation                   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Image Generation Service           │
│  - Vertex AI client                     │
│  - Prompt optimization                  │
│  - Aspect ratio selection               │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Image Processing Service           │
│  - Custom ratio cropping                │
│  - Smart subject detection              │
│  - Background removal                   │
│  - Format conversion                    │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Storage Service (Supabase)         │
│  - Upload to object storage             │
│  - Generate public URLs                 │
│  - Save metadata to PostgreSQL          │
└─────────────────┬───────────────────────┘
                  │
                Response
```

---

## 📡 API Design

### Core Endpoints

#### 1. Generate Image (Primary Endpoint)

**POST** `/api/v2/generate`

**Request Body**:
```json
{
  "prompt": "A modern tech startup logo with blue and purple gradient",
  "archetype": "minimalist_vector_art",
  "aspect_ratio": "2:7",  // Custom ratio
  "style": {
    "color_scheme": "blue and purple",
    "mood": ["modern", "professional"]
  },
  "options": {
    "remove_background": true,
    "generate_thumbnail": true,
    "crop_anchor": "center"  // top, center, bottom, left, right
  }
}
```

**Response**:
```json
{
  "success": true,
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "urls": {
    "original": "https://project.supabase.co/storage/v1/object/public/generated-images/originals/550e8400.png",
    "cropped": "https://project.supabase.co/storage/v1/object/public/generated-images/crops/550e8400_2-7.png",
    "thumbnail": "https://project.supabase.co/storage/v1/object/public/generated-images/thumbnails/550e8400_thumb.png"
  },
  "metadata": {
    "model": "imagen-3.0-generate-002",
    "source_ratio": "9:16",
    "target_ratio": "2:7",
    "file_size_bytes": 145234,
    "has_transparency": true,
    "generation_time_ms": 7842
  }
}
```

#### 2. Get Image Details

**GET** `/api/v2/images/{image_id}`

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "prompt": "A modern tech startup logo...",
  "urls": { ... },
  "metadata": { ... },
  "created_at": "2025-10-10T11:25:50Z"
}
```

#### 3. List Generated Images

**GET** `/api/v2/images?limit=10&offset=0`

**Response**:
```json
{
  "images": [ ... ],
  "total": 42,
  "limit": 10,
  "offset": 0
}
```

#### 4. Delete Image

**DELETE** `/api/v2/images/{image_id}`

#### 5. Health Check

**GET** `/api/v2/health`

**Response**:
```json
{
  "status": "healthy",
  "services": {
    "vertex_ai": "connected",
    "supabase_storage": "connected",
    "supabase_db": "connected"
  }
}
```

### Authentication

**API Key Authentication** (Simple, production-ready):
```
Headers:
  X-API-Key: your-secret-api-key
```

**Rate Limiting**:
- Free tier: 10 requests/minute
- Paid tier: 100 requests/minute

---

## 🔧 Technical Implementation Plan

### Phase 1: Core Infrastructure (Days 1-2)

**Tasks**:
1. Set up v2.0 project structure
2. Copy and adapt v1.0 Vertex AI integration
3. Set up FastAPI application skeleton
4. Configure Supabase connection (Storage + DB)
5. Create database schema
6. Set up environment configuration

**Deliverables**:
- Project structure
- FastAPI app with basic routes
- Supabase integration working
- Database tables created

### Phase 2: Custom Aspect Ratio Engine (Days 3-4)

**Tasks**:
1. Implement aspect ratio analyzer
   - Determine best source ratio for target
2. Build intelligent cropping engine
   - Center-based cropping
   - Subject-aware cropping (using image analysis)
   - Edge-aware cropping
3. Add crop anchor support (top/center/bottom/left/right)
4. Implement crop validation and quality checks
5. Create unit tests for cropping logic

**Deliverables**:
- `aspect_ratio_engine.py` module
- `smart_cropper.py` module
- Comprehensive test suite
- Documentation

### Phase 3: Storage Integration (Days 5-6)

**Tasks**:
1. Implement Supabase Storage client
2. Create upload/download functions
3. Implement URL generation
4. Add metadata storage to PostgreSQL
5. Implement thumbnail generation
6. Add cleanup/deletion functions
7. Test storage reliability

**Deliverables**:
- `storage_service.py` module
- `metadata_service.py` module
- Storage bucket setup guide
- Test coverage

### Phase 4: API Development (Days 7-8)

**Tasks**:
1. Implement all REST endpoints
2. Add request/response validation
3. Implement API key authentication
4. Add rate limiting
5. Error handling and logging
6. Create OpenAPI documentation
7. Add CORS configuration

**Deliverables**:
- Complete FastAPI application
- API documentation (auto-generated)
- Authentication system
- Rate limiting

### Phase 5: Integration & Testing (Days 9-10)

**Tasks**:
1. End-to-end integration testing
2. Load testing
3. Error scenario testing
4. Documentation
5. Example client code

**Deliverables**:
- Integration test suite
- Performance benchmarks
- User documentation
- Example implementations

### Phase 6: Deployment (Days 11-12)

**Tasks**:
1. Railway deployment configuration
2. Environment variable setup
3. Database migrations
4. Production testing
5. Monitoring setup
6. Documentation updates

**Deliverables**:
- Live API on Railway
- Deployment documentation
- Monitoring dashboard
- Production-ready service

---

## 📦 Project Structure

```
v2.0/
├── docs/
│   ├── V2_PLAN.md                    # This file
│   ├── API_DOCUMENTATION.md          # API reference
│   ├── DEPLOYMENT_GUIDE.md           # Railway deployment
│   ├── STORAGE_SETUP.md              # Supabase setup
│   └── CUSTOM_RATIOS.md              # Custom aspect ratio guide
├── src/
│   ├── main.py                       # FastAPI application entry
│   ├── config.py                     # Configuration management
│   ├── models/
│   │   ├── requests.py               # Pydantic request models
│   │   ├── responses.py              # Pydantic response models
│   │   └── database.py               # SQLAlchemy models
│   ├── services/
│   │   ├── image_generator.py        # Vertex AI integration (from v1.0)
│   │   ├── aspect_ratio_engine.py    # Custom ratio logic
│   │   ├── smart_cropper.py          # Intelligent cropping
│   │   ├── storage_service.py        # Supabase Storage
│   │   ├── metadata_service.py       # PostgreSQL operations
│   │   └── background_remover.py     # Background removal (from v1.0)
│   ├── api/
│   │   ├── routes/
│   │   │   ├── generate.py           # Image generation endpoints
│   │   │   ├── images.py             # Image management endpoints
│   │   │   └── health.py             # Health check endpoints
│   │   ├── dependencies.py           # FastAPI dependencies
│   │   ├── authentication.py         # API key auth
│   │   └── middleware.py             # Rate limiting, CORS
│   └── utils/
│       ├── validators.py             # Input validation
│       ├── helpers.py                # Utility functions
│       └── logger.py                 # Logging configuration
├── tests/
│   ├── unit/
│   │   ├── test_aspect_ratio.py
│   │   ├── test_cropping.py
│   │   └── test_storage.py
│   ├── integration/
│   │   ├── test_api_endpoints.py
│   │   └── test_full_workflow.py
│   └── fixtures/
│       └── test_images.py
├── migrations/
│   └── supabase/
│       └── 001_initial_schema.sql
├── scripts/
│   ├── setup_supabase.py             # Supabase initialization
│   ├── test_deployment.py            # Deployment testing
│   └── generate_api_key.py           # API key generation
├── .env.example
├── .env.production.example
├── requirements.txt
├── railway.toml                      # Railway configuration
├── Procfile                          # Railway/Heroku process
├── README.md
└── CHANGELOG.md
```

---

## 🎨 Custom Aspect Ratio Algorithm

### Algorithm: Intelligent Ratio Matching & Cropping

```python
def select_source_ratio(target_ratio: tuple) -> str:
    """
    Select best Imagen ratio for target custom ratio.

    Strategy:
    1. Calculate target aspect (width/height)
    2. Find closest Imagen ratio that's LARGER in both dimensions
    3. Prefer ratios with similar orientation (portrait/landscape)
    """

    target_aspect = target_ratio[0] / target_ratio[1]

    # Available Imagen ratios with their aspects
    imagen_ratios = {
        "1:1": 1.0,
        "4:3": 1.333,
        "16:9": 1.778,
        "3:4": 0.75,
        "9:16": 0.5625
    }

    # Select ratio that minimizes cropping waste
    # but ensures we can achieve target without scaling up

    if target_aspect >= 1:  # Landscape or square
        candidates = ["16:9", "4:3", "1:1"]
    else:  # Portrait
        candidates = ["9:16", "3:4", "1:1"]

    # Pick first candidate that fits
    for ratio in candidates:
        if _can_crop_to_target(ratio, target_ratio):
            return ratio

    return "1:1"  # Fallback


def smart_crop(
    image_bytes: bytes,
    target_ratio: tuple,
    anchor: str = "center"
) -> bytes:
    """
    Intelligently crop image to target ratio.

    Strategies:
    - center: Crop from center (default, safe)
    - subject: Detect main subject, keep centered
    - edge: Detect edges, avoid cutting important elements
    - top/bottom/left/right: Anchor to specific edge
    """

    img = Image.open(BytesIO(image_bytes))
    width, height = img.size

    target_w, target_h = target_ratio
    target_aspect = target_w / target_h

    # Calculate crop dimensions
    if width / height > target_aspect:
        # Image is wider than target, crop width
        new_width = int(height * target_aspect)
        new_height = height
    else:
        # Image is taller than target, crop height
        new_width = width
        new_height = int(width / target_aspect)

    # Determine crop position based on anchor
    if anchor == "center":
        left = (width - new_width) // 2
        top = (height - new_height) // 2
    elif anchor == "top":
        left = (width - new_width) // 2
        top = 0
    elif anchor == "bottom":
        left = (width - new_width) // 2
        top = height - new_height
    # ... more anchor options

    # Perform crop
    cropped = img.crop((
        left,
        top,
        left + new_width,
        top + new_height
    ))

    # Convert back to bytes
    output = BytesIO()
    cropped.save(output, format='PNG')
    return output.getvalue()
```

---

## 💾 Supabase Storage Setup

### Bucket Configuration

```sql
-- Create storage bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('generated-images', 'generated-images', true);

-- Set up bucket policies
CREATE POLICY "Public access to generated images"
ON storage.objects FOR SELECT
USING ( bucket_id = 'generated-images' );

CREATE POLICY "Authenticated users can upload"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'generated-images'
    AND auth.role() = 'authenticated'
);

CREATE POLICY "Authenticated users can delete their images"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'generated-images'
    AND auth.uid() = owner
);
```

### Database Schema

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Generated images table
CREATE TABLE generated_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_url TEXT NOT NULL,
    cropped_url TEXT,
    thumbnail_url TEXT,

    -- Generation details
    prompt TEXT NOT NULL,
    archetype VARCHAR(100),
    native_aspect_ratio VARCHAR(20),  -- Imagen ratio used
    custom_aspect_ratio VARCHAR(20),   -- Target ratio
    crop_anchor VARCHAR(20),

    -- File details
    file_size_bytes BIGINT,
    file_format VARCHAR(10) DEFAULT 'png',
    width_px INTEGER,
    height_px INTEGER,

    -- Processing details
    model_used VARCHAR(100) DEFAULT 'imagen-3.0-generate-002',
    generation_time_ms INTEGER,
    has_transparency BOOLEAN DEFAULT false,
    background_removed BOOLEAN DEFAULT false,

    -- Metadata
    metadata JSONB,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Indexes
    INDEX idx_archetype (archetype),
    INDEX idx_created_at (created_at DESC),
    INDEX idx_custom_ratio (custom_aspect_ratio)
);

-- Function to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for updated_at
CREATE TRIGGER update_generated_images_updated_at
    BEFORE UPDATE ON generated_images
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- API keys table
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash TEXT NOT NULL UNIQUE,
    name VARCHAR(255),
    tier VARCHAR(50) DEFAULT 'free',  -- free, paid
    rate_limit INTEGER DEFAULT 10,    -- requests per minute
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,

    INDEX idx_key_hash (key_hash)
);
```

---

## 🚀 Railway Deployment Configuration

### railway.toml

```toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn src.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/v2/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[env]
PYTHON_VERSION = "3.11"
```

### Procfile

```
web: uvicorn src.main:app --host 0.0.0.0 --port $PORT --workers 4
```

### Environment Variables (Railway)

```env
# Google Cloud Vertex AI
GOOGLE_CLOUD_PROJECT=vibe-decker-mvp
GOOGLE_APPLICATION_CREDENTIALS_JSON={service_account_json}

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_BUCKET_NAME=generated-images

# API Configuration
API_SECRET_KEY=your-secret-key-here
API_RATE_LIMIT_FREE=10
API_RATE_LIMIT_PAID=100

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
```

---

## 🔐 Security Considerations

1. **API Key Management**:
   - Store API keys hashed (bcrypt)
   - Rate limiting per key
   - Automatic key rotation support

2. **Image Access**:
   - Public URLs for generated images (no auth needed)
   - Option for private buckets with signed URLs
   - TTL for temporary images

3. **Input Validation**:
   - Prompt sanitization (prevent injection)
   - File size limits
   - Aspect ratio validation

4. **Storage Security**:
   - Bucket access policies
   - File type validation
   - Malware scanning (future)

---

## 📊 Performance Targets

- **Image Generation**: < 10 seconds (avg)
- **Custom Cropping**: < 500ms
- **Upload to Supabase**: < 2 seconds
- **Total API Response**: < 15 seconds
- **Concurrent Requests**: 10+ simultaneous
- **Uptime**: 99.5% minimum

---

## 💰 Cost Estimation (Monthly)

### For 1000 images/month:

**Vertex AI Imagen 3**:
- ~$0.02 per image = $20

**Supabase**:
- Storage (1GB free, ~500MB used) = $0
- Bandwidth (2GB free, ~2GB used) = $0
- Database (Free tier) = $0

**Railway**:
- Free tier ($5 credit) = $0
- Paid plan (if needed) = $5-20

**Total**: ~$20-40/month for 1000 images

---

## 🎯 Success Criteria

### MVP (Minimum Viable Product):
- ✅ Generate images with custom aspect ratios
- ✅ Store in Supabase with public URLs
- ✅ REST API deployed on Railway
- ✅ Basic documentation

### V2.0 Complete:
- ✅ All custom ratios working perfectly
- ✅ Intelligent cropping with multiple strategies
- ✅ Full CRUD API for images
- ✅ Production-ready with monitoring
- ✅ Comprehensive documentation
- ✅ 90%+ test coverage

---

## 📅 Timeline

**Total Estimated Time**: 12-15 days

- **Phase 1**: 2 days (Infrastructure)
- **Phase 2**: 2 days (Custom Ratios)
- **Phase 3**: 2 days (Storage)
- **Phase 4**: 2 days (API)
- **Phase 5**: 2 days (Testing)
- **Phase 6**: 2 days (Deployment)

---

## 🔄 Migration from v1.0

### What to Keep:
- ✅ Vertex AI integration code
- ✅ Background removal logic
- ✅ Image processing utilities
- ✅ Pydantic models (adapt for API)

### What to Add:
- ✅ Custom aspect ratio engine
- ✅ Supabase integration
- ✅ FastAPI application
- ✅ Storage management
- ✅ API authentication

### What to Change:
- ⚠️ Return URLs instead of base64 (primary response)
- ⚠️ Async all the way (FastAPI native)
- ⚠️ Add database persistence
- ⚠️ Cloud-native configuration

---

## 📚 Next Steps

1. **Review this plan** - Confirm requirements and approach
2. **Set up Supabase** - Create project, buckets, tables
3. **Begin Phase 1** - Project structure and basic infrastructure
4. **Iterative development** - Build and test incrementally
5. **Deploy MVP** - Get working version live quickly
6. **Iterate to v2.0** - Add advanced features

---

## ❓ Open Questions / Decisions Needed

1. **API Authentication**:
   - Simple API keys (recommended for MVP)?
   - Or OAuth/JWT for production?

2. **Image Retention**:
   - Keep images forever?
   - Auto-delete after X days?
   - Let users manage lifecycle?

3. **Pricing Model**:
   - Free tier limits?
   - Paid tier pricing?
   - Or internal use only?

4. **Custom Features**:
   - Support batch generation?
   - WebSocket for progress updates?
   - Image variations/editing?

---

**Status**: ✅ Plan Complete - Ready for Review & Implementation
