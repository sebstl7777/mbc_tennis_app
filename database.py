from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.environ["postgresql://postgres:%40tlaSt.Louis7@db.jfkdvjuishdjdqmnuqay.supabase.co:5432/postgres"]

engine = create_engine(
    DATABASE_URL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

