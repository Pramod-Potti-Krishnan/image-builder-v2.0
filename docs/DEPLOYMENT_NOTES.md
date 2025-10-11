# Deployment Notes - Image Build Agent v2.0

## 📦 Files to Deploy

### Core Application Files
```
src/
├── main.py                          # FastAPI application entry point
├── models/
│   └── image_models.py             # Pydantic models
└── services/
    ├── vertex_ai_service.py        # Vertex AI Imagen integration
    ├── aspect_ratio_engine.py      # Aspect ratio logic
    ├── storage_service.py          # Supabase Storage
    ├── database_service.py         # PostgreSQL metadata
    └── image_generation_service.py # Main orchestrator
```

### Configuration Files
```
requirements.txt                     # Python dependencies
.env.example                        # Environment variable template
Procfile                            # Process definition (Railway/Heroku)
railway.toml                        # Railway configuration
runtime.txt                         # Python version specification
```

### Documentation (Optional)
```
README.md                           # Project overview
QUICKSTART.md                       # Quick start guide
SETUP_GUIDE.md                      # Detailed setup
docs/
├── SUPABASE_STORAGE_SETUP.md      # Supabase configuration guide
└── DEPLOYMENT_NOTES.md            # This file
```

---

## 🚫 Files to EXCLUDE from Production

### Archive Folder (Development Only)
```
archive/                            # DO NOT DEPLOY
├── test_files/                    # Test scripts and results
├── sql_scripts/                   # SQL setup scripts
├── logs/                          # Development logs
├── html_reports/                  # Test reports
└── setup_scripts/                 # Setup utilities
```

### Other Exclusions
```
tests/                             # Unit tests
examples/                          # Example code
database/                          # Local database files
*.log                              # Log files
.env                               # Environment file (use platform secrets)
```

---

## 🔐 Environment Variables Required

### Vertex AI Configuration
```bash
GOOGLE_PROJECT_ID=vibe-decker-mvp
GOOGLE_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

### Supabase Configuration
```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGc...     # Service role key (REQUIRED)
SUPABASE_KEY=eyJhbGc...             # Anon key (fallback)
```

### Application Configuration
```bash
PORT=8000                           # Server port
LOG_LEVEL=INFO                      # Logging level
```

---

## 🚀 Deployment Steps

### 1. Pre-deployment Checklist
- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Supabase bucket created (`generated-images`)
- [ ] RLS policies configured
- [ ] PostgreSQL table created
- [ ] Vertex AI credentials configured
- [ ] Dependencies up to date

### 2. Deploy to Railway/Heroku
```bash
# Railway
railway up

# Heroku
git push heroku main
```

### 3. Verify Deployment
```bash
# Health check
curl https://your-app.railway.app/api/v2/health

# Test generation
curl -X POST https://your-app.railway.app/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A simple test image",
    "aspect_ratio": "1:1",
    "archetype": "minimalist_vector_art"
  }'
```

---

## 📊 Database Setup (One-time)

### Create PostgreSQL Table
Run the SQL from `archive/sql_scripts/create_images_table.sql` in your Supabase SQL editor.

### Configure Storage RLS
Run the SQL from `archive/sql_scripts/disable_rls_for_bucket.sql` in your Supabase SQL editor.

See `docs/SUPABASE_STORAGE_SETUP.md` for detailed instructions.

---

## 🔧 Platform-Specific Configuration

### Railway
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
- **Environment**: Set all variables in Railway dashboard
- **Health Check**: `/api/v2/health`

### Heroku
- **Procfile**: `web: uvicorn src.main:app --host 0.0.0.0 --port $PORT`
- **Buildpack**: `heroku/python`
- **Environment**: Use `heroku config:set`
- **Add-ons**: None required (uses external Supabase)

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY .env.example .env

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 📈 Monitoring and Maintenance

### Logs
Monitor application logs for:
- Image generation failures
- Storage upload errors
- Database connection issues
- Rate limiting warnings

### Metrics to Track
- Images generated per day
- Average generation time
- Storage usage
- Database size
- Error rate

### Regular Maintenance
- Review and archive old images
- Monitor storage costs
- Update dependencies
- Check Vertex AI quotas
- Verify Supabase limits

---

## 🐛 Common Production Issues

### Issue: 500 Error on Image Generation
**Causes**:
- Vertex AI credentials missing/invalid
- Supabase keys incorrect
- Network timeout

**Solution**:
- Check environment variables
- Verify service account permissions
- Increase timeout settings

### Issue: Images Not Uploading to Supabase
**Causes**:
- RLS policies blocking uploads
- Bucket doesn't exist
- Service key not used

**Solution**:
- Verify RLS policies (see SUPABASE_STORAGE_SETUP.md)
- Check `SUPABASE_SERVICE_KEY` is set
- Ensure bucket is created

### Issue: Database Writes Failing
**Causes**:
- Table doesn't exist
- RLS policies blocking
- Connection issues

**Solution**:
- Run table creation SQL
- Check database RLS policies
- Verify Supabase URL and key

---

## 📞 Support and Resources

### Documentation
- Main README: `README.md`
- Setup Guide: `SETUP_GUIDE.md`
- Supabase Guide: `docs/SUPABASE_STORAGE_SETUP.md`

### External Resources
- Vertex AI Imagen: https://cloud.google.com/vertex-ai/docs/generative-ai/image/overview
- Supabase Storage: https://supabase.com/docs/guides/storage
- FastAPI: https://fastapi.tiangolo.com/

---

**Last Updated**: October 2025
**Version**: 2.0
