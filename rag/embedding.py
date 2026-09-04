import logging
import uuid
from sqlalchemy.orm import Session
from database.models.article import Article
from database.models.embeddings import EmbeddingsMetadata
from database.connection import SessionLocal

logger = logging.getLogger(__name__)

def embed_and_store(article: Article, db: Session = None) -> EmbeddingsMetadata:
    """Mock implementation of embedding and storing in Qdrant."""
    db_created = False
    if db is None:
        db = SessionLocal()
        db_created = True
        
    try:
        # Check if already embedded
        existing = db.query(EmbeddingsMetadata).filter(EmbeddingsMetadata.article_id == article.id).first()
        if existing:
            return existing
            
        vector_id = str(uuid.uuid4())
        
        metadata = EmbeddingsMetadata(
            article_id=article.id,
            vector_id=vector_id
        )
        db.add(metadata)
        db.commit()
        logger.debug(f"[Embedding Mock] Generated mock vector ID {vector_id} for article: {article.title[:30]}...")
        return metadata
    except Exception as e:
        logger.error(f"[Embedding Mock] Error creating embedding metadata for article {article.id}: {e}")
        db.rollback()
        raise e
    finally:
        if db_created:
            db.close()

def embed_batch(articles: list, db: Session = None):
    """Batch embedding generating mock metadata and storing in DB with single commit."""
    if not articles:
        return
        
    db_created = False
    if db is None:
        db = SessionLocal()
        db_created = True
        
    try:
        art_ids = [art.id for art in articles]
        existing_embeddings = db.query(EmbeddingsMetadata).filter(EmbeddingsMetadata.article_id.in_(art_ids)).all()
        existing_art_ids = {e.article_id for e in existing_embeddings}
        
        to_process = [art for art in articles if art.id not in existing_art_ids]
        if not to_process:
            return
            
        for art in to_process:
            vector_id = str(uuid.uuid4())
            metadata = EmbeddingsMetadata(
                article_id=art.id,
                vector_id=vector_id
            )
            db.add(metadata)
            
        db.commit()
        logger.info(f"[Embedding Mock] Batch generated mock vectors for {len(to_process)} articles.")
    except Exception as e:
        logger.error(f"[Embedding Mock] Error batch embedding: {e}")
        db.rollback()
        raise e
    finally:
        if db_created:
            db.close()
