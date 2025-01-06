# server\utils\read_transcript_from_yt.py
import re
import os
import sys
import csv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

# server\utils\read_transcript_from_yt.py
import logging
import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api._errors import NoTranscriptAvailable, TranscriptsDisabled

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def extract_video_id(url):
    """
    Extract video ID from various forms of YouTube URLs
    """
    if not url:
        return None
        
    # Regular expressions for different YouTube URL formats
    patterns = [
        r'(?:v=|\/videos\/|embed\/|youtu.be\/|\/v\/|\/e\/|watch\?v%3D|watch\?feature=player_embedded&v=)([^#\&\?\n]*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_transcript(url=None, video_id=None, language='en'):
    """
    Get transcript for a YouTube video
    
    Args:
        url (str, optional): YouTube video URL
        video_id (str, optional): YouTube video ID
        language (str, optional): Preferred language code (default: 'en')
    
    Returns:
        dict: Dictionary containing success status and either transcript or error message
    """
    try:
        # Get video ID if URL was provided
        if url and not video_id:
            video_id = extract_video_id(url)
        
        if not video_id:
            return {
                'success': False,
                'error': 'No valid video ID found'
            }

        # Get available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        try:
            # Try to get transcript in preferred language
            transcript = transcript_list.find_transcript([language])
        except NoTranscriptAvailable:
            try:
                # If preferred language not available, try to get any transcript and translate
                transcript = transcript_list.find_transcript([])
                transcript = transcript.translate(language)
            except Exception as e:
                logger.error(f"Translation error: {str(e)}")
                return {
                    'success': False,
                    'error': f'Could not get or translate transcript: {str(e)}'
                }

        # Get the transcript data
        transcript_data = transcript.fetch()
        
        # Format the transcript data
        formatter = TextFormatter()
        formatted_transcript = formatter.format_transcript(transcript_data)

        return {
            'success': True,
            'video_id': video_id,
            'language': transcript.language,
            'transcript': transcript_data,
            'formatted_transcript': formatted_transcript
        }

    except TranscriptsDisabled:
        return {
            'success': False,
            'error': 'Transcripts are disabled for this video'
        }
    except NoTranscriptAvailable:
        return {
            'success': False,
            'error': 'No transcript available for this video'
        }
    except Exception as e:
        logger.error(f"Error getting transcript: {str(e)}")
        return {
            'success': False,
            'error': f'Error getting transcript: {str(e)}'
        }

def main():
    """Test function"""
    # Test URL
    test_url = 'https://www.youtube.com/watch?v=bDf4OvBolAQ'
    
    # Get transcript
    result = get_transcript(url=test_url)
    
    # Print results
    if result['success']:
        print(f"Successfully retrieved transcript for video")
        print(f"Language: {result['language']}")
        print("\nFirst few entries of transcript data:")
        for entry in result['transcript'][:3]:
            print(entry)
        print("\nSample of formatted transcript:")
        print(result['formatted_transcript'][:500] + "...")
    else:
        print(f"Error: {result['error']}")

if __name__ == '__main__':
    main()