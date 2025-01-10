
import os
import sys
from datetime import datetime
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import logging
from typing import Dict, List
import psycopg2.extras

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.db import get_db_connection
from utils.poker_embedding_processor import PokerEmbeddingProcessor
from data.pwds import Pwds

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def prepare_hand_data(row: pd.Series) -> Dict:
    """Convert a DataFrame row into the expected hand data format"""
    return {
        'game_location': row['game_location'],
        'stakes': row['stakes'],
        'caller_cards': row['caller_cards'],
        'preflop_action': row['preflop_action'],
        'preflop_commentary': row['preflop_commentary'],
        'flop_action': row['flop_action'],
        'flop_commentary': row['flop_commentary'],
        'turn_action': row['turn_action'],
        'turn_commentary': row['turn_commentary'],
        'river_action': row['river_action'],
        'river_commentary': row['river_commentary']
    }

def store_embeddings(
    conn,
    hand_id: int,
    chunk_type: str,
    embedding: List[float],
    created_at: datetime
):
    """Store embeddings in the database"""
    cursor = conn.cursor()
    
    try:
        # Convert numpy array to Python list if necessary
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
            
        # Insert the embedding
        cursor.execute("""
            INSERT INTO hand_embeddings 
            (hand_analysis_id, embedding_type, embedding, created_at)
            VALUES (%s, %s, %s, %s)
        """, (hand_id, chunk_type, embedding, created_at))
        
    except Exception as e:
        logger.error(f"Error storing embedding for hand {hand_id}: {str(e)}")
        conn.rollback()
        raise
    finally:
        cursor.close()

def main():
    # Get database connection
    conn = get_db_connection()
    
    try:
        # Read the transcript analysis data
        df = pd.read_sql('SELECT * FROM transcript_analysis', conn)
        logger.info(f"Read {len(df)} rows from transcript_analysis")
        
        # Initialize the embedding processor with your API key
        api_key = Pwds.VOYAGE_AI_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            
        processor = PokerEmbeddingProcessor(api_key)
        
        # Process each hand
        for idx, row in df.iterrows():
            try:
                if row['id'] < 347:
                    continue
                logger.info(f"Processing hand {row['id']}")
                
                # Prepare hand data
                hand_data = prepare_hand_data(row)
                
                # Get embeddings using all three strategies
                strategies = {
                    'street_based': processor.create_street_based_chunks,
                    'component_based': processor.create_component_based_chunks,
                    'hybrid': processor.create_hybrid_chunks
                }
                
                for strategy_name, chunk_func in strategies.items():
                    # Get chunks and embeddings
                    chunks = chunk_func(hand_data)
                    embeddings = processor.get_embeddings(chunks)
                    
                    # Store each embedding
                    for chunk_type, embedding in embeddings.items():
                        store_embeddings(
                            conn,
                            row['id'],
                            f"{strategy_name}_{chunk_type}",
                            embedding,
                            row['created_at']
                        )
                
                # Commit after each hand is processed
                conn.commit()
                logger.info(f"Successfully processed and stored embeddings for hand {row['id']}")
                
            except Exception as e:
                logger.error(f"Error processing hand {row['id']}: {str(e)}")
                conn.rollback()
                continue
                
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()