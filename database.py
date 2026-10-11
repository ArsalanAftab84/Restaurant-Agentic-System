import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
db_pool = None

try:
    if DATABASE_URL:
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 20, dsn=DATABASE_URL)
        print("Database pool created successfully.")
    else:
        print("DATABASE_URL is missing from .env")
except Exception as e:
    print(f"CRITICAL: Failed to connect to database. Error: {e}")

def get_db_connection():
    """FastAPI Dependency to manage DB connections per request"""
    if not db_pool:
        raise Exception("Database pool is not initialized.")
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        db_pool.putconn(conn)