# Supabase Storage Configuration Guide

## 📚 Complete Guide to Configuring Supabase Storage with Row-Level Security (RLS)

This document captures our complete learning journey and best practices for configuring Supabase Storage buckets with proper Row-Level Security policies.

---

## 🎯 Overview

When integrating Supabase Storage into your application, you need to configure:
1. **Storage Bucket** - Container for your files
2. **Row-Level Security (RLS) Policies** - Access control for storage operations
3. **PostgreSQL Database** - Metadata storage (optional but recommended)

---

## 📦 Part 1: Creating the Storage Bucket

### Via Supabase Dashboard
1. Navigate to **Storage** in your Supabase project
2. Click **"New bucket"**
3. Configure:
   - **Name**: `generated-images` (use kebab-case)
   - **Public bucket**: ✅ Enable (for public URL access)
   - **File size limit**: Set as needed (default: 50MB)
   - **Allowed MIME types**: Leave empty for all types, or specify (e.g., `image/png, image/jpeg`)

### Via SQL (Alternative)
```sql
INSERT INTO storage.buckets (id, name, public)
VALUES ('generated-images', 'generated-images', true);
```

---

## 🔐 Part 2: Understanding Row-Level Security (RLS)

### What is RLS?
Row-Level Security is PostgreSQL's mechanism to control which users can access which rows in a table. In Supabase Storage, RLS policies control access to files in `storage.objects` table.

### Key Concepts

#### 1. **Policy Operations**
- `SELECT` - Read/list files
- `INSERT` - Upload files
- `UPDATE` - Modify file metadata
- `DELETE` - Delete files
- `ALL` - All operations

#### 2. **Policy Roles**
- `authenticated` - Logged-in users
- `anon` - Anonymous users
- `service_role` - Backend services (bypass RLS)

#### 3. **Policy Clauses**
- `USING` - Controls which rows can be **read, updated, or deleted**
- `WITH CHECK` - Controls which rows can be **inserted or updated**

⚠️ **CRITICAL**: For `INSERT` operations, use **ONLY** `WITH CHECK`, not `USING`!

---

## 🚨 Common Mistakes and Solutions

### ❌ Mistake 1: Using USING Clause for INSERT
```sql
-- WRONG - Will cause error: "only WITH CHECK expression allowed for INSERT"
CREATE POLICY "Allow uploads"
ON storage.objects FOR INSERT TO authenticated
USING (bucket_id = 'generated-images')        -- ❌ ERROR!
WITH CHECK (bucket_id = 'generated-images');
```

✅ **Solution**:
```sql
-- CORRECT - INSERT only needs WITH CHECK
CREATE POLICY "Allow uploads"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'generated-images');  -- ✅ Correct
```

### ❌ Mistake 2: Separate Policies for Each Operation
Creating individual policies for SELECT, INSERT, UPDATE, DELETE can lead to conflicts and permission issues.

✅ **Solution**: Use a single permissive `ALL` policy:
```sql
CREATE POLICY "Allow all for generated-images"
ON storage.objects FOR ALL
USING (bucket_id = 'generated-images')
WITH CHECK (bucket_id = 'generated-images');
```

### ❌ Mistake 3: Not Considering Service Role
Even with `service_role` credentials, RLS policies can block operations if not properly configured.

✅ **Solution**: Ensure your policy allows the intended operations or use permissive `ALL` policy.

---

## ✅ Recommended RLS Policy Configuration

### Option 1: Permissive ALL Policy (Simplest)
**Best for**: Development, internal tools, trusted environments

```sql
-- Drop existing policies
DROP POLICY IF EXISTS "Allow all for generated-images" ON storage.objects;

-- Create permissive policy
CREATE POLICY "Allow all for generated-images"
ON storage.objects FOR ALL
USING (bucket_id = 'generated-images')
WITH CHECK (bucket_id = 'generated-images');
```

**Advantages**:
- ✅ Simple and straightforward
- ✅ Works for all operations
- ✅ No permission conflicts
- ✅ Works with service_role and authenticated users

**Disadvantages**:
- ⚠️ Less granular control
- ⚠️ Anyone can delete files (if bucket is public)

### Option 2: Granular Policies (More Secure)
**Best for**: Production, multi-tenant applications

```sql
-- Policy for uploading (INSERT)
CREATE POLICY "Allow authenticated uploads"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'generated-images');

-- Policy for reading (SELECT)
CREATE POLICY "Allow public reads"
ON storage.objects FOR SELECT
USING (bucket_id = 'generated-images');

-- Policy for updating (UPDATE)
CREATE POLICY "Allow authenticated updates"
ON storage.objects FOR UPDATE TO authenticated
USING (bucket_id = 'generated-images')
WITH CHECK (bucket_id = 'generated-images');

-- Policy for deleting (DELETE)
CREATE POLICY "Allow authenticated deletes"
ON storage.objects FOR DELETE TO authenticated
USING (bucket_id = 'generated-images');
```

**Advantages**:
- ✅ Fine-grained access control
- ✅ Can restrict who can delete/update
- ✅ Better audit trail

**Disadvantages**:
- ⚠️ More complex
- ⚠️ Potential for policy conflicts
- ⚠️ Harder to debug

---

## 🔧 Implementation in Python

### Setup Service
```python
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

class SupabaseStorageService:
    def __init__(self):
        # Use service_role key for backend operations
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_KEY")  # NOT anon key!

        self.client = create_client(self.url, self.key)
        self.bucket_name = "generated-images"

    def upload_image(self, file_path: str, image_bytes: bytes) -> str:
        """
        Upload image to Supabase Storage.

        Args:
            file_path: Path within bucket (e.g., "generated/image_123.png")
            image_bytes: Image data as bytes

        Returns:
            Public URL of uploaded image
        """
        # Upload to storage
        response = self.client.storage.from_(self.bucket_name).upload(
            path=file_path,
            file=image_bytes,
            file_options={"content-type": "image/png"}
        )

        # Get public URL
        public_url = self.client.storage.from_(self.bucket_name).get_public_url(file_path)

        return public_url
```

### Environment Variables
```bash
# .env file
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGc...  # Service role key (NOT anon key)
SUPABASE_KEY=eyJhbGc...           # Fallback to anon key if service key not available
```

---

## 🗄️ Part 3: PostgreSQL Database for Metadata

### Why Store Metadata?
While Supabase Storage handles file storage, storing metadata in PostgreSQL provides:
- 🔍 Fast querying and filtering
- 📊 Analytics and statistics
- 🔗 Relations with other data
- 📝 Additional custom fields

### Database Schema
```sql
-- Drop existing table if needed
DROP TABLE IF EXISTS public.generated_images CASCADE;

-- Create images table
CREATE TABLE public.generated_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id TEXT UNIQUE NOT NULL,
    prompt TEXT NOT NULL,
    aspect_ratio TEXT NOT NULL,
    archetype TEXT NOT NULL,

    -- Image URLs
    original_url TEXT,
    cropped_url TEXT,
    transparent_url TEXT,

    -- Storage paths
    original_path TEXT,
    cropped_path TEXT,
    transparent_path TEXT,

    -- Generation metadata
    source_aspect_ratio TEXT,
    target_aspect_ratio TEXT,
    negative_prompt TEXT,
    crop_anchor TEXT DEFAULT 'center',
    model TEXT DEFAULT 'imagen-3.0-generate-002',
    platform TEXT DEFAULT 'vertex-ai',

    -- Performance metrics
    generation_time_ms INTEGER,
    original_size_bytes INTEGER,
    cropped_size_bytes INTEGER,
    transparent_size_bytes INTEGER,

    -- Flags
    background_removed BOOLEAN DEFAULT false,
    cropped BOOLEAN DEFAULT false,

    -- Additional metadata (flexible JSONB)
    metadata JSONB,
    tags TEXT[],
    created_by TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX idx_images_archetype ON public.generated_images(archetype);
CREATE INDEX idx_images_aspect_ratio ON public.generated_images(aspect_ratio);
CREATE INDEX idx_images_created_at ON public.generated_images(created_at DESC);
CREATE INDEX idx_images_image_id ON public.generated_images(image_id);

-- Enable RLS
ALTER TABLE public.generated_images ENABLE ROW LEVEL SECURITY;

-- Permissive policy (adjust for production)
CREATE POLICY "Allow all for generated images"
ON public.generated_images FOR ALL
USING (true)
WITH CHECK (true);
```

### Database Service (Python)
```python
from supabase import create_client
from typing import Optional, Dict, Any

class ImageDatabaseService:
    def __init__(self):
        load_dotenv()
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_KEY")
        self.client = create_client(self.url, self.key)

    def save_image_record(
        self,
        image_id: str,
        prompt: str,
        aspect_ratio: str,
        urls: Dict[str, str],
        **metadata
    ) -> Dict[str, Any]:
        """Save image metadata to database."""
        record = {
            "image_id": image_id,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "original_url": urls.get("original"),
            "cropped_url": urls.get("cropped"),
            "transparent_url": urls.get("transparent"),
            **metadata
        }

        response = self.client.table("generated_images").insert(record).execute()
        return {"success": True, "record": response.data[0]}

    def get_image_by_id(self, image_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve image record by ID."""
        response = self.client.table("generated_images") \
            .select("*") \
            .eq("image_id", image_id) \
            .execute()

        return response.data[0] if response.data else None
```

---

## 🧪 Testing Your Configuration

### Test 1: Verify Bucket Exists
```python
# List all buckets
buckets = supabase.storage.list_buckets()
print([b.name for b in buckets])
# Should include 'generated-images'
```

### Test 2: Verify RLS Policies
```sql
-- Check policies on storage.objects
SELECT
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'storage'
AND tablename = 'objects'
AND qual::text LIKE '%generated-images%';
```

### Test 3: Test Upload
```python
# Test upload
test_data = b"test image data"
response = supabase.storage.from_("generated-images").upload(
    "test/test.png",
    test_data
)
print(f"Upload successful: {response}")

# Get public URL
url = supabase.storage.from_("generated-images").get_public_url("test/test.png")
print(f"Public URL: {url}")
```

---

## 📋 Troubleshooting Checklist

### Issue: "new row violates row-level security policy"

✅ **Check**:
1. Are you using `SUPABASE_SERVICE_KEY` (not anon key)?
2. Is the RLS policy permissive enough?
3. Does the policy include the operation you're attempting?
4. Is `bucket_id` correctly specified in the policy?

✅ **Solution**:
```sql
-- Verify current policies
SELECT * FROM pg_policies
WHERE tablename = 'objects';

-- Drop and recreate with permissive policy
DROP POLICY IF EXISTS "Allow all for generated-images" ON storage.objects;

CREATE POLICY "Allow all for generated-images"
ON storage.objects FOR ALL
USING (bucket_id = 'generated-images')
WITH CHECK (bucket_id = 'generated-images');
```

### Issue: "only WITH CHECK expression allowed for INSERT"

✅ **Solution**: Remove `USING` clause from INSERT policy:
```sql
-- WRONG
CREATE POLICY "..." FOR INSERT
USING (...)           -- ❌ Remove this
WITH CHECK (...);

-- CORRECT
CREATE POLICY "..." FOR INSERT
WITH CHECK (...);     -- ✅ Only WITH CHECK
```

### Issue: Files uploading but URLs not accessible

✅ **Check**:
1. Is the bucket set to `public`?
2. Is there a SELECT policy allowing reads?

✅ **Solution**:
```sql
-- Make bucket public
UPDATE storage.buckets
SET public = true
WHERE id = 'generated-images';

-- Add SELECT policy
CREATE POLICY "Allow public reads"
ON storage.objects FOR SELECT
USING (bucket_id = 'generated-images');
```

---

## 🎓 Key Learnings Summary

1. **Use Service Role Key**: Backend services should use `SUPABASE_SERVICE_KEY`, not the anon key
2. **INSERT Policies**: Only use `WITH CHECK`, never `USING`
3. **Permissive Policies**: Start with a simple `ALL` policy, then restrict as needed
4. **Public Buckets**: Enable public access if you need public URLs
5. **Database + Storage**: Store file metadata in PostgreSQL for better querying
6. **Environment Variables**: Always use environment variables, never hardcode keys
7. **Testing**: Test each component (bucket, RLS, upload, URL access) independently

---

## 🚀 Production Checklist

Before deploying to production:

- [ ] Bucket created and configured
- [ ] RLS policies tested and verified
- [ ] Service role key configured in environment
- [ ] Database table created with proper indexes
- [ ] Upload/download tested successfully
- [ ] Public URLs accessible
- [ ] Error handling implemented
- [ ] Logging configured
- [ ] Rate limiting considered
- [ ] File size limits set
- [ ] MIME type restrictions (if needed)
- [ ] Cleanup/retention policy defined

---

## 📚 Additional Resources

- [Supabase Storage Documentation](https://supabase.com/docs/guides/storage)
- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Supabase Storage RLS Guide](https://supabase.com/docs/guides/storage/security/access-control)

---

**Document Version**: 1.0
**Last Updated**: October 2025
**Maintained By**: Image Build Agent v2.0 Team
