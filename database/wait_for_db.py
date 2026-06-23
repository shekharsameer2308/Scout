import os
import sys
import time
import logging
from sqlalchemy import create_engine

# Setup simple logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("wait_for_db")

def wait_for_db():
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/scout_db")
    
    # Convert postgres:// to postgresql:// for SQLAlchemy
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
        
    logger.info("Verifying database connectivity...")
    
    # We do not want SQL echoes for this connection check
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        
    max_retries = 30
    retry_interval = 1.0
    
    for attempt in range(1, max_retries + 1):
        try:
            engine = create_engine(database_url, connect_args=connect_args)
            with engine.connect() as connection:
                # Connection was successful
                logger.info("Database is ready and accepting connections!")
                sys.exit(0)
        except Exception as e:
            logger.warning(
                f"[Attempt {attempt}/{max_retries}] Database connection failed: {e}. "
                f"Retrying in {retry_interval}s..."
            )
            time.sleep(retry_interval)
            
    logger.error("Database connection could not be established after maximum retries. Exiting.")
    sys.exit(1)

if __name__ == "__main__":
    wait_for_db()
