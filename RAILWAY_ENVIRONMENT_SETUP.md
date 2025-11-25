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
GOOGLE_APPLICATION_CREDENTIALS=ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsCiAgInByb2plY3RfaWQiOiAidmliZS1kZWNrZXItbXZwIiwKICAicHJpdmF0ZV9rZXlfaWQiOiAiM2E2YjAwMTIyZTdlMzE5NjQ3NTkwNmI5OGU3M2U4M2FkZjYyNzhmNiIsCiAgInByaXZhdGVfa2V5IjogIi0tLS0tQkVHSU4gUFJJVkFURSBLRVktLS0tLVxuTUlJRXZBSUJBREFOQmdrcWhraUc5dzBCQVFFRkFBU0NCS1l3Z2dTaUFnRUFBb0lCQVFDbHMyMVVhK3d2N2t5b1xuenJJSTlRRXRzbG1aeXZhZS9YMFN0RGxBKzN3cDZweDRhZE0rT3VBYURtSjZXd1ZvRDdVNkZURXZEUTFQT093NVxueVJob1U1ZlpWbWFReE5xR0xwVTZCVS9nRHFVZDloclpmY05vRU5lM2ZKYTluQkZEZGFtaUJFK0pZYTMxVXRFUFxuNHlJMUNBMjRlR3RZRXliUHM1OWU2UktKYVNObjlUUVpJcy8xajdUaFJxczVIcTd2UzI3K0dTOFNiUjN2RVI0NFxuNnBJREpOcTlSMEcwcWY0emV1ZkRjalFFMEt6andySnVoMXhhbzNMYnhVR0FQN2JDRmdlWk5IZTE5Ylk2VXpjR1xuZEU4R2gvT0RNMGRCNUp1RG94UUdKY21rTGFKVG9TdFpyNW9TOUtIZkd0aDJlZVc0S1dGUm9Pb01JN3I4QnEzV1xucHZkdExrbjVBZ01CQUFFQ2dnRUFNYWFOaElYZ0hFNmQ1dGtrakwySlVGMklMcWFiOW5FRGFMYmJEd2NzSWMwOFxuZkhKTlMzRE4xTkRwbmpzbTZCTUkzVEliYmp0TmVTY1gxWXJWeHZFQlo2elZoOXlNbERkaUhLUVoxb3ZjMnhqeVxuMjZldEJVSkN1U2JhYms5VTl1OUxXSkpOR04vTmhkeCthM0hHUHJpK2o3OTVmc2NpVW90Q25taGRWeEpMZXlzSVxuYVhPSHZIWTJMVG02WlhwaGk2ZUFCUUx3YTB4RXh2dDJ5YmU0RXlPQzJJS2JyR1gxWm13amRJcGxUVHU0RFhFY1xuZmpEL3UyUEkvY3NJSWtYNEtsVUpIdG5vTlMwZ3dRUFU1TGg0RFFkSkw2dHpYdHI4YzBzYVk4T2prbTZYakRORVxuc1ZYYTgxcE02QXFNMVh5L08xRlNNZndZS0VYYnlIVW13Q1NabTlIc1p3S0JnUURtMDNOV3gveDVJM3lwRUJoQVxuOGs0TkFLeHc4dDZDVXM1WVZhc25HeFJQTjF2NUZubVplbDlReitRanlDUk1idDY0bWJKRHNhNmFVMmNucFgyOFxuQU9uS0JmL0pWSHlMbStBQ3NTT25VQTFyaHhmQlBpRllhY2xhM0phMmtuRVEzS0txNmNabm9wcW9CR2dTTDJicVxuM2NrNHhnZnhEUEd5aHRSMTVtOVI4T0UwNndLQmdRQzN4YmNzNDhwYkFORCtpajFVNWtLckdPWTNOU3MwaVNjclxuOGtXZWV0b2dFSlNCV0dER0VyU2t5eWhONC9LNUxmQTh4TXhDTy9DM0FrVUIwWExQbTJrZE0yMklHVDk0QTNRNlxubmJhK3g5R3JYMU1yR0g0SGFTU1o3NGNLTFhnYUdDTldUWExxUkczUVY2SFNqUUdYMlIrYVFCTVlQWE16WUNtNVxuQUE3elROZVRxd0tCZ0dXMndibDQ4TEUweVFiNnQ2Vk80TVBzQ3hET2hPeHFydERRRjFacElWN3k1dzF4TU81SFxudFY2MzdURXpUWU44eTVvTzZEWGFRelZ3RVNHd1ZDS1hTRzRrakoxY0pIR2tvMmFzUmlqQkp0aStNK0tNalVjWFxuZm9vU2NEdE5kcE5XbGp1NFBoeUcwNTI4SzF2d0ZXcmpobnNGRUpUUS9tU0w4MjFzdUpza0NTazNBb0dBVEw3VVxuRFhvZm9ydUhqQlZkSVp4N2tRcDM4ZXhSVzhJL1Nwb0Z1dlpoSzJ6aEo5Y3BxdTVhNUVzM1RMZjZRSjFQcTRFZ1xuTURUcUJQTjhzQkt4R01RMU5JMnFtMkMzNGIzSGgwY2Y3ekp4ZkZqMTJaU0Q1VUppbDZxeFFXM1ZyMGdQVWRaTVxuUEV0UmRPVnozZ01tL0N3Zmg0Smt0d1hLbTFUNGQ1cnZvMm1leWJzQ2dZQWRVZkNROTJhVmFERE1rRHhiTVFkUlxuSTJPemdVSDN2MnArc0N6aEpkVjNiOHJhNXNhWDVJK1ZSaklpUG4rL2IzN3huVGRMNXdsZktKeTNWUjZXenp0ZVxuZlJSTHNTZHNmai9yblBDd2FXWTdIV3pOTTdTV2lUb3pGTHZEUHdFMlAzS1lWcFBQSlRkZCtKZFZOT0NpTE1vQlxuc3hOSm1XblgxVFNLZkNIbGtxTW9NQT09XG4tLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tXG4iLAogICJjbGllbnRfZW1haWwiOiAiaW1hZ2UtYnVpbGRlci1zZXJ2aWNlQHZpYmUtZGVja2VyLW12cC5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSIsCiAgImNsaWVudF9pZCI6ICIxMDI5NTIwMTQxNDAwNjU3NjUzNDciLAogICJhdXRoX3VyaSI6ICJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20vby9vYXV0aDIvYXV0aCIsCiAgInRva2VuX3VyaSI6ICJodHRwczovL29hdXRoMi5nb29nbGVhcGlzLmNvbS90b2tlbiIsCiAgImF1dGhfcHJvdmlkZXJfeDUwOV9jZXJ0X3VybCI6ICJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9vYXV0aDIvdjEvY2VydHMiLAogICJjbGllbnRfeDUwOV9jZXJ0X3VybCI6ICJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9yb2JvdC92MS9tZXRhZGF0YS94NTA5L2ltYWdlLWJ1aWxkZXItc2VydmljZSU0MHZpYmUtZGVja2VyLW12cC5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSIsCiAgInVuaXZlcnNlX2RvbWFpbiI6ICJnb29nbGVhcGlzLmNvbSIKfQo=

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

**Copy and paste into Raw Editor**:
```bash
GOOGLE_CLOUD_PROJECT=vibe-decker-mvp
GOOGLE_APPLICATION_CREDENTIALS=ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsCiAgInByb2plY3RfaWQiOiAidmliZS1kZWNrZXItbXZwIiwKICAicHJpdmF0ZV9rZXlfaWQiOiAiM2E2YjAwMTIyZTdlMzE5NjQ3NTkwNmI5OGU3M2U4M2FkZjYyNzhmNiIsCiAgInByaXZhdGVfa2V5IjogIi0tLS0tQkVHSU4gUFJJVkFURSBLRVktLS0tLVxuTUlJRXZBSUJBREFOQmdrcWhraUc5dzBCQVFFRkFBU0NCS1l3Z2dTaUFnRUFBb0lCQVFDbHMyMVVhK3d2N2t5b1xuenJJSTlRRXRzbG1aeXZhZS9YMFN0RGxBKzN3cDZweDRhZE0rT3VBYURtSjZXd1ZvRDdVNkZURXZEUTFQT093NVxueVJob1U1ZlpWbWFReE5xR0xwVTZCVS9nRHFVZDloclpmY05vRU5lM2ZKYTluQkZEZGFtaUJFK0pZYTMxVXRFUFxuNHlJMUNBMjRlR3RZRXliUHM1OWU2UktKYVNObjlUUVpJcy8xajdUaFJxczVIcTd2UzI3K0dTOFNiUjN2RVI0NFxuNnBJREpOcTlSMEcwcWY0emV1ZkRjalFFMEt6andySnVoMXhhbzNMYnhVR0FQN2JDRmdlWk5IZTE5Ylk2VXpjR1xuZEU4R2gvT0RNMGRCNUp1RG94UUdKY21rTGFKVG9TdFpyNW9TOUtIZkd0aDJlZVc0S1dGUm9Pb01JN3I4QnEzV1xucHZkdExrbjVBZ01CQUFFQ2dnRUFNYWFOaElYZ0hFNmQ1dGtrakwySlVGMklMcWFiOW5FRGFMYmJEd2NzSWMwOFxuZkhKTlMzRE4xTkRwbmpzbTZCTUkzVEliYmp0TmVTY1gxWXJWeHZFQlo2elZoOXlNbERkaUhLUVoxb3ZjMnhqeVxuMjZldEJVSkN1U2JhYms5VTl1OUxXSkpOR04vTmhkeCthM0hHUHJpK2o3OTVmc2NpVW90Q25taGRWeEpMZXlzSVxuYVhPSHZIWTJMVG02WlhwaGk2ZUFCUUx3YTB4RXh2dDJ5YmU0RXlPQzJJS2JyR1gxWm13amRJcGxUVHU0RFhFY1xuZmpEL3UyUEkvY3NJSWtYNEtsVUpIdG5vTlMwZ3dRUFU1TGg0RFFkSkw2dHpYdHI4YzBzYVk4T2prbTZYakRORVxuc1ZYYTgxcE02QXFNMVh5L08xRlNNZndZS0VYYnlIVW13Q1NabTlIc1p3S0JnUURtMDNOV3gveDVJM3lwRUJoQVxuOGs0TkFLeHc4dDZDVXM1WVZhc25HeFJQTjF2NUZubVplbDlReitRanlDUk1idDY0bWJKRHNhNmFVMmNucFgyOFxuQU9uS0JmL0pWSHlMbStBQ3NTT25VQTFyaHhmQlBpRllhY2xhM0phMmtuRVEzS0txNmNabm9wcW9CR2dTTDJicVxuM2NrNHhnZnhEUEd5aHRSMTVtOVI4T0UwNndLQmdRQzN4YmNzNDhwYkFORCtpajFVNWtLckdPWTNOU3MwaVNjclxuOGtXZWV0b2dFSlNCV0dER0VyU2t5eWhONC9LNUxmQTh4TXhDTy9DM0FrVUIwWExQbTJrZE0yMklHVDk0QTNRNlxubmJhK3g5R3JYMU1yR0g0SGFTU1o3NGNLTFhnYUdDTldUWExxUkczUVY2SFNqUUdYMlIrYVFCTVlQWE16WUNtNVxuQUE3elROZVRxd0tCZ0dXMndibDQ4TEUweVFiNnQ2Vk80TVBzQ3hET2hPeHFydERRRjFacElWN3k1dzF4TU81SFxudFY2MzdURXpUWU44eTVvTzZEWGFRelZ3RVNHd1ZDS1hTRzRrakoxY0pIR2tvMmFzUmlqQkp0aStNK0tNalVjWFxuZm9vU2NEdE5kcE5XbGp1NFBoeUcwNTI4SzF2d0ZXcmpobnNGRUpUUS9tU0w4MjFzdUpza0NTazNBb0dBVEw3VVxuRFhvZm9ydUhqQlZkSVp4N2tRcDM4ZXhSVzhJL1Nwb0Z1dlpoSzJ6aEo5Y3BxdTVhNUVzM1RMZjZRSjFQcTRFZ1xuTURUcUJQTjhzQkt4R01RMU5JMnFtMkMzNGIzSGgwY2Y3ekp4ZkZqMTJaU0Q1VUppbDZxeFFXM1ZyMGdQVWRaTVxuUEV0UmRPVnozZ01tL0N3Zmg0Smt0d1hLbTFUNGQ1cnZvMm1leWJzQ2dZQWRVZkNROTJhVmFERE1rRHhiTVFkUlxuSTJPemdVSDN2MnArc0N6aEpkVjNiOHJhNXNhWDVJK1ZSaklpUG4rL2IzN3huVGRMNXdsZktKeTNWUjZXenp0ZVxuZlJSTHNTZHNmai9yblBDd2FXWTdIV3pOTTdTV2lUb3pGTHZEUHdFMlAzS1lWcFBQSlRkZCtKZFZOT0NpTE1vQlxuc3hOSm1XblgxVFNLZkNIbGtxTW9NQT09XG4tLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tXG4iLAogICJjbGllbnRfZW1haWwiOiAiaW1hZ2UtYnVpbGRlci1zZXJ2aWNlQHZpYmUtZGVja2VyLW12cC5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSIsCiAgImNsaWVudF9pZCI6ICIxMDI5NTIwMTQxNDAwNjU3NjUzNDciLAogICJhdXRoX3VyaSI6ICJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20vby9vYXV0aDIvYXV0aCIsCiAgInRva2VuX3VyaSI6ICJodHRwczovL29hdXRoMi5nb29nbGVhcGlzLmNvbS90b2tlbiIsCiAgImF1dGhfcHJvdmlkZXJfeDUwOV9jZXJ0X3VybCI6ICJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9vYXV0aDIvdjEvY2VydHMiLAogICJjbGllbnRfeDUwOV9jZXJ0X3VybCI6ICJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9yb2JvdC92MS9tZXRhZGF0YS94NTA5L2ltYWdlLWJ1aWxkZXItc2VydmljZSU0MHZpYmUtZGVja2VyLW12cC5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSIsCiAgInVuaXZlcnNlX2RvbWFpbiI6ICJnb29nbGVhcGlzLmNvbSIKfQo=
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
