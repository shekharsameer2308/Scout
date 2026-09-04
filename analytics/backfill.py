import logging
from sqlalchemy import not_
from database.connection import SessionLocal
from database.models.article import Article
from database.models.analytics import SentimentScore, Keyword
from analytics.sentiment.finbert import analyze_batch
from analytics.keyword_extraction.keybert_extractor import extract_keywords_batch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def run_backfill():
    logger.info("Starting NLP Ingestion Backfill Job...")
    db = SessionLocal()
    try:
        # 1. Fetch articles without sentiment scores
        sentiment_subquery = db.query(SentimentScore.article_id).distinct().subquery()
        articles_no_sentiment = db.query(Article).filter(not_(Article.id.in_(sentiment_subquery))).all()
        
        N = len(articles_no_sentiment)
        logger.info(f"[Backfill] Found {N} articles without sentiment scores.")
        
        # Run analyze_batch in groups of 100
        chunk_size = 100
        for i in range(0, N, chunk_size):
            chunk = articles_no_sentiment[i:i+chunk_size]
            analyze_batch(chunk, db)
            
        # 2. Fetch articles without keywords
        keywords_subquery = db.query(Keyword.article_id).distinct().subquery()
        articles_no_keywords = db.query(Article).filter(not_(Article.id.in_(keywords_subquery))).all()
        
        M = len(articles_no_keywords)
        logger.info(f"[Backfill] Found {M} articles without keywords.")
        
        # Run extract_keywords_batch in groups of 100
        for i in range(0, M, chunk_size):
            chunk = articles_no_keywords[i:i+chunk_size]
            extract_keywords_batch(chunk, db)
                
        print(f"Backfill complete: {N} sentiment, {M} keywords processed")
        
    finally:
        db.close()

if __name__ == "__main__":
    run_backfill()
