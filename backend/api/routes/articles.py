from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models.article import Article
from backend.schemas.article import ArticleOut

router = APIRouter(prefix="/articles", tags=["articles"])

@router.get("/", response_model=List[ArticleOut])
async def get_articles(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    industry: Optional[str] = None,
    topic: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Article)
    if industry:
        query = query.filter(Article.industry == industry)
    if topic:
        query = query.filter(Article.topic_name == topic)
    if search:
        # ilike is case-insensitive search
        query = query.filter(
            (Article.title.ilike(f"%{search}%")) | (Article.content.ilike(f"%{search}%"))
        )
    articles = query.order_by(Article.published_date.desc()).offset(skip).limit(limit).all()
    return articles



@router.get("/fetch-internet")
async def fetch_internet_articles(q: str):
    """Fetches articles for a custom product query from Google News RSS feed,
    performs real-time brand detection and lexical sentiment analysis, and aggregates stats.
    """
    import feedparser
    import requests
    import re
    
    if not q:
        return {"articles": [], "stats": {}}
        
    query_encoded = requests.utils.quote(q)
    feed_url = f"https://news.google.com/rss/search?q={query_encoded}&hl=en-US&gl=US&ceid=US:en"
    
    # Common brands for matching
    BRANDS = [
        "Apple", "Samsung", "Google", "Microsoft", "Dell", "HP", "Lenovo", "Asus", 
        "Acer", "Huawei", "Xiaomi", "Sony", "LG", "Tesla", "BYD", "Nvidia", "Intel", 
        "AMD", "Amazon", "Meta", "Toyota", "Ford", "GM", "Reliance"
    ]
    
    # Lexical lists
    POSITIVE_WORDS = {
        "innovative", "innovation", "growth", "breakthrough", "record", "profit", 
        "surpasses", "succeed", "popular", "advanced", "leadership", "excellent", 
        "rise", "gains", "partnership", "collaboration", "upgrade", "success", "boost", 
        "revenue", "demand", "unveiled", "unveils", "strong", "best", "leading"
    }
    NEGATIVE_WORDS = {
        "decline", "layoff", "layoffs", "drop", "deficit", "regulatory", "lawsuit", 
        "delay", "crash", "recall", "fail", "plunge", "loss", "warning", "decrease", 
        "lawsuits", "investigation", "fined", "dip", "falls", "slump", "cuts", "debt"
    }
    
    articles = []
    stats = {}
    
    try:
        # Fetch RSS
        response = requests.get(feed_url, timeout=8)
        feed = feedparser.parse(response.content)
        
        for entry in feed.entries[:40]: # limit to 40 articles
            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            url = entry.get("link", "")
            source = entry.get("source", {}).get("name", "Google News")
            pub_date = entry.get("published", "")
            
            # 1. Clean HTML from summary
            clean_summary = re.sub(r'<[^>]*>', '', summary)
            
            # 2. Match brands
            matched_brands = []
            text_to_scan = f"{title} {clean_summary}".lower()
            for brand in BRANDS:
                if re.search(r'\b' + re.escape(brand.lower()) + r'\b', text_to_scan):
                    matched_brands.append(brand)
                    
            # 3. Sentiment analysis (lexical)
            words = re.findall(r'\b\w+\b', text_to_scan)
            pos_score = sum(1 for w in words if w in POSITIVE_WORDS)
            neg_score = sum(1 for w in words if w in NEGATIVE_WORDS)
            
            if pos_score > neg_score:
                sentiment = "positive"
            elif neg_score > pos_score:
                sentiment = "negative"
            else:
                sentiment = "neutral"
                
            if not matched_brands:
                matched_brands = ["General"]
                
            articles.append({
                "title": title,
                "summary": clean_summary[:400] + "..." if len(clean_summary) > 400 else clean_summary,
                "url": url,
                "source": source,
                "published_date": pub_date,
                "sentiment": sentiment,
                "brands": matched_brands
            })
            
            # 4. Aggregated stats
            for brand in matched_brands:
                if brand == "General":
                    continue
                if brand not in stats:
                    stats[brand] = {
                        "mentions": 0,
                        "positive": 0,
                        "negative": 0,
                        "neutral": 0
                    }
                stats[brand]["mentions"] += 1
                stats[brand][sentiment] += 1
                
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to fetch live RSS feeds for {q}: {e}")
        return {"articles": [], "stats": {}, "error": str(e)}
        
    return {
        "articles": articles,
        "stats": stats
    }

@router.post("/ingest-keyword")
async def ingest_keyword(q: str, db: Session = Depends(get_db)):
    """Fetches articles from Google News search feed matching q,
    cleans them, normalizes them, and runs the full pipeline in batch
    (FinBERT, KeyBERT, Qdrant, Competitors) with concurrent scraping.
    """
    import feedparser
    import requests
    import re
    import trafilatura
    import logging
    import concurrent.futures
    from database.models.competitor import CompetitorMention
    from database.models.analytics import SentimentScore, Keyword
    from database.models.embeddings import EmbeddingsMetadata
    from data_pipeline.processors import cleaner, classifier
    from analytics.sentiment.finbert import analyze_batch
    from analytics.keyword_extraction.keybert_extractor import extract_keywords_batch
    from rag.embedding import embed_batch
    from data_pipeline.scheduler.pipeline_runner import WATCHLIST
    
    logger = logging.getLogger(__name__)
    
    if not q:
        raise HTTPException(status_code=400, detail="Search query parameter 'q' is required")
        
    query_encoded = requests.utils.quote(q)
    feed_url = f"https://news.google.com/rss/search?q={query_encoded}&hl=en-US&gl=US&ceid=US:en"
    
    articles_fetched = 0
    new_ingested = 0
    duplicates_skipped = 0
    errors = 0
    
    ingested_details = []
    
    try:
        response = requests.get(feed_url, timeout=10)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        
        entries = feed.entries[:15]
        articles_fetched = len(entries)
        
        # 1. Bulk check duplicates to avoid scraping them
        urls = [entry.get("link") for entry in entries if entry.get("link")]
        existing_urls = {a.url for a in db.query(Article.url).filter(Article.url.in_(urls)).all()}
        duplicates_skipped = sum(1 for url in urls if url in existing_urls)
        
        entries_to_fetch = [entry for entry in entries if entry.get("link") and entry.get("link") not in existing_urls]
        
        # Thread function to download/extract content concurrently
        def fetch_content(entry):
            url = entry.get("link")
            summary = entry.get("summary") or entry.get("description") or ""
            clean_summary = cleaner.clean_text(summary)
            clean_summary = cleaner.strip_boilerplate(clean_summary)
            content = clean_summary
            try:
                downloaded = trafilatura.fetch_url(url)
                if downloaded:
                    extracted = trafilatura.extract(downloaded)
                    if extracted:
                        content = cleaner.clean_text(extracted)
                        content = cleaner.strip_boilerplate(content)
                        content = cleaner.truncate(content)
            except Exception as te:
                logger.warning(f"Trafilatura failed for {url}: {te}")
            return entry, content, clean_summary

        # 2. Parallel scraping of non-duplicate articles
        fetched_results = []
        if entries_to_fetch:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(fetch_content, entry): entry for entry in entries_to_fetch}
                for future in concurrent.futures.as_completed(futures):
                    try:
                        entry, content, clean_summary = future.result()
                        fetched_results.append((entry, content, clean_summary))
                    except Exception as fe:
                        logger.error(f"Thread pool task failed: {fe}")
                        errors += 1
        
        # 3. Bulk Insert Articles
        db_articles = []
        for entry, content, clean_summary in fetched_results:
            title = entry.get("title", "")
            url = entry.get("link", "")
            source = entry.get("source", {}).get("name") if entry.get("source") else "Google News"
            pub_date_str = entry.get("published", "")
            published_date = cleaner.normalize_date(pub_date_str)
            industry, confidence = classifier.classify_industry(content or title)
            
            try:
                db_article = Article(
                    title=title,
                    content=content,
                    summary=clean_summary[:400] + "..." if len(clean_summary) > 400 else clean_summary,
                    source=source,
                    author="Google News RSS Scraper",
                    url=url,
                    industry=industry,
                    published_date=published_date
                )
                db.add(db_article)
                db_articles.append(db_article)
            except Exception as e:
                logger.error(f"Failed to create article object: {e}")
                errors += 1
                
        if db_articles:
            try:
                db.commit()
                for art in db_articles:
                    db.refresh(art)
                new_ingested = len(db_articles)
            except Exception as e:
                logger.error(f"Failed to commit batch articles: {e}")
                db.rollback()
                errors += len(db_articles)
                db_articles = []
                
        # 4. Batch ML Operations
        if db_articles:
            sentiment_map = {}
            kw_map = {}
            
            try:
                sentiment_scores = analyze_batch(db_articles, db)
                sentiment_map = {s.article_id: s.sentiment for s in sentiment_scores}
            except Exception as e:
                logger.error(f"Failed to batch analyze sentiment: {e}")
                
            try:
                keywords = extract_keywords_batch(db_articles, db)
                for kw in keywords:
                    if kw.article_id not in kw_map:
                        kw_map[kw.article_id] = []
                    kw_map[kw.article_id].append(kw.keyword)
            except Exception as e:
                logger.error(f"Failed to batch extract keywords: {e}")
                
            try:
                embed_batch(db_articles, db)
            except Exception as e:
                logger.error(f"Failed to batch embed articles: {e}")
                
            # 5. Competitor Mentions Bulk Insertion
            db_mentions = []
            for art in db_articles:
                mentions = cleaner.detect_mentions(art.content, WATCHLIST)
                if mentions:
                    for mention in mentions:
                        db_mention = CompetitorMention(
                            article_id=art.id,
                            company_name=mention["company_name"],
                            mention_count=mention["mention_count"],
                            context_snippet=mention["context_snippet"]
                        )
                        db.add(db_mention)
                        db_mentions.append(db_mention)
            if db_mentions:
                try:
                    db.commit()
                except Exception as e:
                    logger.error(f"Failed to commit competitor mentions: {e}")
                    db.rollback()
                    
            # 6. Format Response Details
            for art in db_articles:
                ingested_details.append({
                    "id": str(art.id),
                    "title": art.title,
                    "url": art.url,
                    "source": art.source,
                    "industry": art.industry,
                    "sentiment": sentiment_map.get(art.id, "neutral"),
                    "keywords": kw_map.get(art.id, [])[:5]
                })
                
    except Exception as e:
        logger.error(f"Error fetching Google News feed for query '{q}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch Google News feed: {str(e)}")
        
    return {
        "status": "success",
        "stats": {
            "total_fetched": articles_fetched,
            "new_ingested": new_ingested,
            "duplicates_skipped": duplicates_skipped,
            "errors": errors
        },
        "articles": ingested_details
    }


@router.get("/{article_id}", response_model=ArticleOut)
async def get_article(article_id: UUID, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

