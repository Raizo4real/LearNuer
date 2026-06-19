from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Define the SQLite connection string
# This creates a file named "learneur.db" in the same directory
SQLALCHEMY_DATABASE_URL = "sqlite:///./learneur.db"

# 2. Create the SQLAlchemy engine
# connect_args={"check_same_thread": False} is required ONLY for SQLite in FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. Create a SessionLocal class
# Each instance of this class will be a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Create a Base class
# All our ORM models (in models.py) will inherit from this Base
Base = declarative_base()

# 5. Dependency injection function
# This yields a database session for a single request and closes it safely afterward
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()