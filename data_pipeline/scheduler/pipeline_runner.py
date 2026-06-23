import argparse
import logging
from sqlalchemy.orm import Session
from database.connection import SessionLocal, engine, Base
from database.models.article import Article
from database.models.competitor import CompetitorMention
from data_pipeline.collectors import newsapi_collector, rss_collector
from data_pipeline.processors import cleaner, classifier
from analytics.topic_modeling.bertopic_model import run_topic_modeling

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Hardcoded watchlist of 20 companies for competitor intelligence (Phase 7)
WATCHLIST = [
    "Tesla", "BYD", "Toyota", "Ford", "GM", "Samsung", "TSMC",
    "Apple", "Google", "Microsoft", "Amazon", "Meta", "Nvidia",
    "Tata", "Reliance", "Shell", "BP", "ExxonMobil", "Siemens", "Bosch"
]

INDUSTRIES = ["logistics", "pharma", "agriculture", "defense"]

def run_pipeline(dry_run: bool = False, run_topics_flag: bool = False):
    """Orchestrates the data pipeline ingestion flow."""
    logger.info(f"Starting Scout Data Ingestion Pipeline (Dry Run: {dry_run})")
    
    # 1. Fetch articles from all sources
    logger.info("Collecting articles from NewsAPI...")
    newsapi_articles = newsapi_collector.fetch_all_industries(INDUSTRIES)
    
    logger.info("Collecting articles from RSS feeds...")
    rss_articles = rss_collector.fetch_all_rss()
    
    combined_raw = newsapi_articles + rss_articles
    logger.info(f"Total raw articles collected: {len(combined_raw)}")
    
    # 2. Clean and process batch
    logger.info("Cleaning and normalizing articles...")
    processed_articles = cleaner.process_batch(combined_raw)
    
    # Initialize DB session if not dry run
    db: Session = None
    if not dry_run:
        # Ensure tables exist
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        
        # Lazy load heavy ML packages only when database writes are active
        from analytics.sentiment.finbert import analyze_sentiment
        from analytics.keyword_extraction.keybert_extractor import extract_keywords
        from rag.embedding import embed_and_store
        
    inserted_count = 0
    duplicate_count = 0
    error_count = 0
    
    # 3. Ingestion Loop
    for art_dict in processed_articles:
        url = art_dict.get("url")
        title = art_dict.get("title")
        content = art_dict.get("content")
        industry = art_dict.get("industry")
        
        if not url:
            logger.warning(f"Skipping article with no URL: {title[:30]}")
            continue
            
        # Re-classify industry to verify category and confidence (Phase 2 Task 4)
        classified_ind, confidence = classifier.classify_industry(content or title)
        if classified_ind != "general" and classified_ind != industry:
            logger.info(f"Overriding collector industry '{industry}' with classified industry '{classified_ind}' (conf: {confidence:.2f})")
            industry = classified_ind
            art_dict["industry"] = industry
            
        if dry_run:
            logger.info(f"[Dry Run] Would process article: '{title[:50]}' | Industry: {industry} | URL: {url}")
            inserted_count += 1
            continue
            
        try:
            # Skip if URL already exists in DB (Deduplication)
            existing = db.query(Article).filter(Article.url == url).first()
            if existing:
                duplicate_count += 1
                logger.debug(f"Skipping duplicate article: '{title[:30]}' ({url})")
                continue
                
            # Insert Article
            db_article = Article(
                title=title,
                content=content,
                summary=art_dict.get("summary") or (content[:400] + "..." if content else ""),
                source=art_dict.get("source") or "Unknown",
                author=art_dict.get("author") or "Unknown",
                url=url,
                industry=industry,
                published_date=art_dict.get("published_date")
            )
            db.add(db_article)
            db.commit()
            db.refresh(db_article)
            inserted_count += 1
            
            # Analyze Sentiment (Phase 3)
            try:
                analyze_sentiment(db_article, db)
            except Exception as e:
                logger.error(f"Failed to analyze sentiment for article {db_article.id}: {e}")
                
            # Extract Keywords (Phase 3)
            try:
                extract_keywords(db_article, db)
            except Exception as e:
                logger.error(f"Failed to extract keywords for article {db_article.id}: {e}")
                
            # Embed and Store (Phase 5)
            try:
                embed_and_store(db_article, db)
            except Exception as e:
                logger.error(f"Failed to embed and store article {db_article.id}: {e}")
                
            # Competitor Mention Detection (Phase 7)
            try:
                mentions = cleaner.detect_mentions(content, WATCHLIST)
                if mentions:
                    for mention in mentions:
                        db_mention = CompetitorMention(
                            article_id=db_article.id,
                            company_name=mention["company_name"],
                            mention_count=mention["mention_count"],
                            context_snippet=mention["context_snippet"]
                        )
                        db.add(db_mention)
                    db.commit()
                    logger.debug(f"[Mentions] Found {len(mentions)} mentions in article: '{title[:30]}'")
            except Exception as e:
                logger.error(f"Failed to process competitor mentions for article {db_article.id}: {e}")
                
        except Exception as e:
            logger.error(f"Failed to insert article '{title[:30]}': {e}")
            error_count += 1
            if db:
                db.rollback()
                
    if db:
        db.close()
        
    logger.info(f"Pipeline complete. Processed {inserted_count} new, skipped {duplicate_count} duplicates, {error_count} errors. Total articles input: {len(processed_articles)}")
    
    # 4. Weekly Topic Modeling Batch Job Integration (Phase 4)
    if run_topics_flag:
        logger.info("Running weekly topic modeling batch job...")
        run_topic_modeling()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scout Ingestion Pipeline Runner")
    parser.add_argument("--dry-run", action="store_true", help="Run the pipeline without database writes")
    parser.add_argument("--run-topics", action="store_true", help="Run the topic modeling algorithm after the main pipeline")
    
    args = parser.parse_args()
    run_pipeline(dry_run=args.dry_run, run_topics_flag=args.run_topics)
