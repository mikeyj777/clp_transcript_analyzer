from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
import voyageai

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PokerEmbeddingProcessor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = voyageai.Client(api_key=self.api_key)
    
    def create_street_based_chunks(self, hand: Dict = {}, structured_query = None) -> List[str]:
        """Street-based chunking strategy"""
        chunks = []
        
        # Context chunk
        context = ''
        if len(hand) == 0 and not structured_query:
            return chunks
        if len(hand) == 0:
            chunks.append(('context', structured_query))
        else:
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

def get_embeddings(
        self,
        chunks: List[Tuple[str, str]],
        model: str = "voyage-3-large",
        batch_size: int = 128,
        input_type: str = "document"  # Default to document for hand storage
    ) -> Dict[str, List[float]]:
    """
    Generate embeddings for the given chunks using Voyage AI API.
    
    Args:
        chunks: List of tuples containing (chunk_type, chunk_text)
        model: Model to use for embeddings (default: voyage-3-large)
        batch_size: Number of chunks to process in each batch
        input_type: Type of input for embedding ("query" or "document")
            - "query": Optimized for short search queries
            - "document": Optimized for longer content (default)
        
    Returns:
        Dictionary mapping chunk_types to their embedding vectors
    """
    if input_type not in ["query", "document"]:
        raise ValueError("input_type must be either 'query' or 'document'")
        
    embeddings = {}
    texts = [text for _, text in chunks]
    chunk_types = [chunk_type for chunk_type, _ in chunks]
    
    # For queries, we want to use shorter, more focused text
    if input_type == "query":
        # Truncate and focus the text for query embeddings
        texts = [text[:512] for text in texts]  # Arbitrary limit, adjust as needed
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_chunk_types = chunk_types[i:i + batch_size]
        
        try:
            result = self.client.embed(
                input=batch,
                model=model,
                input_type=input_type
            )
            
            for chunk_type, embedding in zip(batch_chunk_types, result.embeddings):
                embeddings[chunk_type] = embedding
                
        except Exception as e:
            logger.error(f"Error generating embeddings for batch {i//batch_size}: {str(e)}")
            raise
    
    return embeddings