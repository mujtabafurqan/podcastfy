# Deployment Guide

This document describes how to deploy the Podcastfy async API to Railway.

## Prerequisites

- Node.js and npm (for Railway CLI)
- OpenAI API key
- Gemini API key (optional)

## Quick Deployment

Run the automated deployment script:

```bash
./deploy_railway.sh
```

The script will:
1. Install Railway CLI if needed
2. Login to Railway
3. Create/configure the project
4. Set up PostgreSQL database
5. Configure environment variables
6. Deploy both web and worker services

## Manual Deployment

If you prefer manual control:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init podcastfy-async

# Add database
railway add postgresql

# Set environment variables
railway variables set OPENAI_API_KEY="your-key-here"
railway variables set GEMINI_API_KEY="your-key-here"

# Deploy web service
railway up

# Create and deploy worker service
railway service create worker
railway service --service=worker up
```

## Local Development

To run the services locally:

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Start web service
python -m podcastfy.api.async_app

# Start worker (in another terminal)
python -m podcastfy.worker
```

## Configuration Files

- `railway.json` - Railway deployment configuration
- `procfile` - Process definitions for web and worker services
- `requirements.txt` - Includes production dependencies like gunicorn

## Service URLs

After deployment, you can access:
- Health check: `/api/health`
- Library: `/api/library` 
- Async generation: `/api/generate-async`
- Status check: `/api/status/{job_id}`