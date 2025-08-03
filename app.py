#!/usr/bin/env python3
"""
YouTube Transcript Extractor API

FastAPI service for extracting YouTube transcripts using multiple methods.
Designed for n8n automation workflows.
"""

import re
import json
import subprocess
import tempfile
import os
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="YouTube Transcript Extractor API",
    description="Extract transcripts from YouTube videos using multiple fallback methods",
    version="1.0.0"
)

# Add CORS middleware for n8n compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranscriptRequest(BaseModel):
    video_id: str = Field(..., description="YouTube video ID or URL")


class TranscriptResponse(BaseModel):
    success: bool
    video_id: str
    transcript: Optional[str] = None
    method_used: Optional[str] = None
    timestamp: str
    word_count: Optional[int] = None
    character_count: Optional[int] = None
    errors: Optional[list] = None
    error: Optional[str] = None


def extract_video_id(url_or_id: str) -> str:
    """Extract video ID from YouTube URL or return ID if already provided."""
    if len(url_or_id) == 11 and not '/' in url_or_id:
        return url_or_id
    
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    raise ValueError("Invalid YouTube URL or video ID")


def get_transcript_youtube_api(video_id: str) -> tuple[str, str]:
    """Method 1: Try youtube_transcript_api."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        # Try to get transcript directly
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Extract text from transcript data
        text_parts = []
        for entry in transcript_list:
            if isinstance(entry, dict) and 'text' in entry:
                text_parts.append(entry['text'])
        
        if text_parts:
            return ' '.join(text_parts), "youtube_transcript_api"
        
        # If direct method fails, try list transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_generated_transcript(['en'])
        transcript_data = transcript.fetch()
        
        text_parts = []
        for entry in transcript_data:
            if isinstance(entry, dict) and 'text' in entry:
                text_parts.append(entry['text'])
        
        if text_parts:
            return ' '.join(text_parts), "youtube_transcript_api"
        
        raise Exception("No text found in transcript data")
        
    except ImportError:
        raise Exception("youtube_transcript_api not installed")
    except Exception as e:
        raise Exception(f"YouTube Transcript API failed: {e}")


def get_transcript_yt_dlp(video_id: str) -> tuple[str, str]:
    """Method 2: Try yt-dlp to extract subtitles with cookies."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Try to download subtitles using yt-dlp with cookies
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            output_template = os.path.join(temp_dir, "%(title)s.%(ext)s")
            
            # Check if cookies file exists
            cookies_path = "/app/cookies.txt"
            if not os.path.exists(cookies_path):
                logger.warning("Cookies file not found, proceeding without cookies")
                cookies_path = None
            
            cmd = [
                "yt-dlp",
                "--write-auto-subs",
                "--write-subs", 
                "--sub-langs", "en,en-US,en-GB",
                "--skip-download",
                "--no-warnings",
                "--extractor-args", "youtube:skip=dash",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--add-header", "Accept-Language:en-US,en;q=0.9",
                "--add-header", "Accept:text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "--sleep-requests", "1",
                "--sleep-subtitles", "1",
                "--output", output_template,
                video_url
            ]
            
            # Add cookies if available
            if cookies_path:
                cmd.extend(["--cookies", cookies_path])
                logger.info("Using cookies for yt-dlp authentication")
            else:
                logger.warning("No cookies available - may encounter bot detection")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                raise Exception(f"yt-dlp failed: {result.stderr}")
            
            # Look for subtitle files
            subtitle_files = []
            for file in os.listdir(temp_dir):
                if file.endswith(('.vtt', '.srt')):
                    subtitle_files.append(os.path.join(temp_dir, file))
            
            if not subtitle_files:
                raise Exception("No subtitle files found")
            
            # Read the first subtitle file
            with open(subtitle_files[0], 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Clean VTT/SRT format
            text = clean_subtitle_content(content)
            
            if text:
                return text, "yt-dlp"
            else:
                raise Exception("No text extracted from subtitle file")
                
    except subprocess.TimeoutExpired:
        raise Exception("yt-dlp timeout")
    except FileNotFoundError:
        raise Exception("yt-dlp not installed")
    except Exception as e:
        raise Exception(f"yt-dlp method failed: {e}")


def clean_subtitle_content(content: str) -> str:
    """Clean subtitle content (VTT/SRT format)."""
    lines = content.split('\n')
    text_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip empty lines, timestamps, and VTT headers
        if (not line or 
            line.startswith('WEBVTT') or 
            '-->' in line or 
            line.isdigit() or
            line.startswith('NOTE') or
            line.startswith('STYLE')):
            continue
        
        # Remove HTML tags and formatting
        line = re.sub(r'<[^>]+>', '', line)
        line = re.sub(r'&[a-zA-Z]+;', '', line)
        
        if line:
            text_lines.append(line)
    
    return ' '.join(text_lines)


def clean_transcript_text(text: str) -> str:
    """Clean and format transcript text."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common subtitle artifacts
    text = re.sub(r'\[.*?\]', '', text)  # Remove [Music], [Applause], etc.
    text = re.sub(r'\(.*?\)', '', text)  # Remove (background noise), etc.
    
    # Clean up punctuation
    text = re.sub(r'\s+([,.!?])', r'\1', text)
    
    # Capitalize sentences
    sentences = text.split('. ')
    cleaned_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence:
            sentence = sentence[0].upper() + sentence[1:]
            cleaned_sentences.append(sentence)
    
    return '. '.join(cleaned_sentences).strip()


def extract_transcript_internal(video_id: str) -> Dict[str, Any]:
    """Try multiple methods to extract transcript."""
    methods = [
        ("YouTube Transcript API", get_transcript_youtube_api),
        ("yt-dlp", get_transcript_yt_dlp)
    ]
    
    errors = []
    
    for method_name, method_func in methods:
        try:
            text, source = method_func(video_id)
            
            if text and text.strip():
                cleaned_text = clean_transcript_text(text)
                return {
                    "success": True,
                    "video_id": video_id,
                    "transcript": cleaned_text,
                    "method_used": source,
                    "timestamp": datetime.now().isoformat(),
                    "word_count": len(cleaned_text.split()),
                    "character_count": len(cleaned_text)
                }
        except Exception as e:
            error_msg = f"{method_name}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Error in {method_name}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    return {
        "success": False,
        "video_id": video_id,
        "errors": errors,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "YouTube Transcript Extractor API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint for monitoring."""
    return {"status": "ok"}


@app.post("/extract", response_model=TranscriptResponse, tags=["Transcript"])
async def extract_transcript(request: TranscriptRequest):
    """
    Extract transcript from YouTube video.
    
    - **video_id**: YouTube video ID or full URL
    """
    try:
        video_id = extract_video_id(request.video_id)
        result = extract_transcript_internal(video_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail={
                "message": "Could not extract transcript",
                "errors": result.get("errors", []),
                "video_id": video_id
            })
        
        return TranscriptResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail={
            "message": "Invalid video ID or URL",
            "error": str(e)
        })
    except Exception as e:
        logger.error(f"Unexpected error in extract_transcript: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail={
            "message": "Internal server error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })


@app.get("/extract", response_model=TranscriptResponse, tags=["Transcript"])
async def extract_transcript_get(
    video_id: str = Query(..., description="YouTube video ID or URL")
):
    """
    Extract transcript from YouTube video (GET method for n8n compatibility).
    
    - **video_id**: YouTube video ID or full URL
    """
    try:
        logger.info(f"GET request for video_id: {video_id}")
        request = TranscriptRequest(video_id=video_id)
        return await extract_transcript(request)
    except Exception as e:
        logger.error(f"Error in extract_transcript_get: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )