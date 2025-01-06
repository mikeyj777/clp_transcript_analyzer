# app/services/claude_service.py
import os
import json
import logging
from anthropic import Anthropic

from data.pwds import Pwds

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ClaudeService:
    def __init__(self):
        self.api_key = Pwds.ANTRHOPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-sonnet-20241022"
        self.system_prompt = """You are a poker hand analyzer. Your task is to extract structured information from poker hand transcripts.
        Focus on identifying:
        1. Game location and stakes
        2. The caller's hole cards
        3. Street by street action including positions and betting
        4. Commentary from Bart
        Keep your analysis precise and poker-specific."""

    def complete(self, user_prompt):
        """
        Send prompt to Claude and return structured analysis
        Returns: dict with analyzed poker hand data
        """
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0,  # Using 0 for consistent, structured output
                system=self.system_prompt,
                messages=[{
                    "role": "user",
                    "content": user_prompt
                }]
            )
            
            # Extract JSON from response
            try:
                # Claude should return a JSON string, but let's be defensive
                response_text = message.content[0].text
                analysis = json.loads(response_text)
                
                # Validate required fields
                required_fields = {
                    'game_location', 'stakes', 'caller_cards',
                    'preflop_action', 'preflop_commentary',
                    'flop_cards', 'flop_action', 'flop_commentary',
                    'turn_card', 'turn_action', 'turn_commentary',
                    'river_card', 'river_action', 'river_commentary'
                }
                
                missing_fields = required_fields - set(analysis.keys())
                if missing_fields:
                    raise ValueError(f"Missing required fields in Claude response: {missing_fields}")
                
                return analysis
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Claude response as JSON: {e}")
                logger.debug(f"Raw response: {response_text}")
                raise ValueError("Claude response was not valid JSON")
                
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            raise

    def _validate_analysis(self, analysis):
        """
        Validate the structure of the analysis
        Returns: bool, error_message
        """
        required_structure = {
            'game_location': str,
            'stakes': str,
            'caller_cards': str,
            'preflop_action': dict,
            'preflop_commentary': str,
            'flop_cards': str,
            'flop_action': dict,
            'flop_commentary': str,
            'turn_card': str,
            'turn_action': dict,
            'turn_commentary': str,
            'river_card': str,
            'river_action': dict,
            'river_commentary': str
        }
        
        for field, expected_type in required_structure.items():
            if field not in analysis:
                return False, f"Missing field: {field}"
            if not isinstance(analysis[field], expected_type):
                return False, f"Invalid type for {field}: expected {expected_type}, got {type(analysis[field])}"
        
        return True, None