from datetime import datetime, timedelta
import logging
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from database.models.article import Article
from database.models.analytics import SentimentScore, Keyword, Topic

logger = logging.getLogger(__name__)

def sentiment_summary(db: Session, industry: str = None) -> list:
    """Calculates sentiment distribution count and percentage for all or filtered articles."""
    query = db.query(
        SentimentScore.sentiment,
        func.count(SentimentScore.id).label("count")
    ).join(Article, Article.id == SentimentScore.article_id)
    
    if industry:
        query = query.filter(Article.industry == industry)
        
    results = query.group_by(SentimentScore.sentiment).all()
    total_count = sum(r.count for r in results)
    
    summary = []
    for r in results:
        summary.append({
            "sentiment": r.sentiment,
            "count": r.count,
            "percentage": round((r.count / total_count) * 100, 2) if total_count > 0 else 0.0
        })
        
    return summary

def top_topics(db: Session, limit: int = 10) -> list:
    """Returns top topics ordered by frequency."""
    topics = db.query(Topic).order_by(Topic.frequency.desc()).limit(limit).all()
    return [
        {
            "topic_name": t.topic_name,
            "frequency": t.frequency,
            "date": t.created_at
        } for t in topics
    ]

def trending_keywords(db: Session, days: int = 7) -> list:
    """Returns top 20 keywords based on average importance score over last N days."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    results = db.query(
        Keyword.keyword,
        func.avg(Keyword.score).label("avg_score")
    ).join(Article, Article.id == Keyword.article_id).filter(
        Article.published_date >= cutoff_date
    ).group_by(
        Keyword.keyword
    ).order_by(
        func.avg(Keyword.score).desc()
    ).limit(20).all()
    
    return [
        {
            "keyword": r.keyword,
            "score": round(r.avg_score, 2)
        } for r in results
    ]

def sentiment_over_time(db: Session, days: int = 30) -> list:
    """Calculates daily counts of positive, negative, and neutral sentiments.
    
    Handles SQLite and PostgreSQL dialects automatically.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    is_sqlite = db.bind.dialect.name == "sqlite"
    
    # Dialect-agnostic grouping field
    if is_sqlite:
        date_field = func.strftime("%Y-%m-%d", Article.published_date)
    else:
        # PostgreSQL DATE_TRUNC truncates to day, but we cast to DATE to match YYYY-MM-DD
        date_field = func.cast(func.date_trunc("day", Article.published_date), func.DATE)
        
    results = db.query(
        date_field.label("date_group"),
        func.sum(case((SentimentScore.sentiment == "positive", 1), else_=0)).label("positive"),
        func.sum(case((SentimentScore.sentiment == "negative", 1), else_=0)).label("negative"),
        func.sum(case((SentimentScore.sentiment == "neutral", 1), else_=0)).label("neutral")
    ).join(
        SentimentScore, Article.id == SentimentScore.article_id
    ).filter(
        Article.published_date >= cutoff_date
    ).group_by(
        "date_group"
    ).order_by(
        "date_group"
    ).all()
    
    over_time_list = []
    for r in results:
        # format date group back to string for frontend consumption
        date_str = str(r.date_group)
        over_time_list.append({
            "date": date_str,
            "positive": int(r.positive or 0),
            "negative": int(r.negative or 0),
            "neutral": int(r.neutral or 0)
        })
        
    return over_time_list

def topic_velocity(db: Session, days: int = 7) -> list:
    """Calculates and returns topic velocity over the last N days."""
    from analytics.trends.trend_detector import get_topic_velocity
    return get_topic_velocity(db, days=days)

def get_competitor_summaries(db: Session) -> list:
    """Calculates overall competitor mention statistics and sentiment/industry breakdown."""
    from database.models.competitor import CompetitorMention
    
    # 1. Get total mentions per competitor
    results = db.query(
        CompetitorMention.company_name,
        func.sum(CompetitorMention.mention_count).label("total_mentions")
    ).group_by(CompetitorMention.company_name).all()
    
    # 2. Get industry breakdowns for all competitors in a single grouped query
    ind_results = db.query(
        CompetitorMention.company_name,
        Article.industry,
        func.sum(CompetitorMention.mention_count).label("count")
    ).join(Article, Article.id == CompetitorMention.article_id)\
     .group_by(CompetitorMention.company_name, Article.industry).all()
     
    # 3. Get sentiment breakdowns for all competitors in a single grouped query
    sent_results = db.query(
        CompetitorMention.company_name,
        SentimentScore.sentiment,
        func.sum(CompetitorMention.mention_count).label("count")
    ).join(SentimentScore, SentimentScore.article_id == CompetitorMention.article_id)\
     .group_by(CompetitorMention.company_name, SentimentScore.sentiment).all()
     
    # Map industry results in memory: {company_name: {industry: count}}
    industry_maps = {}
    for row in ind_results:
        if row.company_name not in industry_maps:
            industry_maps[row.company_name] = {}
        industry_maps[row.company_name][row.industry] = int(row.count or 0)
        
    # Map sentiment results in memory: {company_name: {sentiment: count}}
    sentiment_maps = {}
    for row in sent_results:
        if row.company_name not in sentiment_maps:
            sentiment_maps[row.company_name] = {}
        sentiment_maps[row.company_name][row.sentiment] = int(row.count or 0)
        
    summaries = []
    for r in results:
        company_name = r.company_name
        summaries.append({
            "company_name": company_name,
            "total_mentions": int(r.total_mentions or 0),
            "industry_breakdown": industry_maps.get(company_name, {}),
            "sentiment_breakdown": sentiment_maps.get(company_name, {})
        })
        
    # Sort by total mentions descending
    summaries = sorted(summaries, key=lambda x: x["total_mentions"], reverse=True)
    return summaries

def get_competitor_mentions(db: Session, company_name: str) -> list:
    """Fetches details of all article mentions for a specific competitor."""
    from database.models.competitor import CompetitorMention
    
    results = db.query(
        Article.title.label("article_title"),
        Article.url.label("article_url"),
        SentimentScore.sentiment.label("sentiment"),
        CompetitorMention.mention_count,
        CompetitorMention.context_snippet,
        Article.published_date
    ).join(Article, Article.id == CompetitorMention.article_id)\
     .outerjoin(SentimentScore, SentimentScore.article_id == CompetitorMention.article_id)\
     .filter(CompetitorMention.company_name == company_name)\
     .order_by(Article.published_date.desc()).all()
     
    mentions = []
    for r in results:
        mentions.append({
            "article_title": r.article_title,
            "article_url": r.article_url,
            "sentiment": r.sentiment or "neutral",
            "mention_count": int(r.mention_count or 1),
            "context_snippet": r.context_snippet or "",
            "published_date": r.published_date
        })
    return mentions
