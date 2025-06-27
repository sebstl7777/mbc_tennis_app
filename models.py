from sqlalchemy import Column, Integer, String, Float, JSON
from database import Base

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    rating = Column(Float, default=1000.0)

class TableData(Base):
    __tablename__ = "tables"
    id = Column(Integer, primary_key=True, index=True)
    data = Column(JSON)

