"""
Database models for the RFID Audio Player application.

This module defines the database schema and provides connection setup.
"""

import os
import logging
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import sessionmaker, declarative_base

# Configure logging
logging.basicConfig(
    filename='/home/pi/rfid_audio.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('models')

# Database configuration
Base = declarative_base()

# Get database path from environment or use default
DB_PATH = os.environ.get('RFID_AUDIO_DB_PATH', 'rfid_audio.db')
DATABASE_URL = f"sqlite:///{DB_PATH}"

logger.info(f"Using database at {DB_PATH}")

class RFIDAudio(Base):
    """
    Database model for mapping RFID IDs to audio files.
    
    Attributes:
        id (str): The RFID tag ID as a string (primary key)
        file (str): The filename of the associated audio file
    """
    __tablename__ = "rfid_audio"
    id = Column(String, primary_key=True)
    file = Column(String, nullable=False)

# Create database engine with proper configuration
engine = create_engine(DATABASE_URL, echo=False, 
                      connect_args={"check_same_thread": False},  # Allow access from multiple threads
                      pool_pre_ping=True)  # Check connection before using it
Session = sessionmaker(bind=engine)

# Create tables if they don't exist
def init_db():
    """Initialize the database by creating all defined tables."""
    try:
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise
        
def get_session():
    """
    Create and return a new database session.
    
    Returns:
        Session: A new database session
    """
    return Session()