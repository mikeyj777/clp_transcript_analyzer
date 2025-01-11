from flask import jsonify
from typing import Dict, List, Any
import logging
from datetime import datetime
from config.db import get_db_connection
from utils.query_embedding_processor import QueryEmbeddingProcessor
from utils.claude_service import ClaudeService
from data.pwds import Pwds

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
claude_service = ClaudeService()
query_processor = QueryEmbeddingProcessor(api_key=Pwds.VOYAGE_AI_API_KEY)

def get_similar_hands(query_embedding: List[float], embedding_type: str = 'situation', num_results: int = 5) -> List[Dict[str, Any]]:
    """
    Find similar hands using vector similarity search in PostgreSQL
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Query using vector similarity search with added considerations for position matches
        query = """
        WITH similar_embeddings AS (
            SELECT 
                hand_analysis_id,
                embedding <-> %s::vector as similarity_distance,
                ta.caller_cards,
                ta.preflop_action
            FROM hand_embeddings he
            JOIN transcript_analysis ta ON ta.id = he.hand_analysis_id
            WHERE embedding_type = %s
            ORDER BY similarity_distance ASC
            LIMIT %s * 2  -- Fetch extra results for filtering
        )
        SELECT 
            ta.*,
            se.similarity_distance
        FROM similar_embeddings se
        JOIN transcript_analysis ta ON ta.id = se.hand_analysis_id
        ORDER BY se.similarity_distance ASC
        LIMIT %s;
        """
        
        cur.execute(query, (query_embedding, embedding_type, num_results * 2, num_results))
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
            hand_text = ''
            for k, v in hand.items():
                hand_text += f"{k}: {v}\n" 
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
        
        analysis_prompt = f"""
        
        The query that we're sending you will have all or a portion of a poker hand.
        The hands will mostly be Texas Hold Em Poker, however there may be a few other variations such as Omaha.

        
        Analyze these similar poker hands in relation to the query: '{query}'

        Retrieved similar hands:
        {formatted_hands}

        Assume that the query containts the portion of the hand played so far.  
        The preflop, flop, turn and river action are referred to as different streets of play.

        Use the retrieved similar hands as context for your analysis.  

        As an example, if the query was simply "I'm in the big blind with Ace of Spades and Ace of Clubs", 
        the similar hands could be expected to be played in early position with a premium starting hand.  In this case, assume that this commentary is only about the preflop.  If no betting action was provided, then provide guidance on  

        Provide guidance on how to play the next street of the hand.  
        Give some discussion as to how it has been played so far.

        Use the guidance from the similar hands to state how you would play the next street of the hand.  
        If the query includes other players action, how would you react to their action?  
        The similar hands include commentary about the recommended actions that should have been taken in similar situations.  
        Use these as reference here when providing guidance in your respone.

        If the query contains the full hand, provide your full commentary on each street as it was played.  

        Focus on:
        1. The most relevant aspects of each hand to the query situation
        2. Key patterns in how similar situations were played
        3. Important strategic considerations
        4. Specific actionable recommendations
        5. Common mistakes to avoid

        Format your response with clear sections for:
        1. Overall Analysis - How these hands relate to the query
        2. Key Strategic Patterns
        3. Specific Recommendations
        4. Important Considerations & Risks"""

        return claude_service.complete(analysis_prompt)
        
    except Exception as e:
        logger.error(f"Error analyzing hands with Claude: {e}")
        return "Unable to analyze hands at this time."

def hand_analysis(query: str, num_results: int = 5):
    """
    Main function to analyze poker hands based on user query
    """
    try:
        # Get query embeddings
        query_embeddings = query_processor.embed_query(query)
        logger.debug(f"Generated embeddings for query: {query}")
        if not query_embeddings:
            return jsonify({
                "status": "error",
                "result": "Unable to process query. Please try rephrasing."
            })
        
        # Get situation embedding for similarity search
        query_vector = query_embeddings.get('situation', [])
        if not query_vector:
            return jsonify({
                "status": "error",
                "result": "Unable to generate query embeddings."
            })
        
        # Find similar hands
        similar_hands = get_similar_hands(
            query_vector,
            embedding_type='situation',
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