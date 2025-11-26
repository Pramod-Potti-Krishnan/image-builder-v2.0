# Railway Environment Variables Configuration
## Image Builder v2.0 - Security Migration

**Last Updated**: 2025-11-25
**Status**: Ready for deployment
**Security**: Service Account + IP Allowlist

---

## 🔐 Security Changes Summary

### ✅ **New Security Model**
- **Google Cloud**: Service Account authentication (base64-encoded JSON)
- **API Access**: IP-based allowlist (Director Service + Text Service)
- **Removed**: API_KEYS authentication (replaced by IP allowlist)

### ⚠️ **Action Required**
1. Set Google Cloud service account credentials (base64)
2. Configure allowed IP addresses
3. Update Supabase credentials (already rotated by user)
4. Remove old API_KEYS environment variable

---

## 📋 Required Environment Variables

### **1. Google Cloud / Vertex AI** (✨ Service Account)

```bash
# Project ID
GOOGLE_CLOUD_PROJECT=vibe-decker-mvp

# Service Account Credentials (BASE64 ENCODED)
# ⚠️ REMOVED FOR SECURITY - Generate new credentials and add directly in Railway
# DO NOT commit credentials to git!
GOOGLE_APPLICATION_CREDENTIALS=<BASE64_ENCODED_SERVICE_ACCOUNT_JSON>

# Region
VERTEX_AI_LOCATION=us-central1
```

---

### **2. Supabase Configuration** (🔄 User will provide new keys)

```bash
# Supabase URL
SUPABASE_URL=<your-supabase-url>

# Supabase Anonymous Key (NEW - rotated)
SUPABASE_KEY=<new-anon-key>

# Supabase Service Role Key (NEW - rotated)
SUPABASE_SERVICE_KEY=<new-service-role-key>

# Storage Bucket
SUPABASE_BUCKET=generated-images
```

**⚠️ NOTE**: User has rotated Supabase keys. New keys will be provided by user.

---

### **3. IP Allowlist Security** (✨ New)

```bash
# Comma-separated list of allowed IP addresses
# Format: IP1,IP2,IP3
ALLOWED_IPS=<director-service-ip>,<text-service-ip>

# Enable IP allowlist (should be true in production)
ENABLE_IP_ALLOWLIST=true

# Allow localhost (set to false in production)
ALLOW_LOCAL_IPS=false
```

**📝 TO DO**: Get actual IP addresses for:
- Director Service IP: `<to-be-determined>`
- Text Service IP: `<to-be-determined>`

---

### **4. Application Settings**

```bash
# Environment
ENVIRONMENT=production

# Logging
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_WORKERS=4

# Feature Flags
ENABLE_BACKGROUND_REMOVAL=true
ENABLE_TRANSPARENT_PNG=true
ENABLE_CUSTOM_ASPECT_RATIOS=true

# Resource Limits
MAX_IMAGE_SIZE_MB=10
RATE_LIMIT_PER_MINUTE=60
```

---

## 🚀 Deployment Steps

### **Step 1: Log into Railway**
```bash
# Via browser
https://railway.app
# Navigate to your project: Image Builder v2.0
```

### **Step 2: Navigate to Environment Variables**
1. Click on your service
2. Go to "Variables" tab
3. Click "Raw Editor" for bulk paste

### **Step 3: Remove Old Variables**
**Delete these (no longer used)**:
- `API_KEYS`
- `API_KEY_HEADER`

### **Step 4: Add/Update Variables**

**⚠️ SECURITY WARNING**: Do NOT paste credentials here!
Add them directly in Railway dashboard:
```bash
GOOGLE_CLOUD_PROJECT=vibe-decker-mvp
GOOGLE_APPLICATION_CREDENTIALS=<ADD_NEW_BASE64_CREDENTIALS_IN_RAILWAY>
VERTEX_AI_LOCATION=us-central1
SUPABASE_URL=<user-will-provide>
SUPABASE_KEY=<user-will-provide>
SUPABASE_SERVICE_KEY=<user-will-provide>
SUPABASE_BUCKET=generated-images
ALLOWED_IPS=<director-ip>,<text-service-ip>
ENABLE_IP_ALLOWLIST=true
ALLOW_LOCAL_IPS=false
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

### **Step 5: Save and Deploy**
1. Click "Deploy" to apply changes
2. Railway will automatically redeploy with new environment
3. Monitor deployment logs for any issues

---

## ✅ Verification Steps

### **1. Health Check**
```bash
curl https://web-production-1b5df.up.railway.app/api/v2/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "services": {
    "vertex_ai": true,
    "supabase": true,
    "image_service": true
  }
}
```

### **2. Test Image Generation** (from allowed IP)
```bash
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A simple test image",
    "aspect_ratio": "1:1"
  }'
```

**Expected**: 200 OK with image URLs

### **3. Test IP Blocking** (from unauthorized IP)
```bash
# Should return 403 Forbidden if not from allowed IP
curl -X POST https://web-production-1b5df.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test"}'
```

**Expected**: 403 Forbidden

---

## 🔍 Troubleshooting

### **Issue: "Authentication failed" error**
**Cause**: Google Cloud credentials not properly configured
**Fix**: Verify `GOOGLE_APPLICATION_CREDENTIALS` is the full base64 string (no line breaks)

### **Issue: "403 Forbidden" from valid services**
**Cause**: IP address not in allowlist
**Fix**:
1. Check actual IP of Director/Text services
2. Add to `ALLOWED_IPS`
3. Redeploy

### **Issue**: "Supabase upload failed"
**Cause**: Invalid Supabase credentials
**Fix**: Verify new rotated keys are correct

---

## 📞 Next Steps for User

1. ✅ **Get Service IPs**:
   - Director Service IP address
   - Text Service IP address

2. ✅ **Get New Supabase Credentials**:
   - New SUPABASE_KEY (anon key)
   - New SUPABASE_SERVICE_KEY (service role key)

3. ✅ **Update Railway**:
   - Set all environment variables
   - Deploy changes

4. ✅ **Test**:
   - Health check
   - Image generation from Text Service
   - Verify IP blocking works

---

## 🎯 Security Benefits

### **Before**:
- ❌ API keys (can be exposed in logs, code)
- ❌ Less control over who accesses API
- ❌ Harder to audit access

### **After**:
- ✅ Service Account (secure, scoped permissions)
- ✅ IP allowlist (network-level security)
- ✅ Easy to audit and manage access
- ✅ No secrets in API calls

---

**End of Configuration Guide**
