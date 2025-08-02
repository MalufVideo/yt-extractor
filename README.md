# YouTube Transcript Extractor API

A robust FastAPI service for extracting YouTube transcripts using multiple fallback methods. Designed specifically for n8n automation workflows and deployable on Coolify.

## Features

- **Multiple extraction methods**: youtube_transcript_api → yt-dlp fallback
- **Clean JSON API**: RESTful endpoints with structured responses
- **n8n compatible**: Both GET and POST endpoints for automation workflows
- **Docker ready**: Containerized for easy deployment
- **Health checks**: Built-in monitoring endpoints
- **Error handling**: Graceful failure with detailed error messages

## API Endpoints

### Health Check
```
GET /health
GET /
```

### Extract Transcript
```
POST /extract
{
  "video_id": "bFxWRkWAFzs"
}

GET /extract?video_id=bFxWRkWAFzs
```

### Response Format
```json
{
  "success": true,
  "video_id": "bFxWRkWAFzs",
  "transcript": "Clean transcript text...",
  "method_used": "youtube_transcript_api",
  "timestamp": "2025-08-02T19:48:31.604875",
  "word_count": 5618,
  "character_count": 29296
}
```

## Coolify Deployment Guide

### Step 1: Prepare Your Repository

1. Create a new GitHub repository
2. Upload all the files from this directory:
   - `app.py`
   - `Dockerfile`
   - `requirements.txt`
   - `docker-compose.yml`
   - `.dockerignore`

### Step 2: Set Up Coolify Service

1. **Login to Coolify** and navigate to your server dashboard

2. **Create New Service**:
   - Click "New Service" → "Application"
   - Choose "Public Repository"

3. **Configure Repository**:
   - **Repository URL**: `https://github.com/yourusername/youtube-transcript-api`
   - **Branch**: `main` (or your default branch)
   - **Build Pack**: Select "Dockerfile"

4. **Configure Build Settings**:
   - **Dockerfile Location**: `./Dockerfile`
   - **Docker Context**: `.`
   - **Build Command**: Leave empty (uses Dockerfile)

5. **Configure Network Settings**:
   - **Port**: `8000`
   - **Public Port**: `80` or `443` (for HTTPS)
   - **Protocol**: `HTTP`

6. **Configure Domain**:
   - Set your desired domain/subdomain
   - Example: `transcript-api.yourdomain.com`
   - Enable SSL if using HTTPS

7. **Environment Variables** (Optional):
   - Add any custom environment variables if needed
   - For production, you might want to add logging levels

8. **Deploy**: Click "Deploy" to start the build process

### Step 3: Verify Deployment

1. **Check Build Logs**: Monitor the build process in Coolify
2. **Test Health Endpoint**: Visit `https://your-domain.com/health`
3. **Test API**: Try the transcript extraction endpoint

### Step 4: Configure n8n Integration

In your n8n workflow, use HTTP Request node:

**Method**: `GET` or `POST`
**URL**: `https://your-domain.com/extract`

For GET method:
- Add query parameter: `video_id` = `{{your_video_id}}`

For POST method:
- Set Content-Type: `application/json`
- Body:
```json
{
  "video_id": "{{$node["Previous Node"].json["video_id"]}}"
}
```

## Local Development

### Using Docker Compose
```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Using Python directly
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py

# Or with uvicorn
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Testing the API

```bash
# Health check
curl http://localhost:8000/health

# Extract transcript (GET)
curl "http://localhost:8000/extract?video_id=bFxWRkWAFzs"

# Extract transcript (POST)
curl -X POST "http://localhost:8000/extract" \
  -H "Content-Type: application/json" \
  -d '{"video_id": "bFxWRkWAFzs"}'
```

## Troubleshooting

### Common Coolify Issues

1. **Build Fails**:
   - Check build logs in Coolify dashboard
   - Ensure Dockerfile is in repository root
   - Verify requirements.txt syntax

2. **Service Won't Start**:
   - Check if port 8000 is correctly configured
   - Verify health check endpoint responds
   - Check container logs

3. **Can't Access API**:
   - Verify domain DNS settings
   - Check SSL certificate if using HTTPS
   - Ensure firewall allows traffic on configured port

### Dependencies Issues

If you encounter issues with dependencies:

1. **youtube-transcript-api not working**:
   - API falls back to yt-dlp automatically
   - Check if video has transcripts available

2. **yt-dlp fails**:
   - Ensure ffmpeg is installed (included in Dockerfile)
   - Check if video has auto-generated subtitles

## Environment Variables

Optional environment variables you can set in Coolify:

- `PYTHONUNBUFFERED=1` (already set in docker-compose)
- `LOG_LEVEL=info` (for custom logging)
- `MAX_WORKERS=4` (if scaling needed)

## Resource Requirements

- **CPU**: 1 vCPU minimum
- **RAM**: 512MB minimum (1GB recommended)
- **Storage**: 2GB minimum
- **Network**: Outbound internet access required

## Security Considerations

- Service runs as non-root user
- No sensitive data stored
- CORS enabled for web integration
- Health checks prevent zombie containers
- Regular security updates via base image updates