# Quick Start Guide - Image Build Agent v2.0

Get up and running in 5 minutes!

## Step 1: Install Dependencies

```bash
cd /path/to/image_builder/v2.0

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

## Step 2: Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit .env with your values
nano .env  # or use your favorite editor
```

**Minimum required**:
```bash
GOOGLE_CLOUD_PROJECT=your-gcp-project
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

## Step 3: Set Up Google Cloud

```bash
# Login
gcloud auth login
gcloud auth application-default login

# Set project
gcloud config set project your-gcp-project

# Enable API
gcloud services enable aiplatform.googleapis.com
```

## Step 4: Set Up Supabase

1. Go to https://supabase.com/dashboard
2. Create a new project (or use existing)
3. Go to **Storage** → Create bucket named `generated-images`
4. Make bucket **Public**
5. Copy **URL** and **anon key** to `.env`

## Step 5: Run the Service

```bash
# Start server
uvicorn src.main:app --reload

# Or use the shortcut
python -m src.main
```

Server runs at: **http://localhost:8000**

## Step 6: Test It!

Open http://localhost:8000/docs in your browser

**Or use curl**:

```bash
curl -X POST "http://localhost:8000/api/v2/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over mountains",
    "aspect_ratio": "2:7"
  }'
```

## What's Next?

- **Deploy to Railway**: See README.md deployment section
- **Add API Keys**: Set `API_KEYS` in `.env` for security
- **Custom Aspect Ratios**: Try `2:7`, `21:9`, `3:5`, etc.
- **Background Removal**: Add `"options": {"remove_background": true}`

---

## Common Issues

### "Authentication failed"
**Fix**: Run `gcloud auth application-default login`

### "Bucket not found"
**Fix**: Create `generated-images` bucket in Supabase Storage

### "No module named 'src'"
**Fix**: Make sure you're in the v2.0 directory

---

**You're ready to generate images! 🎨**
