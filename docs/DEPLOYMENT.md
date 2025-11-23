# Vercel Deployment Guide

## 🌐 Live Deployment

**Production URL**: [https://brazillian-cds-datafeeder-v2.vercel.app/](https://brazillian-cds-datafeeder-v2.vercel.app/)

## 📋 Prerequisites

- Python 3.9+
- Vercel account
- Git repository

## 🚀 Quick Deploy

### Method 1: Vercel CLI

1. **Install Vercel CLI**
   ```bash
   npm i -g vercel
   ```

2. **Login to Vercel**
   ```bash
   vercel login
   ```

3. **Deploy**
   ```bash
   vercel
   ```

4. **Deploy to Production**
   ```bash
   vercel --prod
   ```

### Method 2: Git Integration (Recommended)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Deploy FastAPI to Vercel"
   git push origin master
   ```

2. **Import in Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Click "Add New" → "Project"
   - Import your GitHub repository
   - Vercel will auto-detect the configuration

3. **Deploy**
   - Click "Deploy"
   - Vercel will build and deploy automatically

## ⚙️ Configuration Files

### vercel.json
```json
{
  "version": 2,
  "builds": [
    {
      "src": "src/api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "src/api/index.py"
    }
  ],
  "env": {
    "ENVIRONMENT": "production"
  }
}
```

### src/api/index.py
This file is the entry point for Vercel. It imports the FastAPI app from `main.py`.

## 🔧 Environment Variables

Set in Vercel Dashboard under Project Settings → Environment Variables:

| Variable | Value | Description |
|----------|-------|-------------|
| `ENVIRONMENT` | `production` | Deployment environment |
| `API_VERSION` | `2.0.0` | API version string |

## 📁 File Structure for Vercel

```
.
├── src/
│   └── api/
│       └── index.py      # Vercel entry point (required)
├── main.py               # FastAPI app
├── src/                  # Application code
├── public/               # Static files
├── requirements.txt      # Dependencies (required)
└── vercel.json          # Vercel config (required)
```

## ✅ Deployment Checklist

- [ ] `src/api/index.py` exists and imports the app
- [ ] `requirements.txt` has all dependencies
- [ ] `vercel.json` is configured correctly
- [ ] Environment variables are set
- [ ] Code is pushed to Git repository
- [ ] Repository is connected to Vercel

## 🧪 Testing Deployment

After deployment, test these endpoints:

```bash
# Replace YOUR-DEPLOYMENT-URL with your actual URL

# Home page
curl https://YOUR-DEPLOYMENT-URL.vercel.app/

# Health check
curl https://YOUR-DEPLOYMENT-URL.vercel.app/health

# API docs
curl https://YOUR-DEPLOYMENT-URL.vercel.app/docs
```

## 🐛 Troubleshooting

### Build Fails

**Problem**: Build fails with module import errors

**Solution**: Make sure all dependencies are in `requirements.txt`
```bash
pip freeze > requirements.txt
```

### 404 Errors

**Problem**: All routes return 404

**Solution**: Check that `src/api/index.py` properly imports the app:
```python
from main import app
```

### Function Timeout

**Problem**: Requests timeout after 10 seconds

**Solution**: Vercel free tier has 10s timeout. Upgrade or optimize code.

### Static Files Not Loading

**Problem**: HTML template not found or "Template file not found" error

**Solution**: 

1. Ensure `public/` directory is included in the deployment:
   - The `vercel.json` should include static build configuration
   - Check that `public/home.html` exists in the repository

2. The application now supports multiple path resolution strategies:
   - `/var/task/public/home.html` (Vercel serverless)
   - Relative paths for local development
   - Fallback to embedded HTML if template not found

3. Verify environment variables are set:
   ```bash
   ENVIRONMENT=production
   API_VERSION=2.0.0
   ```

4. If the issue persists, check Vercel build logs for file inclusion.

## 📊 Monitoring

### View Logs

1. Go to Vercel Dashboard
2. Select your project
3. Go to "Deployments"
4. Click on a deployment
5. View "Function Logs"

### Performance

- Check response times in Vercel Analytics
- Monitor function invocations
- Track error rates

## 🔄 CI/CD

Vercel automatically deploys:

- **Production**: Pushes to `main` or `master` branch
- **Preview**: Pushes to any other branch or pull requests

### Disable Auto-Deploy

In Vercel Dashboard:
1. Project Settings → Git
2. Disable "Production Branch Auto Deploy"
3. Manually trigger deployments

## 📈 Scaling

### Vercel Limits (Free Tier)

- 10 second function timeout
- 12 deployments per day
- 100 GB bandwidth per month

### Upgrade Options

- **Pro**: $20/month - 60s timeout, more deployments
- **Enterprise**: Custom limits and support

## 🔐 Security

### Environment Variables

Never commit sensitive data. Use Vercel environment variables for:
- API keys
- Database credentials
- Secret tokens

### CORS Configuration

Update CORS settings in `main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## 📚 Additional Resources

- [Vercel Python Documentation](https://vercel.com/docs/functions/serverless-functions/runtimes/python)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vercel CLI Reference](https://vercel.com/docs/cli)

---

Need help? Open an issue on GitHub!
