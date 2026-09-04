import logging
from typing import List
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sqlalchemy.orm import Session
from database.models.article import Article
from database.models.analytics import SentimentScore

logger = logging.getLogger(__name__)

# Lazy singleton model and tokenizer references
_tokenizer = None
_model = None

def get_finbert():
    """Lazy-loads and returns the FinBERT tokenizer and model on CPU."""
    global _tokenizer, _model
    if _model is None:
        logger.info("[FinBERT] Loading ProsusAI/finbert model and tokenizer...")
        _tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
        _model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
        # Run on CPU explicitly
        _model.to("cpu")
        _model.eval()
        logger.info("[FinBERT] Model loaded successfully on CPU.")
    return _tokenizer, _model

def analyze_sentiment(article: Article, db: Session) -> SentimentScore:
    """Performs sentiment analysis on a single article and saves results to the DB."""
    try:
        # Check if score already exists
        existing = db.query(SentimentScore).filter(SentimentScore.article_id == article.id).first()
        if existing:
            return existing
            
        tokenizer, model = get_finbert()
        text = article.content or article.title or ""
        
        # Tokenize and truncate to 512 tokens
        tokens = tokenizer(
            text, 
            truncation=True, 
            max_length=512, 
            return_tensors="pt"
        )
        
        # Perform inference on CPU
        with torch.no_grad():
            outputs = model(**tokens)
            probs = F.softmax(outputs.logits, dim=-1)
            val, idx = torch.max(probs, dim=-1)
            
            # Label mapping: 0 -> positive, 1 -> negative, 2 -> neutral
            labels = ["positive", "negative", "neutral"]
            sentiment = labels[idx.item()]
            score = val.item()
            
        db_score = SentimentScore(
            article_id=article.id,
            sentiment=sentiment,
            score=score
        )
        db.add(db_score)
        db.commit()
        logger.debug(f"[FinBERT] Sentiment for '{article.title[:30]}...': {sentiment} ({score:.2f})")
        return db_score
    except Exception as e:
        logger.error(f"[FinBERT] Error analyzing sentiment for article {article.id}: {e}")
        db.rollback()
        raise e

def analyze_batch(articles: List[Article], db: Session) -> List[SentimentScore]:
    """Processes a batch of articles in chunks of 16 to avoid OOM errors."""
    if not articles:
        return []
        
    tokenizer, model = get_finbert()
    chunk_size = 16
    
    # Pre-filter articles that already have sentiment scores in a batch query
    art_ids = [art.id for art in articles]
    existing_art_ids = {s.article_id for s in db.query(SentimentScore.article_id).filter(SentimentScore.article_id.in_(art_ids)).all()}
    to_process = [art for art in articles if art.id not in existing_art_ids]
            
    if not to_process:
        logger.info("[FinBERT] All articles in batch already have sentiment scores. Skipping.")
        return []
        
    logger.info(f"[FinBERT] Processing sentiment for {len(to_process)} articles in chunks of {chunk_size}...")
    db_scores = []
    
    for i in range(0, len(to_process), chunk_size):
        chunk = to_process[i:i+chunk_size]
        texts = [art.content or art.title or "" for art in chunk]
        
        try:
            # Tokenize batch with padding and truncation
            tokens = tokenizer(
                texts,
                truncation=True,
                max_length=512,
                padding=True,
                return_tensors="pt"
            )
            
            with torch.no_grad():
                outputs = model(**tokens)
                probs = F.softmax(outputs.logits, dim=-1)
                
                for idx, art in enumerate(chunk):
                    prob_vals = probs[idx]
                    max_val, max_idx = torch.max(prob_vals, dim=-1)
                    
                    labels = ["positive", "negative", "neutral"]
                    sentiment = labels[max_idx.item()]
                    score = max_val.item()
                    
                    db_score = SentimentScore(
                        article_id=art.id,
                        sentiment=sentiment,
                        score=score
                    )
                    db.add(db_score)
                    db_scores.append(db_score)
                    
            db.commit()
            
            # Log progress every 50 articles
            processed_so_far = min(i + chunk_size, len(to_process))
            if processed_so_far % 48 == 0 or processed_so_far == len(to_process):
                logger.info(f"[FinBERT] Processed {processed_so_far}/{len(to_process)} articles.")
                
        except Exception as e:
            logger.error(f"[FinBERT] Error processing batch starting at index {i}: {e}")
            db.rollback()
            
    return db_scores
