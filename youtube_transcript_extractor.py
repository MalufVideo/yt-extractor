#!/usr/bin/env python3
"""
YouTube Transcript Extractor

This script extracts transcripts from YouTube videos using multiple methods and outputs JSON.
Usage: python youtube_transcript_extractor.py <video_url_or_id>
"""

import sys
import re
import json
import subprocess
import tempfile
import os
from datetime import datetime


def extract_video_id(url_or_id):
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


def get_transcript_youtube_api(video_id):
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


def get_transcript_yt_dlp(video_id):
    """Method 2: Try yt-dlp to extract subtitles."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Try to download subtitles using yt-dlp
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            output_template = os.path.join(temp_dir, "%(title)s.%(ext)s")
            
            cmd = [
                "yt-dlp",
                "--write-auto-subs",
                "--write-subs",
                "--sub-langs", "en",
                "--skip-download",
                "--output", output_template,
                video_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
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


def clean_subtitle_content(content):
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


def clean_transcript_text(text):
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


def extract_transcript(video_id):
    """Try multiple methods to extract transcript."""
    methods = [
        ("YouTube Transcript API", get_transcript_youtube_api),
        ("yt-dlp", get_transcript_yt_dlp)
    ]
    
    errors = []
    
    for method_name, method_func in methods:
        try:
            print(f"Trying {method_name}...")
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
            print(f"Failed: {error_msg}")
    
    return {
        "success": False,
        "video_id": video_id,
        "errors": errors,
        "timestamp": datetime.now().isoformat()
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: python youtube_transcript_extractor.py <video_url_or_id>")
        sys.exit(1)
    
    video_input = sys.argv[1]
    
    try:
        video_id = extract_video_id(video_input)
        print(f"Extracting transcript for video ID: {video_id}")
        
        result = extract_transcript(video_id)
        
        print("\n" + "="*50)
        print("TRANSCRIPT RESULT (JSON)")
        print("="*50)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if not result["success"]:
            sys.exit(1)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()