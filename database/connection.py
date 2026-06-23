import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

def clean_database_url(url: str) -> str:
    if not url:
        return url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    try:
        parsed = urlparse(url)
        if parsed.query:
            q_params = parse_qsl(parsed.query)
            filtered = [(k, v) for k, v in q_params if k.lower() != "pgbouncer"]
            parsed = parsed._replace(query=urlencode(filtered))
            url = urlunparse(parsed)
    except Exception:
        pass
    return url

DATABASE_URL = clean_database_url(os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/scout_db"))

# For sqlite compatibility during unit tests if needed
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
