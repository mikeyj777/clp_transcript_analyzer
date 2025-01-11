from typing import Dict, Optional
import re


class HandQueryParser:
    """Parses poker hand queries to match stored hand analysis format"""
    
    @staticmethod
    def parse_position(query: str) -> Optional[str]:
        """Extract position information"""
        positions = {
            'utg': 'UTG',
            'lowjack': 'LowJack',
            'hijack': 'HJ',
            'cutoff': 'cutoff',
            'button': 'button',
            'small blind': 'SB',
            'big blind': 'BB',
            'straddle': 'straddle'
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
            'c': 'Clubs', 's': 'Spades'
        }
        return suits.get(suit.lower(), suit.title())

    @staticmethod
    def parse_cards(query: str) -> Optional[str]:
        """Extract card information in proper English format matching data"""
        # Clean the query
        query = query.lower()
        
        # Look for patterns like "two black aces" or "ace of clubs and ace of spades"
        pairs_pattern = r'two black aces|two red aces'
        if re.search(pairs_pattern, query):
            if 'black aces' in query:
                return 'Ace of Clubs and Ace of Spades'
            if 'red aces' in query:
                return 'Ace of Hearts and Ace of Diamonds'
        
        # Standard "X of Y and A of B" pattern
        pattern = r'(\w+) of (\w+) and (\w+) of (\w+)'
        match = re.search(pattern, query)
        if match:
            rank1, suit1, rank2, suit2 = match.groups()
            # Normalize to proper format
            card1 = f"{HandQueryParser.normalize_rank(rank1)} of {HandQueryParser.normalize_suit(suit1)}"
            card2 = f"{HandQueryParser.normalize_rank(rank2)} of {HandQueryParser.normalize_suit(suit2)}"
            return f"{card1} and {card2}"
        
        return None

    @staticmethod
    def parse_game_info(query: str) -> Dict[str, str]:
        """Extract game type and stakes information"""
        game_info = {}
        
        # Look for stakes patterns like "2/3/5" or "5/10"
        stakes_pattern = r'(?:[\$]?\d+/){1,2}[\$]?\d+'
        stakes_match = re.search(stakes_pattern, query)
        if stakes_match:
            game_info['stakes'] = stakes_match.group(0)
            
        # Look for straddle mentions
        if 'straddle' in query.lower():
            game_info['straddle'] = True
            
        return game_info

    @staticmethod
    def parse_query(query: str) -> Dict:
        """Parse full query into structured format matching hand analysis data"""
        structured_query = {
            'position': HandQueryParser.parse_position(query),
            'hero_cards': HandQueryParser.parse_cards(query),
            'game_info': HandQueryParser.parse_game_info(query)
        }
        return structured_query