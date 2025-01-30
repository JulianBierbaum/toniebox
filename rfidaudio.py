from sqlalchemy import create_engine, Column, String

from main import Base

class RFIDAudio(Base):
    __tablename__ = "rfid_audio"
    id = Column(String, primary_key=True)
    file = Column(String, nullable=False)