import numpy as np
from typing import List, Dict, Tuple
from sklearn.metrics.pairwise import cosine_similarity
import voyageai
from data.pwds import Pwds


def handle_query(query):
    pass

class PokerSimilaritySearch:
    def __init__(self, embedding_processor):
        self.processor = embedding_processor
        self.hand_embeddings = {}
        self.hand_data = {}
        self.vo = voyageai.Client(api_key=Pwds.VOYAGE_AI_API_KEY)
    
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
        weights: Dict[str, float] = None,
        use_reranker: bool = True
    ) -> List[Tuple[str, float]]:
        """
        Find similar hands using specified strategy and optional weights
        
        Args:
            query_hand: Hand data to find similar matches for
            strategy: Embedding strategy ('street_based', 'component_based', or 'hybrid')
            n_results: Number of results to return
            weights: Optional weights for different chunk types
            use_reranker: Whether to use Voyage's reranker for final ranking
        """
        
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
        
        # Get top candidates using embedding similarity
        top_candidates = sorted(
            similarities.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n_results * 2]  # Get 2x candidates for reranking
        
        if use_reranker:
            # Convert query hand to text for reranking
            query_text = self._hand_to_text(query_hand)
            
            # Convert candidate hands to text
            candidate_texts = [
                self._hand_to_text(self.hand_data[hand_id])
                for hand_id, _ in top_candidates
            ]
            
            # Use Voyage reranker
            reranked = self.vo.rerank(
                query_text,
                candidate_texts,
                model="rerank-2",
                top_k=n_results
            )
            
            # Return reranked results
            return [
                (top_candidates[r.index][0], r.relevance_score)
                for r in reranked.results
            ]
        
        # If not using reranker, return top N results
        return top_candidates[:n_results]
    
    def _hand_to_text(self, hand: Dict) -> str:
        """Convert hand data to text format for reranking"""
        text_parts = [
            f"Game: {hand['game_location']}, Stakes: {hand['stakes']}, "
            f"Hero Cards: {hand['caller_cards']}"
        ]
        
        for street in ['preflop', 'flop', 'turn', 'river']:
            action = hand.get(f'{street}_action', '')
            commentary = hand.get(f'{street}_commentary', '')
            if action or commentary:
                text_parts.append(
                    f"{street.upper()}: Action: {action} Commentary: {commentary}"
                )
        
        return " ".join(text_parts)