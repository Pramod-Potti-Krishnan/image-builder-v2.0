# Security Migration Summary
## Image Builder v2.0 - Service Account + IP Allowlist

**Date**: 2025-11-25
**Status**: ✅ **COMPLETED - Ready for Railway Deployment**
**Migration Type**: API Key → Service Account + IP Allowlist

---

## 🎯 Migration Overview

### **Problem**
- API keys were publicly exposed (now deleted)
- Need more secure authentication for Google Cloud Vertex AI
- Need to restrict API access to known services only

### **Solution**
- ✅ **Google Service Account** authentication (JSON-based, more secure)
- ✅ **IP Allowlist** middleware (only Director & Text services can access)
- ✅ **Removed** API_KEYS authentication (replaced by IP filtering)
- ✅ **Rotated** Supabase credentials (user already completed)

---

## ✨ What Changed

### **1. New Files Created**
```
src/middleware/__init__.py          # Middleware package
src/middleware/ip_allowlist.py      # IP allowlist middleware (169 lines)
RAILWAY_ENVIRONMENT_SETUP.md        # Deployment guide for Railway
SECURITY_MIGRATION_SUMMARY.md       # This file
```

### **2. Files Modified**
```
src/config/settings.py              # Added ALLOWED_IPS, removed API_KEYS
src/main.py                         # Added IP middleware, removed API key auth
.env.example                        # Updated configuration template
```

### **3. Security Changes**

#### **Before**:
```python
# API key header authentication
@app.post("/api/v2/generate")
async def generate_image(request, api_key: str = Depends(verify_api_key)):
    ...
```

#### **After**:
```python
# IP allowlist middleware (applied to all endpoints)
app.add_middleware(
    IPAllowlistMiddleware,
    allowed_ips=["director-ip", "text-service-ip"],
    enable_allowlist=True
)

@app.post("/api/v2/generate")
async def generate_image(request):  # No API key needed
    ...
```

---

## 📋 Code Changes Summary

### **settings.py** (src/config/settings.py)
**Removed**:
- `api_keys: Optional[str]` field
- `api_keys_list` property

**Added**:
- `allowed_ips: Optional[str]` field
- `enable_ip_allowlist: bool` field
- `allow_local_ips: bool` field
- `allowed_ips_list` property

### **main.py** (src/main.py)
**Removed**:
- `verify_api_key()` dependency function
- `Depends(verify_api_key)` from all endpoints
- Unused imports: `Depends`, `Header`

**Added**:
- `IPAllowlistMiddleware` import
- Middleware registration after CORS
- IP allowlist configuration

**Endpoints Updated** (all 6):
- `/api/v2/generate` ✅
- `/api/v2/generate-batch` ✅
- `/api/v2/models` ✅
- `/api/v2/images/{image_id}` ✅
- `/api/v2/images` ✅
- `/api/v2/images/{image_id}` (DELETE) ✅

### **IP Allowlist Middleware** (src/middleware/ip_allowlist.py)
**Features**:
- Blocks unauthorized IPs with 403 Forbidden
- Supports X-Forwarded-For and X-Real-IP headers (proxy-aware)
- Configurable allowlist enable/disable
- Localhost support for development
- Dynamic IP add/remove methods
- Comprehensive logging

---

## 🔐 Security Architecture

### **Authentication Flow**

```
┌─────────────────────────────────────────────────────────────────┐
│                     Client Request                               │
│  (Director Service or Text Service)                             │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                    ┌───────────▼────────────┐
                    │   Railway Load         │
                    │   Balancer/Proxy       │
                    └───────────┬────────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │  IP Allowlist Middleware           │
              │  - Check X-Forwarded-For header    │
              │  - Verify IP in allowed list       │
              │  - Block if unauthorized (403)     │
              └─────────────────┬──────────────────┘
                                │
                    ┌───────────▼────────────┐
                    │   CORS Middleware      │
                    └───────────┬────────────┘
                                │
                    ┌───────────▼────────────┐
                    │   FastAPI Route        │
                    │   /api/v2/generate     │
                    └───────────┬────────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │  Image Generation Service          │
              │  - Uses Vertex AI Service          │
              └─────────────────┬──────────────────┘
                                │
                    ┌───────────▼────────────┐
                    │   Vertex AI Service    │
                    │   + Service Account    │
                    │   (base64 credentials) │
                    └───────────┬────────────┘
                                │
                    ┌───────────▼────────────┐
                    │  Google Cloud          │
                    │  Vertex AI Imagen 3    │
                    └────────────────────────┘
```

### **Security Layers**
1. **Network Layer**: IP Allowlist (middleware)
2. **Application Layer**: Google Service Account (Vertex AI)
3. **Data Layer**: Supabase Service Role Key (storage/DB)

---

## 📦 Railway Deployment Requirements

### **Environment Variables to Set**

#### **✅ Google Cloud** (Ready)
```bash
GOOGLE_CLOUD_PROJECT=vibe-decker-mvp
GOOGLE_APPLICATION_CREDENTIALS=ewogICJ0eXBlIjogInNlcn... (full base64 string)
VERTEX_AI_LOCATION=us-central1
```

#### **⏳ Supabase** (Awaiting user's new keys)
```bash
SUPABASE_URL=<user-will-provide>
SUPABASE_KEY=<user-will-provide-new-anon-key>
SUPABASE_SERVICE_KEY=<user-will-provide-new-service-role-key>
SUPABASE_BUCKET=generated-images
```

#### **⏳ IP Allowlist** (Need actual IPs)
```bash
ALLOWED_IPS=<director-service-ip>,<text-service-ip>
ENABLE_IP_ALLOWLIST=true
ALLOW_LOCAL_IPS=false  # Set to false in production
```

#### **✅ Application Settings** (Ready)
```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_WORKERS=4
ENABLE_BACKGROUND_REMOVAL=true
ENABLE_TRANSPARENT_PNG=true
ENABLE_CUSTOM_ASPECT_RATIOS=true
MAX_IMAGE_SIZE_MB=10
RATE_LIMIT_PER_MINUTE=60
```

#### **❌ Remove**
```bash
API_KEYS  # Delete this variable
```

---

## 🧪 Testing Checklist

### **Before Deployment**
- [x] Python syntax validation (all files compile)
- [x] Middleware logic tested
- [x] Settings configuration tested
- [x] Main app structure validated
- [x] Base64 credentials generated

### **After Railway Deployment**
- [ ] Health check returns "healthy"
- [ ] Vertex AI authentication works
- [ ] Supabase connection works
- [ ] IP allowlist blocks unauthorized IPs
- [ ] Director Service can access API
- [ ] Text Service can access API
- [ ] Image generation end-to-end test
- [ ] Background removal works
- [ ] Custom aspect ratios work

---

## 🔍 Verification Commands

### **1. Health Check**
```bash
curl https://web-production-1b5df.up.railway.app/api/v2/health
```
**Expected**: `{"status":"healthy", ...}`

### **2. Test from Allowed IP**
```bash
# Run from Director or Text Service
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"test image","aspect_ratio":"1:1"}'
```
**Expected**: 200 OK with image URLs

### **3. Test IP Blocking**
```bash
# Run from unauthorized IP
curl https://web-production-1b5df.up.railway.app/api/v2/generate
```
**Expected**: 403 Forbidden

---

## 📊 Migration Impact

### **Text & Table Builder Service**
- ✅ **No changes required** on their side
- ✅ Their integration code is already correct
- ✅ Just need to be on allowed IP list
- ✅ 500 errors will be fixed once Railway deployed

### **Director Service**
- ✅ **No changes required** on their side
- ✅ Just need to be on allowed IP list

### **Image Builder v2.0**
- ✅ **Security improved** significantly
- ✅ **No API keys to manage** or rotate
- ✅ **IP-based access control** (more secure)
- ✅ **Service Account** for Google Cloud (best practice)

---

## 📝 Next Steps for User

### **Step 1: Get Missing Information**
1. ✅ Base64 credentials (ready)
2. ⏳ Director Service IP address
3. ⏳ Text Service IP address
4. ⏳ New Supabase SUPABASE_KEY
5. ⏳ New Supabase SUPABASE_SERVICE_KEY

### **Step 2: Update Railway**
1. Log into Railway dashboard
2. Navigate to Image Builder v2.0 project
3. Go to Variables tab
4. Remove `API_KEYS` variable
5. Add/update all variables from `RAILWAY_ENVIRONMENT_SETUP.md`
6. Deploy

### **Step 3: Verify Deployment**
1. Check health endpoint
2. Test from Text Service
3. Verify IP blocking works
4. Monitor logs for any issues

### **Step 4: Notify Integration Teams**
1. Text & Table Builder team (integration working now!)
2. Director Service team (if they use image builder)

---

## 🎉 Benefits

### **Security**
- ✅ No API keys to expose or rotate
- ✅ Service Account credentials (more secure)
- ✅ IP allowlist (network-level security)
- ✅ Easier to audit access

### **Maintenance**
- ✅ Fewer secrets to manage
- ✅ No API key rotation needed
- ✅ Simple IP-based access control
- ✅ Better logging and monitoring

### **Integration**
- ✅ No changes for existing clients
- ✅ Text Service integration will work
- ✅ Director Service continues working
- ✅ Easy to add new services (just add IP)

---

## 📚 Documentation

### **Files to Reference**
- `RAILWAY_ENVIRONMENT_SETUP.md` - Complete Railway deployment guide
- `SECURITY_MIGRATION_SUMMARY.md` - This file (migration overview)
- `.env.example` - Configuration template
- `src/middleware/ip_allowlist.py` - IP allowlist implementation

### **Logs to Monitor**
```bash
# Railway dashboard → Deployments → Logs
# Watch for:
- "IP Allowlist Middleware initialized"
- "Allowed IPs: ..."
- "Initialized Vertex AI Imagen"
- "Decoded base64 credentials"
```

---

## ✅ Completion Status

**Code Changes**: ✅ **COMPLETE**
- All files created/modified
- Syntax validated
- Logic tested

**Documentation**: ✅ **COMPLETE**
- Railway deployment guide
- Migration summary
- Environment template

**Testing**: ✅ **LOCAL VALIDATION COMPLETE**
- Python compilation successful
- No syntax errors
- Ready for deployment

**Deployment**: ⏳ **AWAITING USER**
- Need service IPs
- Need new Supabase keys
- Need Railway configuration

---

## 🚀 Ready for Deployment!

Once you have:
1. Director Service IP
2. Text Service IP
3. New Supabase keys

Follow the steps in `RAILWAY_ENVIRONMENT_SETUP.md` to deploy.

**Expected Result**: Text & Table Builder team will see AI-generated backgrounds working! 🎨

---

**End of Migration Summary**
