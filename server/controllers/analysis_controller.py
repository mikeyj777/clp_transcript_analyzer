from flask import jsonify
import os
from typing import Dict, List, Any
import logging
from datetime import datetime
from config.db import get_db_connection
from utils.poker_embedding_processor import PokerEmbeddingProcessor
from utils.claude_service import ClaudeService
from data.pwds import Pwds
from controllers.transcript_controller import TranscriptController

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
claude_service = ClaudeService()
embedding_processor = PokerEmbeddingProcessor(api_key=Pwds.VOYAGE_AI_API_KEY)
tc = TranscriptController()

def prepare_query_for_search(query: str) -> Dict:
    """
    Use Claude to prepare the query for searching similar hands
    """
    try:
        response = tc.analyze_with_claude(query)
        logging.debug(f'Claude response: {response}')
        return response  # Consider using json.loads with proper formatting
    except Exception as e:
        logger.error(f"Error preparing query with Claude: {e}")
        return {}

def get_similar_hands(query_embedding: List[float], embedding_type: str = 'situation', num_results: int = 5) -> List[Dict[str, Any]]:
    """
    Find similar hands using vector similarity search in PostgreSQL
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Query using vector similarity search
        query = """
        WITH similar_embeddings AS (
            SELECT 
                hand_analysis_id,
                embedding <-> %s::vector as similarity_distance
            FROM hand_embeddings
            WHERE embedding_type = %s
            ORDER BY similarity_distance ASC
            LIMIT %s
        )
        SELECT 
            ta.*,
            se.similarity_distance
        FROM similar_embeddings se
        JOIN transcript_analysis ta ON ta.id = se.hand_analysis_id
        ORDER BY se.similarity_distance ASC;
        """
        
        cur.execute(query, (query_embedding, embedding_type, num_results))
        columns = [desc[0] for desc in cur.description]
        results = [dict(zip(columns, row)) for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Error finding similar hands: {e}")
        return []

def analyze_hands(query: str, hands: List[Dict[str, Any]]) -> str:
    """
    Use Claude to analyze the hands and provide insights using RAG pattern.
    """
    try:
        hands_context = []
        for hand in hands:
            hand_text = (
                f"Game: {hand['game_location']}, Stakes: {hand['stakes']}\n"
                f"Hero Cards: {hand['caller_cards']}\n"
                f"PREFLOP: {hand['preflop_action']}\n"
                f"Commentary: {hand['preflop_commentary']}\n"
            )
            
            if hand['flop_cards']:
                hand_text += (
                    f"FLOP: {hand['flop_cards']}\n"
                    f"Action: {hand['flop_action']}\n"
                    f"Commentary: {hand['flop_commentary']}\n"
                )
            
            if hand['turn_card']:
                hand_text += (
                    f"TURN: {hand['turn_card']}\n"
                    f"Action: {hand['turn_action']}\n"
                    f"Commentary: {hand['turn_commentary']}\n"
                )
            
            if hand['river_card']:
                hand_text += (
                    f"RIVER: {hand['river_card']}\n"
                    f"Action: {hand['river_action']}\n"
                    f"Commentary: {hand['river_commentary']}"
                )
            
            similarity_score = 1 - hand.get('similarity_distance', 0)
            hands_context.append(f"Hand (Similarity: {similarity_score:.2f}):\n{hand_text}\n")
        
        formatted_hands = "\n".join(hands_context)
        
        analysis_prompt = f"""Analyze these similar poker hands in relation to the query: '{query}'

Retrieved similar hands:
{formatted_hands}

Focus on:
1. Patterns and insights across hands
2. The relevance based on similarity scores
3. Key actions and decisions that worked well
4. Common situations and strategic patterns

Format your response with clear sections for:
1. Overall analysis
2. Key patterns identified
3. Specific recommendations
4. Important considerations"""

        return claude_service.complete(analysis_prompt)
        
    except Exception as e:
        logger.error(f"Error analyzing hands with Claude: {e}")
        return "Unable to analyze hands at this time."

def hand_analysis(query: str, num_results: int = 5):
    """
    Main function to analyze poker hands based on user query
    """
    try:
        # Prepare search query
        structured_query = prepare_query_for_search(query)
        logger.debug(f"Structured query: {structured_query}")
        if not structured_query:
            return jsonify({
                "status": "error",
                "result": "Unable to process query format. Please try rephrasing."
            })
        
        # Get query embeddings using hybrid chunking strategy
        query_chunks = embedding_processor.create_hybrid_chunks(structured_query)
        logger.debug(f"Query chunks: {query_chunks}")
        query_embeddings = embedding_processor.get_embeddings(
            chunks=query_chunks,
            model="voyage-3-large",
            input_type="query",
            batch_size=1  # Queries are typically single items
        )
        logger.debug(f"Query embeddings: {query_embeddings}")
        
        # Get the situation embedding for similarity search
        query_vector = query_embeddings.get('situation', [])
        logger.debug(f"Query vector: {query_vector}")
        
        if not query_vector:
            return jsonify({
                "status": "error",
                "result": "Unable to generate query embeddings."
            })
        
        # Find similar hands
        similar_hands = get_similar_hands(
            query_vector,
            embedding_type='situation',  # Match the chunk type we're using for comparison
            num_results=num_results
        )
        
        if not similar_hands:
            return jsonify({
                "status": "success",
                "result": "No similar hands found. Please try a different query."
            })
        
        # Analyze hands and generate insights
        analysis = analyze_hands(query, similar_hands)
        
        # Log successful analysis
        logger.debug(f"Successfully analyzed hand query: {query}")
        
        return jsonify({
            "status": "success",
            "result": analysis,
            "similar_hands": [
                {
                    "hand_id": hand["id"],
                    "game_location": hand["game_location"],
                    "stakes": hand["stakes"],
                    "caller_cards": hand["caller_cards"],
                    "preflop_action": hand["preflop_action"],
                    "flop_cards": hand["flop_cards"],
                    "flop_action": hand["flop_action"],
                    "turn_card": hand["turn_card"],
                    "turn_action": hand["turn_action"],
                    "river_card": hand["river_card"],
                    "river_action": hand["river_action"],
                    "similarity_score": 1 - hand.get("similarity_distance", 0)
                }
                for hand in similar_hands
            ]
        })
        
    except Exception as e:
        logger.error(f"Error in hand analysis: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "result": "An error occurred during analysis. Please try again later."
        })

def main():
    test_query = "in the big blind with two black aces"

if __name__ == "__main__":
    main()