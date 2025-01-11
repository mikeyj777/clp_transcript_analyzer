from typing import Dict, Optional
import re

class HandQueryParser:
    """Parses poker queries into structured format matching transcript data"""
    
    @staticmethod
    def parse_position(query: str) -> Optional[str]:
        """Extract position information"""
        positions = {
            'utg': 'UTG',
            'lowjack': 'LowJack',
            'hijack': 'HJ',
            'cutoff': 'cutoff',
            'button': 'button',
            'sb': 'small blind',
            'bb': 'big blind',
            'straddle': 'straddle',
            '+1': '+1',  # For positions relative to UTG
            '+2': '+2'
        }
        
        # Look for position mentions in query
        query_lower = query.lower()
        for short, full in positions.items():
            if short in query_lower:
                return full
        return None
    
    @staticmethod
    def normalize_rank(rank: str) -> str:
        """Normalize card rank to proper format"""
        ranks = {
            '2': 'Two', '3': 'Three', '4': 'Four', '5': 'Five',
            '6': 'Six', '7': 'Seven', '8': 'Eight', '9': 'Nine',
            '10': 'Ten', 'j': 'Jack', 'q': 'Queen', 'k': 'King',
            'a': 'Ace'
        }
        return ranks.get(rank.lower(), rank.title())

    @staticmethod
    def normalize_suit(suit: str) -> str:
        """Normalize card suit to proper format"""
        suits = {
            'h': 'Hearts', 'd': 'Diamonds',
            'c': 'Clubs', 's': 'Spades',
            'heart': 'Hearts', 'diamond': 'Diamonds',
            'club': 'Clubs', 'spade': 'Spades'
        }
        return suits.get(suit.lower(), suit.title())

    @staticmethod
    def parse_cards(query: str) -> Optional[str]:
        """Extract card information in proper English format"""
        query = query.lower()
        
        # Handle special patterns
        pairs_pattern = r'(two black|two red) (aces|kings|queens|jacks)'
        match = re.search(pairs_pattern, query)
        if match:
            color, rank = match.groups()
            rank = rank.rstrip('s')  # Remove plural
            if color == 'two black':
                return f"{HandQueryParser.normalize_rank(rank)} of Clubs and {HandQueryParser.normalize_rank(rank)} of Spades"
            if color == 'two red':
                return f"{HandQueryParser.normalize_rank(rank)} of Hearts and {HandQueryParser.normalize_rank(rank)} of Diamonds"
        
        # Standard "X of Y and A of B" pattern
        pattern = r'(\w+) of (\w+) and (\w+) of (\w+)'
        match = re.search(pattern, query)
        if match:
            rank1, suit1, rank2, suit2 = match.groups()
            card1 = f"{HandQueryParser.normalize_rank(rank1)} of {HandQueryParser.normalize_suit(suit1)}"
            card2 = f"{HandQueryParser.normalize_rank(rank2)} of {HandQueryParser.normalize_suit(suit2)}"
            return f"{card1} and {card2}"
        
        return None

    @staticmethod
    def parse_stack_size(query: str) -> Optional[str]:
        """Extract stack size information"""
        pattern = r'(\d+)\s*bb|(\$\d+)\s*stack'
        match = re.search(pattern, query.lower())
        if match:
            bb_size, dollar_size = match.groups()
            return bb_size if bb_size else dollar_size
        return None

    @staticmethod
    def parse_game_info(query: str) -> Dict[str, str]:
        """Extract game information"""
        game_info = {}
        
        # Stakes patterns
        stakes_patterns = [
            r'\$?\d+/\$?\d+/?\$?\d*',  # Matches 2/3/5 or 2/3
            r'\$\d+\s*(?:max\s*)?(?:buy[\s-]*in)',  # Matches $800 max buy-in
            r'(?:nl|pot\s*limit)\s*\d+',  # Matches NL100 or pot limit 200
        ]
        
        for pattern in stakes_patterns:
            match = re.search(pattern, query.lower())
            if match:
                game_info['stakes'] = match.group(0)
                break
        
        # Game type
        game_types = {
            'cash': 'cash game',
            'tournament': 'tournament',
            'mtt': 'tournament',
            'sng': 'sit-n-go',
            'sit and go': 'sit-n-go',
        }
        
        for key, value in game_types.items():
            if key in query.lower():
                game_info['game_type'] = value
                break
        
        # Additional info
        if 'straddle' in query.lower():
            game_info['straddle'] = True
        
        if 'mandatory' in query.lower():
            game_info['mandatory_straddle'] = True
            
        return game_info

    @staticmethod
    def parse_player_info(query: str) -> Dict[str, str]:
        """Extract player-related information"""
        player_info = {}
        
        # Number of players
        players_pattern = r'(\d+)[- ](?:handed|player)'
        match = re.search(players_pattern, query.lower())
        if match:
            player_info['num_players'] = match.group(1)
        
        # Villain types/tendencies
        villains = {
            'maniac': 'aggressive',
            'tight': 'tight',
            'loose': 'loose',
            'passive': 'passive',
            'aggressive': 'aggressive',
            'recreational': 'recreational',
            'reg': 'regular'
        }
        
        for key, value in villains.items():
            if key in query.lower():
                player_info['villain_type'] = value
                break
                
        return player_info

    @staticmethod
    def parse_action_history(query: str) -> Dict[str, str]:
        """Extract any action history mentioned in query"""
        action_history = {}
        
        # Preflop actions
        preflop_patterns = {
            'open': r'(?:utg|hj|co|btn|sb|bb)\s+opens?\s+to\s+\$?\d+',
            '3bet': r'(?:3bet|three[- ]?bet)\s+to\s+\$?\d+',
            'call': r'(?:flat|call)(?:s|ed)?\s+(?:the\s+)?\$?\d+',
            'raise': r'raise[ds]?\s+to\s+\$?\d+'
        }
        
        for action_type, pattern in preflop_patterns.items():
            match = re.search(pattern, query.lower())
            if match:
                action_history['preflop_action'] = match.group(0)
                break
                
        return action_history

    def parse_query(self, query: str) -> Dict:
        """Parse full query into structured format matching transcript data"""
        result = {}
        
        # Check position
        position = self.parse_position(query)
        if position is not None:
            result['position'] = position
            
        # Check hero cards
        hero_cards = self.parse_cards(query)
        if hero_cards is not None:
            result['hero_cards'] = hero_cards
            
        # Check stack size
        stack_size = self.parse_stack_size(query)
        if stack_size is not None:
            result['stack_size'] = stack_size
            
        # Check game info
        game_info = self.parse_game_info(query)
        if game_info:  # Only add if dictionary is not empty
            result['game_info'] = game_info
            
        # Check player info
        player_info = self.parse_player_info(query)
        if player_info:  # Only add if dictionary is not empty
            result['player_info'] = player_info
            
        # Check action history
        action_history = self.parse_action_history(query)
        if action_history:  # Only add if dictionary is not empty
            result['action_history'] = action_history
            
        return result