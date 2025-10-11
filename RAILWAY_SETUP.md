# Railway Deployment Setup Guide

## 🚂 Complete Guide to Deploy Image Builder v2.0 on Railway

This guide will help you configure all required environment variables for Railway deployment.

---

## ⚠️ Current Error

Your deployment is failing with:
```
3 validation errors for Settings
google_cloud_project - Field required
supabase_url - Field required
supabase_key - Field required
```

This means Railway doesn't have the required environment variables configured.

---

## 📋 Required Environment Variables

### Step 1: Access Railway Variables

1. Go to your Railway project: https://railway.app/project/your-project
2. Click on your service (`web`)
3. Go to **Variables** tab
4. Click **+ New Variable** for each one below

---

### Step 2: Add Google Cloud / Vertex AI Variables

#### Variable 1: `GOOGLE_CLOUD_PROJECT`
```
GOOGLE_CLOUD_PROJECT=vibe-decker-mvp
```

#### Variable 2: `VERTEX_AI_LOCATION`
```
VERTEX_AI_LOCATION=us-central1
```

#### Variable 3: `GOOGLE_APPLICATION_CREDENTIALS` (Base64 Encoded)

**This is the tricky one!** Railway needs your Google service account JSON as a base64-encoded string.

##### Option A: Use the Helper Script (Easiest)

1. Run the encoder script:
   ```bash
   ./encode_credentials.sh
   ```

2. Enter the path to your service account JSON file when prompted

3. Copy the base64 output

4. In Railway, add variable:
   - Name: `GOOGLE_APPLICATION_CREDENTIALS`
   - Value: [paste the base64 string]

##### Option B: Manual Encoding (macOS/Linux)

```bash
# Encode your service account JSON
base64 -i /path/to/your/service-account-key.json | pbcopy

# This copies the base64 string to your clipboard
# Paste it as the value for GOOGLE_APPLICATION_CREDENTIALS in Railway
```

##### Option C: Manual Encoding (Windows PowerShell)

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\to\service-account-key.json")) | clip
```

---

### Step 3: Add Supabase Variables

#### Variable 4: `SUPABASE_URL`
```
SUPABASE_URL=https://eshvntffcestlfuofwhv.supabase.co
```
(Replace with your actual Supabase project URL)

#### Variable 5: `SUPABASE_SERVICE_KEY` ⚠️ **REQUIRED**
```
SUPABASE_SERVICE_KEY=eyJhbGc...your-service-role-key
```

**How to find it:**
1. Go to your Supabase project: https://supabase.com/dashboard/project/your-project
2. Click **Settings** → **API**
3. Copy the **`service_role`** key (NOT the anon key!)
4. Paste as `SUPABASE_SERVICE_KEY` in Railway

**⚠️ CRITICAL**: You MUST use the service_role key, not the anon key, for backend operations.

#### Variable 6: `SUPABASE_KEY` (Optional Fallback)
```
SUPABASE_KEY=eyJhbGc...your-anon-key
```
(This is the anon/public key from the same Supabase API page)

---

### Step 4: Optional Variables

#### Variable 7: `PORT` (Usually Auto-Set by Railway)
```
PORT=8080
```
Railway usually sets this automatically, but if not, add it.

#### Variable 8: `API_KEYS` (Optional - for API authentication)
```
API_KEYS=your-secret-key-1,your-secret-key-2
```

---

## ✅ Verification Checklist

After adding all variables, verify you have:

- [ ] `GOOGLE_CLOUD_PROJECT` = `vibe-decker-mvp`
- [ ] `VERTEX_AI_LOCATION` = `us-central1`
- [ ] `GOOGLE_APPLICATION_CREDENTIALS` = [long base64 string]
- [ ] `SUPABASE_URL` = `https://xxxxx.supabase.co`
- [ ] `SUPABASE_SERVICE_KEY` = `eyJhbGc...` (service_role key)
- [ ] `SUPABASE_KEY` = `eyJhbGc...` (anon key - optional)

---

## 🚀 Deploy

Once all variables are added:

1. Railway will automatically redeploy
2. Or click **Deploy** button to trigger manual deployment
3. Watch the logs for successful startup:
   ```
   ✅ Image Build Agent v2.0 initialized successfully
   INFO:     Uvicorn running on http://0.0.0.0:8080
   ```

---

## 🧪 Test Your Deployment

Once deployed successfully:

### 1. Health Check
```bash
curl https://your-app.up.railway.app/api/v2/health
```

Expected response:
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

### 2. Generate Test Image
```bash
curl -X POST https://your-app.up.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A simple blue circle",
    "aspect_ratio": "1:1",
    "archetype": "minimalist_vector_art"
  }'
```

---

## 🐛 Troubleshooting

### Error: "Field required" for environment variables

**Cause**: Variables not set in Railway
**Solution**: Follow Steps 1-3 above to add all required variables

### Error: "Permission denied" from Vertex AI

**Cause**: Service account credentials invalid or not decoded properly
**Solution**:
1. Verify your service account JSON is valid
2. Re-encode with the helper script
3. Make sure no extra whitespace in Railway variable

### Error: "Supabase upload failed" or "row violates row-level security"

**Cause**: Using anon key instead of service_role key
**Solution**:
1. Verify you're using `SUPABASE_SERVICE_KEY` with the **service_role** key
2. Check your Supabase RLS policies (see `docs/SUPABASE_STORAGE_SETUP.md`)

### Error: "Application startup failed"

**Cause**: One or more required variables missing
**Solution**: Check Railway logs for which specific variable is missing

---

## 📊 Expected Railway Logs (Success)

```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
2025-10-11 02:22:54 - src.main - INFO - Initializing Image Build Agent v2.0...
2025-10-11 02:22:56 - src.services.vertex_ai_service - INFO - Initialized Vertex AI Imagen (project: vibe-decker-mvp, location: us-central1)
2025-10-11 02:22:56 - src.services.storage_service - INFO - Initialized Supabase Storage (bucket: generated-images)
2025-10-11 02:22:56 - src.services.database_service - INFO - Initialized Image Database Service
2025-10-11 02:22:56 - src.main - INFO - ✅ Image Build Agent v2.0 initialized successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

---

## 🔒 Security Notes

1. **Never commit** `.env` file with actual credentials to Git
2. **Use service_role key** only in backend/server environments (like Railway)
3. **Rotate keys** if accidentally exposed
4. **Enable RLS policies** in Supabase for production security

---

## 📚 Additional Resources

- **Full Deployment Guide**: See `docs/DEPLOYMENT_NOTES.md`
- **Supabase Setup**: See `docs/SUPABASE_STORAGE_SETUP.md`
- **Main README**: See `README.md`

---

## 💡 Quick Reference

| Variable | Where to Find | Example Value |
|----------|---------------|---------------|
| `GOOGLE_CLOUD_PROJECT` | Google Cloud Console → Project Info | `vibe-decker-mvp` |
| `VERTEX_AI_LOCATION` | Google Cloud region | `us-central1` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Service account JSON → Base64 encode | `eyJhbGc...` (long string) |
| `SUPABASE_URL` | Supabase → Settings → API → Project URL | `https://xxxxx.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Supabase → Settings → API → service_role | `eyJhbGc...` (secret key) |
| `SUPABASE_KEY` | Supabase → Settings → API → anon/public | `eyJhbGc...` (public key) |

---

**Need Help?** Check the logs in Railway for specific error messages and refer to the troubleshooting section above.
