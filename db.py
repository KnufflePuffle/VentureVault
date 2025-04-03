import sqlite3
from pathlib import Path

# Initialize SQLite database
DB_PATH = Path('s16472_lfg_bot.db')
DB_PATH.parent.mkdir(exist_ok=True)  # Create data directory if it doesn't exist


def init_db():
    """Initialize the database and create necessary tables if they don't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create plotpoints table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS plotpoints (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'Inactive',
        channel_id TEXT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()
