# Supabase Setup Guide for v2.0

This guide walks you through setting up Supabase Storage and Database for the Image Build Agent v2.0.

---

## Step 1: Create Supabase Storage Bucket

### 1.1 Navigate to Storage

1. Go to https://supabase.com/dashboard
2. Select your project
3. Click **Storage** in the left sidebar

### 1.2 Create Bucket

1. Click **"New bucket"** button
2. Fill in the form:
   - **Name**: `generated-images` (must match your .env)
   - **Public bucket**: ✅ **Check this box** (images need public URLs)
   - **File size limit**: 10 MB (optional, for safety)
   - **Allowed MIME types**: `image/*` (optional, for safety)

3. Click **"Create bucket"**

### 1.3 Verify Bucket

You should see `generated-images` in your bucket list. Click on it to verify it's empty and ready.

---

## Step 2: Set Up Database Schema

### 2.1 Open SQL Editor

1. In Supabase Dashboard, click **SQL Editor** in left sidebar
2. Click **"New query"**

### 2.2 Run Schema

1. Copy the entire contents of `database/schema.sql`
2. Paste into the SQL Editor
3. Click **"Run"** (or press Cmd/Ctrl + Enter)

You should see success messages for:
- ✅ Table created: `generated_images`
- ✅ Indexes created
- ✅ Triggers created
- ✅ RLS policies enabled
- ✅ Views created

### 2.3 Verify Tables

1. Click **Table Editor** in left sidebar
2. You should see:
   - `generated_images` table

Click on it to see the schema with all columns.

---

## Step 3: Test Connection

### 3.1 Test Database Connection

From your v2.0 directory, run:

```bash
cd /Users/pk1980/Documents/Software/deckster-backend/deckster-w-content-strategist/src/agents/image_builder/v2.0

# Activate virtual environment
source .venv/bin/activate

# Test connection
python3 << 'EOF'
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

print("Testing Supabase database connection...")
print("-" * 50)

db_url = os.getenv("DATABASE_URL")

if not db_url or "[YOUR-PASSWORD]" in db_url:
    print("❌ ERROR: DATABASE_URL not configured properly in .env")
    exit(1)

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        # Test basic query
        result = conn.execute(text("SELECT current_database(), current_user, version();"))
        row = result.fetchone()

        print("✅ Database connection successful!")
        print(f"   Database: {row[0]}")
        print(f"   User: {row[1]}")
        print(f"   Version: {row[2][:50]}...")

        # Check if our table exists
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'generated_images';
        """))

        if result.fetchone():
            print("✅ Table 'generated_images' exists!")
        else:
            print("⚠️  Table 'generated_images' not found. Run schema.sql")

except Exception as e:
    print(f"❌ Connection failed: {e}")
    exit(1)
EOF
```

### 3.2 Test Supabase Storage Connection

```bash
python3 << 'EOF'
import os
from dotenv import load_dotenv

load_dotenv()

print("\nTesting Supabase Storage configuration...")
print("-" * 50)

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase_bucket = os.getenv("SUPABASE_BUCKET")

if not supabase_url:
    print("❌ ERROR: SUPABASE_URL not set in .env")
elif not supabase_key:
    print("❌ ERROR: SUPABASE_KEY not set in .env")
elif not supabase_bucket:
    print("❌ ERROR: SUPABASE_BUCKET not set in .env")
else:
    print(f"✅ SUPABASE_URL: {supabase_url}")
    print(f"✅ SUPABASE_KEY: {supabase_key[:20]}...{supabase_key[-10:]}")
    print(f"✅ SUPABASE_BUCKET: {supabase_bucket}")

    # Test Supabase client (if supabase package installed)
    try:
        from supabase import create_client

        client = create_client(supabase_url, supabase_key)

        # Try to list buckets
        buckets = client.storage.list_buckets()
        print(f"\n✅ Supabase client connected!")
        print(f"   Available buckets: {[b.name for b in buckets]}")

        # Check if our bucket exists
        if supabase_bucket in [b.name for b in buckets]:
            print(f"✅ Bucket '{supabase_bucket}' exists!")
        else:
            print(f"⚠️  Bucket '{supabase_bucket}' not found. Create it in Supabase Storage.")

    except ImportError:
        print("\n⚠️  'supabase' package not installed yet")
        print("   Run: pip install -r requirements.txt")
    except Exception as e:
        print(f"\n❌ Supabase connection failed: {e}")

print("\n" + "=" * 50)
print("Setup verification complete!")
EOF
```

---

## Step 4: Install Dependencies (if not done)

```bash
# Make sure you're in v2.0 directory
cd /Users/pk1980/Documents/Software/deckster-backend/deckster-w-content-strategist/src/agents/image_builder/v2.0

# Create/activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

---

## Step 5: Test the API

### 5.1 Start the Server

```bash
# In v2.0 directory with venv activated
uvicorn src.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### 5.2 Test Health Endpoint

In another terminal:

```bash
curl http://localhost:8000/api/v2/health
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
  },
  "timestamp": "2025-10-10T..."
}
```

### 5.3 View API Documentation

Open in browser:
```
http://localhost:8000/docs
```

You should see the interactive OpenAPI documentation.

---

## Step 6: Generate Your First Image (Optional - requires Google Cloud)

If you have Google Cloud set up:

```bash
curl -X POST "http://localhost:8000/api/v2/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A simple blue circle",
    "aspect_ratio": "1:1",
    "options": {
      "store_in_cloud": true
    }
  }'
```

---

## Troubleshooting

### Error: "Database connection failed"

**Check**:
1. Is `DATABASE_URL` in `.env` correct?
2. Did you replace `[YOUR-PASSWORD]` with actual password?
3. Is password URL-encoded if it has special characters?

**Fix**:
```bash
# Verify password in .env
grep DATABASE_URL .env
```

### Error: "Bucket not found"

**Check**:
1. Did you create `generated-images` bucket in Supabase?
2. Is it marked as **Public**?
3. Does `SUPABASE_BUCKET` in `.env` match the bucket name exactly?

**Fix**:
Go to Supabase → Storage → Create bucket named `generated-images`

### Error: "Table 'generated_images' not found"

**Check**:
Did you run the `database/schema.sql` in Supabase SQL Editor?

**Fix**:
1. Open Supabase → SQL Editor
2. Copy contents of `database/schema.sql`
3. Paste and run

### Error: "Authentication failed" (Vertex AI)

**Check**:
1. Is `GOOGLE_CLOUD_PROJECT` set correctly?
2. Have you run `gcloud auth application-default login`?

**Fix**:
```bash
gcloud auth application-default login
gcloud config set project vibe-decker-mvp
```

---

## Checklist

Before running the API, verify:

- [ ] ✅ Supabase project created
- [ ] ✅ Storage bucket `generated-images` created (Public)
- [ ] ✅ Database schema (`schema.sql`) executed
- [ ] ✅ `.env` file configured with all values
- [ ] ✅ Database password replaced (no `[YOUR-PASSWORD]`)
- [ ] ✅ Dependencies installed (`pip install -r requirements.txt`)
- [ ] ✅ Virtual environment activated
- [ ] ✅ Google Cloud authentication set up
- [ ] ✅ Database connection tested successfully
- [ ] ✅ Supabase Storage connection tested
- [ ] ✅ Health check returns "healthy"

---

## Next Steps

Once everything is set up:

1. **Test locally**: Generate images with various aspect ratios
2. **Check Supabase Storage**: See images uploaded to bucket
3. **Check Database**: See metadata in `generated_images` table
4. **Deploy to Railway**: When ready for production

---

## Quick Reference: Environment Variables Needed

```bash
# Google Cloud (Required for image generation)
GOOGLE_CLOUD_PROJECT=vibe-decker-mvp
VERTEX_AI_LOCATION=us-central1

# Supabase (Required for storage and database)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGci...
SUPABASE_BUCKET=generated-images
DATABASE_URL=postgresql://postgres.xxxxx:PASSWORD@aws-0-us-east-2.pooler.supabase.com:6543/postgres

# API (Optional)
API_KEYS=your-secret-key
```

---

**Once all steps are complete, you're ready to generate images!** 🎉
