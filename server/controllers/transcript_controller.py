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
                analysis = self.analyze_with_claude(transcript_text)
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

    def analyze_with_claude(self, transcript_text):
        """
        Private method to handle Claude API interaction
        Returns structured analysis dict
        """
        prompt = f"""
        Analyze this poker hand transcript and extract the following information.
        Some portions may be missing.  If so, include the element and provide a placeholder value stating "not included".
        Some transcripts will only be hand setups and no commentary.  These are detailing the action at the table and are going to be used to query a database for matching hands.
        Again, include all element tags and use the placeholder stating "not included" if they are missing.
        For each commentary section if commentary is incuded in the transcript, provide detailed analysis of at least 500 characters, capturing Bart's full analysis, 
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
            return self.parse_xml_response(response)
        except Exception as e:
            logger.error(f"Error from Claude API: {str(e)}")
            raise

    def parse_xml_response(self, response):
        """
        Parse XML response into dictionary structure matching our database schema,
        excluding None, 'Not Included', and null values
        """
        import xml.etree.ElementTree as ET
        from io import StringIO
        
        try:
            # Parse XML string
            tree = ET.parse(StringIO(response))
            root = tree.getroot()
            
            # Define fields to extract
            fields = {
                'game_location': 'game_location',
                'stakes': 'stakes',
                'caller_cards': 'caller_cards',
                'preflop_action': 'preflop/action',
                'preflop_commentary': 'preflop/commentary',
                'flop_cards': 'flop/cards',
                'flop_action': 'flop/action',
                'flop_commentary': 'flop/commentary',
                'turn_card': 'turn/card',
                'turn_action': 'turn/action',
                'turn_commentary': 'turn/commentary',
                'river_card': 'river/card',
                'river_action': 'river/action',
                'river_commentary': 'river/commentary'
            }
            
            # Build dictionary, excluding invalid values
            result = {}
            for key, path in fields.items():
                element = root.find(path)
                if element is not None and element.text:
                    # Convert to lower case for case-insensitive comparison
                    text = element.text.strip()
                    text_lower = text.lower()
                    
                    # Skip if value is None, "not included", "null", or empty
                    if (text_lower not in ['none', 'not included', 'null', ''] and 
                        text is not None):
                        result[key] = text
                        
            return result
            
        except Exception as e:
            logger.error(f"Error parsing XML response: {str(e)}")
            logger.debug(f"Raw response: {response}")
            raise ValueError("Failed to parse Claude's XML response")