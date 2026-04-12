"""
Database Configuration and Session Management

Manages PostgreSQL connections and SQLAlchemy sessions
"""

import logging
import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

load_dotenv()

logger = logging.getLogger(__name__)

# Base class for all models
Base = declarative_base()

# Database configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db'
)


class DatabaseConfig:
    """Database configuration and session management"""

    def __init__(self, database_url: str = None):
        """
        Initialize database configuration

        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url or DATABASE_URL

        # Create engine with connection pooling
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before using
            echo=False  # Set to True for SQL query logging
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        logger.info(f"Database configured: {self._safe_url()}")

    def _safe_url(self) -> str:
        """Return database URL with password masked"""
        if '@' in self.database_url:
            parts = self.database_url.split('@')
            user_parts = parts[0].split(':')
            if len(user_parts) > 2:
                return f"{user_parts[0]}:{user_parts[1]}:***@{parts[1]}"
        return "***"

    def create_tables(self):
        """Create all tables in the database"""
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("✓ Tables created successfully")

    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("✓ Tables dropped")

    def get_session(self) -> Session:
        """
        Get a new database session

        Returns:
            SQLAlchemy Session object
        """
        return self.SessionLocal()

    def get_session_context(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic cleanup (context manager)

        Usage:
            with db_config.get_session_context() as session:
                # Use session
                pass

        Yields:
            SQLAlchemy Session object
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Session error: {str(e)}")
            raise
        finally:
            session.close()

    def test_connection(self) -> bool:
        """
        Test database connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✓ Database connection successful")
            return True
        except Exception as e:
            logger.error(f"✗ Database connection failed: {str(e)}")
            return False

    def close(self):
        """Close database engine and cleanup"""
        self.engine.dispose()
        logger.info("Database engine closed")


# Global database instance
_db_config = None


def get_db_config() -> DatabaseConfig:
    """
    Get or create global database configuration instance

    Returns:
        DatabaseConfig instance
    """
    global _db_config
    if _db_config is None:
        _db_config = DatabaseConfig()
    return _db_config


def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency injection for FastAPI and other frameworks

    Usage in FastAPI:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db_session)):
            return db.query(User).all()

    Yields:
        SQLAlchemy Session
    """
    db_config = get_db_config()
    session = db_config.get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database(drop_existing: bool = False):
    """
    Initialize database (create tables)

    Args:
        drop_existing: If True, drop existing tables first
    """
    db_config = get_db_config()

    if drop_existing:
        db_config.drop_tables()

    db_config.create_tables()
    logger.info("✓ Database initialized")


# Enable pgvector extension (if needed)
def enable_pgvector():
    """Enable pgvector extension for vector embeddings"""
    db_config = get_db_config()
    try:
        with db_config.engine.connect() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.commit()
        logger.info("✓ pgvector extension enabled")
    except Exception as e:
        logger.warning(f"Could not enable pgvector: {str(e)}")
