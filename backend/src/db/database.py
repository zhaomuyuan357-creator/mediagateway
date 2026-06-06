"""Database setup and session management."""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ..config import get_settings

settings = get_settings()

# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from ..models import api_provider, task, conversation, message
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_schema()


def _migrate_sqlite_schema():
    """Apply lightweight schema fixes for older local SQLite databases."""
    if "sqlite" not in settings.database_url:
        return

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    # 如果旧表存在但新表不存在，创建新表
    # (Base.metadata.create_all 已处理新表创建，这里做额外的兼容迁移)
