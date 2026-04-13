"""
Database Connection Manager for SQLAlchemy / SQLite.
Handles session management, creation of tables, and common DB operations.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base
from config import DB_PATH
from utils.logger import get_logger

logger = get_logger("DB_Manager")

class DatabaseManager:
    _instance = None

    def __new__(cls):
        """Singleton pattern so we share connection pools natively"""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        """Initialize the SQLAlchemy engine and create tables if they don't exist"""
        db_url = f"sqlite:///{DB_PATH}"
        # Setting check_same_thread=False is required for SQLite across multiple threads/agents
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        
        try:
            logger.info(f"Connecting to database at {db_url}")
            Base.metadata.create_all(self.engine)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.fatal(f"Database initialization failed: {e}")
            raise

    def get_session(self) -> Session:
        """
        Get a new database session.
        Make sure to close it or use Context Manager:
            with db_manager.get_session() as session:
                ...
        """
        return self.SessionLocal()

# Global export 
db = DatabaseManager()
