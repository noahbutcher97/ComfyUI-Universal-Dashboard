"""
Database engine and session management for AI Universal Suite.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.services.database.models import Base
from src.utils.logger import log

# Default database path
DEFAULT_DB_PATH = Path(os.getenv("AI_SUITE_DB_PATH", Path(__file__).parent.parent.parent.parent / "data" / "models.db"))

class DatabaseManager:
    """
    Manages the SQLAlchemy engine and sessions.
    """
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def init_db(self):
        """
        Initialize database and run migrations.
        """
        try:
            # 1. Ensure tables are created (Legacy fallback)
            Base.metadata.create_all(bind=self.engine)
            
            # 2. Run Alembic migrations
            from alembic.config import Config
            from alembic import command
            
            # Find alembic.ini relative to this file
            base_dir = Path(__file__).parent.parent.parent.parent
            ini_path = base_dir / "alembic.ini"
            
            if ini_path.exists():
                log.info("Running database migrations...")
                alembic_cfg = Config(str(ini_path))
                # Ensure it uses the correct DB path
                alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{self.db_path}")
                command.upgrade(alembic_cfg, "head")
            else:
                log.warning(f"alembic.ini not found at {ini_path}, skipping migrations.")

            log.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            log.error(f"Failed to initialize database: {e}")
            raise

    def get_session(self) -> Session:
        """
        Get a new database session.
        """
        return self.SessionLocal()

# Singleton instance
db_manager = DatabaseManager()

def get_db():
    """
    Dependency helper for getting a session.
    """
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()
