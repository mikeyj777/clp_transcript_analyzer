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
        self.analysis = None
        self.transcript = None

    def get_transcript(self, youtube_url):
        """
        Stores YouTube transcript in database
        Returns: (response_dict, status_code)
        """
        try:
            transcript_result = get_transcript(url=youtube_url)
            
            if not transcript_result['success']:
                logger.error(f"Failed to get transcript: {transcript_result['error']}")
                return False
                
            # conn = get_db_connection()
            # try:
            #     with conn.cursor() as cur:
            #         cur.execute("""
            #             SELECT id 
            #             FROM transcript 
            #             WHERE video_id = %s
            #         """, (transcript_result['video_id'],))
            #         existing = cur.fetchone()
                    
            #         if existing:
            #             return {
            #                 'transcript_id': existing[0],
            #                 'message': 'Transcript already exists'
            #             }, 200
                

            #     with conn.cursor() as cur:
            #         cur.execute("""
            #             INSERT INTO transcript (video_id, youtube_url, formatted_transcript)
            #             VALUES (%s, %s, %s)
            #             RETURNING id
            #         """, (transcript_result['video_id'], 
            #               youtube_url, 
            #               transcript_result['formatted_transcript']))
            #         transcript_id = cur.fetchone()[0]
            #     conn.commit()
            
            if not 'formatted_transcript' in transcript_result:
                return False
            
            self.transcript = transcript_result['formatted_transcript']
            return True
            
        # finally:
        #     conn.close()
            
        except Exception as e:
            logger.error(f"Error storing transcript: {str(e)}")
            return {'message': str(e)}

    def analyze_transcript(self, transcript_text, url):
        """
        Analyzes poker transcript using Claude
        Returns: (response_dict, status_code)
        """
        try:
            conn = get_db_connection()
            try:
                
                # Get analysis from Claude
                analysis = self._analyze_with_claude(transcript_text)
                self.analysis = analysis
                # Store analysis
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO transcript_analysis 
                        (url, game_location, stakes, caller_cards,
                         preflop_action, preflop_commentary,
                         flop_cards, flop_action, flop_commentary,
                         turn_card, turn_action, turn_commentary,
                         river_card, river_action, river_commentary)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (url, *analysis.values()))
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
        For each commentary section, provide detailed analysis of at least 500 characters, capturing Bart's full analysis, 
        strategic insights, and explanations of the action. Include any relevant player tendencies, pot odds discussions,
        or strategic concepts Bart mentions.
        Do not use any non-unicode characters.  For example, when describing the suit of a card spell out the suit such as Hearts.  Do not use an icon to represent the suit.
        Return ONLY the information in this XML structure:

        <analysis>
            <game_location>location string</game_location>
            <stakes>stakes string</stakes>
            <caller_cards>cards string.  lower rank card first, with explicit suits for both cards.  For example "Jack of Hearts and Queen of Hearts".</caller_cards>
            
            <preflop>
                <action>detailed action string</action>
                <commentary>Bart's commentary string</commentary>
            </preflop>
            
            <flop>
                <cards>flop cards string</cards>
                <action>detailed action string</action>
                <commentary>Bart's commentary string</commentary>
            </flop>
            
            <turn>
                <card>turn card string</card>
                <action>detailed action string</action>
                <commentary>Bart's commentary string</commentary>
            </turn>
            
            <river>
                <card>river card string</card>
                <action>detailed action string</action>
                <commentary>Bart's commentary string</commentary>
            </river>
        </analysis>

        Analyze this poker hand transcript:
        {transcript_text}
        """
        
        try:
            response = self.claude.complete(prompt)
            # Would need to parse XML response here before returning
            # Could use xml.etree.ElementTree or similar
            return self._parse_xml_response(response)
        except Exception as e:
            logger.error(f"Error from Claude API: {str(e)}")
            raise

    def _parse_xml_response(self, response):
        """
        Parse XML response into dictionary structure matching our database schema
        """
        import xml.etree.ElementTree as ET
        from io import StringIO
        
        try:
            # Parse XML string
            tree = ET.parse(StringIO(response))
            root = tree.getroot()
            
            # Extract values into dict matching our database structure
            return {
                'game_location': root.find('game_location').text,
                'stakes': root.find('stakes').text,
                'caller_cards': root.find('caller_cards').text,
                'preflop_action': root.find('preflop/action').text,
                'preflop_commentary': root.find('preflop/commentary').text,
                'flop_cards': root.find('flop/cards').text,
                'flop_action': root.find('flop/action').text,
                'flop_commentary': root.find('flop/commentary').text,
                'turn_card': root.find('turn/card').text,
                'turn_action': root.find('turn/action').text,
                'turn_commentary': root.find('turn/commentary').text,
                'river_card': root.find('river/card').text,
                'river_action': root.find('river/action').text,
                'river_commentary': root.find('river/commentary').text
            }
        except Exception as e:
            logger.error(f"Error parsing XML response: {str(e)}")
            logger.debug(f"Raw response: {response}")
            raise ValueError("Failed to parse Claude's XML response")