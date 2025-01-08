# server\utils\create_table.py
import os
import sys

from config.db import get_db_connection

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create transcripts table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS youtube_transcripts (
            id SERIAL PRIMARY KEY,
            video_id VARCHAR(20) UNIQUE NOT NULL,
            video_url TEXT NOT NULL,
            transcript_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    conn.commit()
    cur.close()
    conn.close()

if __name__ == '__main__':
    init_db()