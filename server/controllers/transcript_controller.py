# app/controllers/transcript_controller.py
from config.db import get_db_connection
from utils.claude_service import ClaudeService 
from utils.read_transcript_from_yt import get_transcript
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TranscriptController:
    def __init__(self):
        self.claude = ClaudeService()

    def store_transcript(self, youtube_url):
        """
        Stores YouTube transcript in database
        Returns: (response_dict, status_code)
        """
        try:
            transcript_result = get_transcript(url=youtube_url)
            
            if not transcript_result['success']:
                logger.error(f"Failed to get transcript: {transcript_result['error']}")
                return {'error': transcript_result['error']}, 400
                
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO transcript (video_id, youtube_url, formatted_transcript)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, (transcript_result['video_id'], 
                          youtube_url, 
                          transcript_result['formatted_transcript']))
                    transcript_id = cur.fetchone()[0]
                conn.commit()
                    
                return {
                    'transcript_id': transcript_id,
                    'message': 'Transcript stored successfully'
                }, 201
            
            finally:
                conn.close()
            
        except Exception as e:
            logger.error(f"Error storing transcript: {str(e)}")
            return {'error': str(e)}, 500

    def analyze_transcript(self, transcript_id):
        """
        Analyzes poker transcript using Claude
        Returns: (response_dict, status_code)
        """
        try:
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT formatted_transcript 
                        FROM transcript 
                        WHERE id = %s
                    """, (transcript_id,))
                    result = cur.fetchone()
                    
                if not result:
                    return {'error': 'Transcript not found'}, 404
                    
                transcript_text = result[0]
                
                # Get analysis from Claude
                analysis = self._analyze_with_claude(transcript_text)
                
                # Store analysis
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO transcript_analysis 
                        (transcript_id, game_location, stakes, caller_cards,
                         preflop_action, preflop_commentary,
                         flop_cards, flop_action, flop_commentary,
                         turn_card, turn_action, turn_commentary,
                         river_card, river_action, river_commentary)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (transcript_id, *analysis.values()))
                    analysis_id = cur.fetchone()[0]
                conn.commit()
                
                return {
                    'analysis_id': analysis_id,
                    'analysis': analysis
                }, 201
            
            finally:
                conn.close()
            
        except Exception as e:
            logger.error(f"Error analyzing transcript: {str(e)}")
            return {'error': str(e)}, 500

    def _analyze_with_claude(self, transcript_text):
        """
        Private method to handle Claude API interaction
        Returns structured analysis dict
        """
        prompt = f"""
        Analyze this poker hand transcript and extract the following information.
        Return ONLY a JSON object with the following structure:
        {{
            "game_location": "string",
            "stakes": "string",
            "caller_cards": "string",
            "preflop_action": {{}},
            "preflop_commentary": "string",
            "flop_cards": "string",
            "flop_action": {{}},
            "flop_commentary": "string",
            "turn_card": "string",
            "turn_action": {{}},
            "turn_commentary": "string",
            "river_card": "string",
            "river_action": {{}},
            "river_commentary": "string"
        }}
        
        Analyze this poker hand transcript:
        {transcript_text}
        """
        
        try:
            response = self.claude.complete(prompt)
            return response
        except Exception as e:
            logger.error(f"Error from Claude API: {str(e)}")
            raise