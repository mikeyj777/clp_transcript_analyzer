from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
import voyageai


class PokerEmbeddingProcessor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = voyageai.Client(api_key=self.api_key)
    
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

    def get_embeddings(
            self,
            chunks: List[Tuple[str, str]],
            model: str = "voyage-3",
            batch_size: int = 128
        ) -> Dict[str, List[float]]:
        """
        Generate embeddings for the given chunks using Voyage AI API.
        
        Args:
            chunks: List of tuples containing (chunk_type, chunk_text)
            model: Model to use for embeddings (default: voyage-3)
            batch_size: Number of chunks to process in each batch
            
        Returns:
            Dictionary mapping chunk_types to their embedding vectors
        """
        
        embeddings = {}
        
        # Group texts by chunk type
        texts = [text for _, text in chunks]
        chunk_types = [chunk_type for chunk_type, _ in chunks]
        
        # Initialize Voyage client
        vo = self.client
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_chunk_types = chunk_types[i:i + batch_size]
            
            try:
                # Generate embeddings for the batch using Voyage API
                result = vo.embed(
                    batch,
                    model=model,
                    input_type="document"  # Using document type since these are text chunks
                )
                
                # Map embeddings to their chunk types
                for chunk_type, embedding in zip(batch_chunk_types, result.embeddings):
                    embeddings[chunk_type] = embedding
                    
            except Exception as e:
                print(f"Error generating embeddings for batch {i//batch_size}: {str(e)}")
                raise
        
        return embeddings