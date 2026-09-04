import pytest
from unittest.mock import MagicMock, patch
import torch
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.connection import Base
from database.models.article import Article
from database.models.competitor import CompetitorMention
from database.models.analytics import SentimentScore, Keyword
from database.models.embeddings import EmbeddingsMetadata

# Imports to test
from analytics.sentiment.finbert import analyze_batch
from analytics.keyword_extraction.keybert_extractor import extract_keywords_batch
from rag.embedding import embed_batch
from backend.services.analytics_service import get_competitor_summaries

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    SessionClass = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionClass()
    
    # Add seed data
    art1 = Article(
        title="Tesla delivers record EV cargo fleet",
        content="Tesla is expanding its global shipping logistics. Tesla autonomous trucking cargo lanes are active.",
        url="https://tesla.com/news1",
        industry="logistics",
        published_date=datetime.utcnow()
    )
    art2 = Article(
        title="Samsung semiconductor growth",
        content="Samsung announces major chip technology breakthroughs in collaboration with competitors.",
        url="https://samsung.com/news2",
        industry="general",
        published_date=datetime.utcnow()
    )
    db.add_all([art1, art2])
    db.commit()
    db.refresh(art1)
    db.refresh(art2)
    
    yield db
    db.close()

def test_analyze_batch_sentiment(db_session):
    # Mock FinBERT
    mock_tokenizer = MagicMock()
    mock_model = MagicMock()
    
    # Mock model outputs logits for positive (index 0) and neutral (index 2)
    # shape is (2, 3)
    mock_outputs = MagicMock()
    mock_outputs.logits = torch.tensor([
        [2.0, -1.0, 0.0],  # Positive
        [-1.0, -2.0, 3.0]   # Neutral
    ])
    mock_model.return_value = mock_outputs
    
    articles = db_session.query(Article).all()
    
    with patch("analytics.sentiment.finbert.get_finbert", return_value=(mock_tokenizer, mock_model)):
        scores = analyze_batch(articles, db_session)
        assert len(scores) == 2
        
        # Verify db entries
        db_scores = db_session.query(SentimentScore).all()
        assert len(db_scores) == 2
        
        sentiments = {s.article_id: s.sentiment for s in db_scores}
        assert sentiments[articles[0].id] == "positive"
        assert sentiments[articles[1].id] == "neutral"

def test_extract_keywords_batch(db_session):
    mock_kw_model = MagicMock()
    # Mock KeyBERT extract_keywords returns a list of lists of tuples
    mock_kw_model.extract_keywords.return_value = [
        [("cargo", 0.9), ("logistics", 0.85)],
        [("growth", 0.95), ("breakthrough", 0.88)]
    ]
    
    articles = db_session.query(Article).all()
    
    with patch("analytics.keyword_extraction.keybert_extractor.get_keybert", return_value=mock_kw_model):
        kws = extract_keywords_batch(articles, db_session)
        assert len(kws) == 4
        
        # Verify db entries
        db_kws = db_session.query(Keyword).all()
        assert len(db_kws) == 4
        
        keywords_by_art = {}
        for k in db_kws:
            if k.article_id not in keywords_by_art:
                keywords_by_art[k.article_id] = []
            keywords_by_art[k.article_id].append(k.keyword)
            
        assert "cargo" in keywords_by_art[articles[0].id]
        assert "growth" in keywords_by_art[articles[1].id]

def test_embed_batch(db_session):
    articles = db_session.query(Article).all()
    embed_batch(articles, db_session)
    
    db_embeds = db_session.query(EmbeddingsMetadata).all()
    assert len(db_embeds) == 2
    assert db_embeds[0].article_id == articles[0].id
    assert db_embeds[1].article_id == articles[1].id

def test_get_competitor_summaries_optimized(db_session):
    articles = db_session.query(Article).all()
    
    # Setup mentions
    m1 = CompetitorMention(
        article_id=articles[0].id,
        company_name="Tesla",
        mention_count=3,
        context_snippet="Tesla autonomous trucking cargo lanes"
    )
    m2 = CompetitorMention(
        article_id=articles[1].id,
        company_name="Samsung",
        mention_count=2,
        context_snippet="Samsung announces major chip technology breakthroughs"
    )
    
    # Setup sentiment scores
    s1 = SentimentScore(
        article_id=articles[0].id,
        sentiment="positive",
        score=0.9
    )
    s2 = SentimentScore(
        article_id=articles[1].id,
        sentiment="neutral",
        score=0.8
    )
    
    db_session.add_all([m1, m2, s1, s2])
    db_session.commit()
    
    # Test aggregation service
    summaries = get_competitor_summaries(db_session)
    assert len(summaries) == 2
    
    tesla_summary = next(s for s in summaries if s["company_name"] == "Tesla")
    assert tesla_summary["total_mentions"] == 3
    assert tesla_summary["industry_breakdown"]["logistics"] == 3
    assert tesla_summary["sentiment_breakdown"]["positive"] == 3
    
    samsung_summary = next(s for s in summaries if s["company_name"] == "Samsung")
    assert samsung_summary["total_mentions"] == 2
    assert samsung_summary["industry_breakdown"]["general"] == 2
    assert samsung_summary["sentiment_breakdown"]["neutral"] == 2
