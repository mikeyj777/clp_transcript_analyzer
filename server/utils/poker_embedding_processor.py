import pandas as pd
from anthropic import Anthropic
import numpy as np
from typing import Dict, List, Tuple

class PokerEmbeddingProcessor:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
    
    def create_street_based_chunks(self, hand: Dict) -> List[str]:
        """Street-based chunking strategy"""
        chunks = []
        
        # Context chunk
        context = f"Game: {hand['game_location']}, Stakes: {hand['stakes']}, "
        context += f"Hero Cards: {hand['caller_cards']}"
        chunks.append(('context', context))
        
        # Street chunks
        streets = ['preflop', 'flop', 'turn', 'river']
        for street in streets:
            action = hand.get(f'{street}_action', '')
            commentary = hand.get(f'{street}_commentary', '')
            if action or commentary:
                chunks.append((
                    street,
                    f"{street.upper()}: Action: {action} Commentary: {commentary}"
                ))
        
        return chunks
    
    def create_component_based_chunks(self, hand: Dict) -> List[str]:
        """Component-based chunking strategy"""
        # Game context
        context = f"Game: {hand['game_location']}, Stakes: {hand['stakes']}"
        
        # All actions combined
        actions = " ".join([
            f"{street}: {hand.get(f'{street}_action', '')}"
            for street in ['preflop', 'flop', 'turn', 'river']
        ])
        
        # All commentary combined
        commentary = " ".join([
            f"{street}: {hand.get(f'{street}_commentary', '')}"
            for street in ['preflop', 'flop', 'turn', 'river']
        ])
        
        return [
            ('context', context),
            ('actions', actions),
            ('commentary', commentary)
        ]
    
    def create_hybrid_chunks(self, hand: Dict) -> List[str]:
        """Hybrid chunking strategy combining multiple approaches"""
        chunks = []
        
        # Game situation context
        situation = (
            f"Game: {hand['game_location']}, Stakes: {hand['stakes']}, "
            f"Hero Cards: {hand['caller_cards']}"
        )
        chunks.append(('situation', situation))
        
        # Action sequence
        action_sequence = " -> ".join([
            f"{street}: {hand.get(f'{street}_action', '')}"
            for street in ['preflop', 'flop', 'turn', 'river']
        ])
        chunks.append(('action_sequence', action_sequence))
        
        # Individual decision point commentary
        for street in ['preflop', 'flop', 'turn', 'river']:
            commentary = hand.get(f'{street}_commentary', '')
            if commentary:
                chunks.append((
                    f'{street}_decision',
                    f"{street} decision point: {commentary}"
                ))
        
        return chunks
    
    def get_embeddings(self, chunks: List[Tuple[str, str]]) -> Dict:
        """Generate embeddings for chunks using Anthropic's API"""
        embeddings = {}
        for chunk_type, text in chunks:
            embedding = self.client.embeddings.create(
                input=[text],
                model="claude-3-5-sonnet-20241022"
            ).data[0].embedding
            embeddings[chunk_type] = embedding
        return embeddings