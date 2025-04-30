"""
Database models for the RFID Audio Player application.

This module defines the database schema and provides connection setup.
"""

from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker, declarative_base

# Database configuration
Base = declarative_base()
DATABASE_URL = "sqlite:///rfid_audio.db"


class RFIDAudio(Base):
    """
    Database model for mapping RFID IDs to audio files.

    Attributes:
        id (str): The RFID tag ID as a string (primary key)
        file (str): The filename of the associated audio file
    """

    __tablename__ = "rfid_audio"
    id = Column(Integer, primary_key=True)
    file = Column(String, nullable=False)


# Create database engine and session factory
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)


# Create tables if they don't exist
def init_db():
    """Initialize the database by creating all defined tables."""
    Base.metadata.create_all(engine)
