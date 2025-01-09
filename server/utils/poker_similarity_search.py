import numpy as np
from typing import List, Dict, Tuple
from sklearn.metrics.pairwise import cosine_similarity

class PokerSimilaritySearch:
    def __init__(self, embedding_processor):
        self.processor = embedding_processor
        self.hand_embeddings = {}
        self.hand_data = {}
    
    def add_hand(self, hand_id: str, hand_data: Dict):
        """Process and store a new hand with all three embedding strategies"""
        self.hand_data[hand_id] = hand_data
        
        # Store embeddings for each strategy
        self.hand_embeddings[hand_id] = {
            'street_based': self.processor.get_embeddings(
                self.processor.create_street_based_chunks(hand_data)
            ),
            'component_based': self.processor.get_embeddings(
                self.processor.create_component_based_chunks(hand_data)
            ),
            'hybrid': self.processor.get_embeddings(
                self.processor.create_hybrid_chunks(hand_data)
            )
        }
    
    def find_similar_hands(
        self,
        query_hand: Dict,
        strategy: str = 'hybrid',
        n_results: int = 5,
        weights: Dict[str, float] = None
    ) -> List[Tuple[str, float]]:
        """Find similar hands using specified strategy and optional weights"""
        
        # Get query embeddings using specified strategy
        if strategy == 'street_based':
            query_chunks = self.processor.create_street_based_chunks(query_hand)
        elif strategy == 'component_based':
            query_chunks = self.processor.create_component_based_chunks(query_hand)
        else:  # hybrid
            query_chunks = self.processor.create_hybrid_chunks(query_hand)
            
        query_embeddings = self.processor.get_embeddings(query_chunks)
        
        # Calculate similarities
        similarities = {}
        for hand_id, stored_embeddings in self.hand_embeddings.items():
            strategy_embeddings = stored_embeddings[strategy]
            
            # Calculate similarity for each chunk type
            chunk_similarities = {}
            for chunk_type in query_embeddings:
                if chunk_type in strategy_embeddings:
                    sim = cosine_similarity(
                        [query_embeddings[chunk_type]],
                        [strategy_embeddings[chunk_type]]
                    )[0][0]
                    chunk_similarities[chunk_type] = sim
            
            # Weighted average of similarities
            if weights is None:
                weights = {chunk_type: 1.0 for chunk_type in chunk_similarities}
            
            total_weight = sum(
                weights[chunk_type] 
                for chunk_type in chunk_similarities 
                if chunk_type in weights
            )
            
            weighted_sim = sum(
                sim * weights.get(chunk_type, 1.0)
                for chunk_type, sim in chunk_similarities.items()
            ) / total_weight
            
            similarities[hand_id] = weighted_sim
        
        # Return top N results
        return sorted(
            similarities.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n_results]