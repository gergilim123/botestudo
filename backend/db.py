import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "bot_movidesk"),
        user=os.getenv("POSTGRES_USER", "botuser"),
        password=os.getenv("POSTGRES_PASSWORD", "botpass123"),
        cursor_factory=RealDictCursor
    )
