from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Get the directory where the database file should be located
# For local development
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(base_dir, 'campaigns_plotpoints.db')

# For Cybrancee deployment, you might need to adjust this path
# You might want to use an environment variable to determine where to store the DB
# Example:
# if 'CYBRANCEE' in os.environ:
#     db_path = '/path/to/cybrancee/data/campaigns_plotpoints.db'

# Create database URL
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

# Create engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Only needed for SQLite
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

def get_db():
    """Function to get a database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize the database by creating all tables"""
    from . import models
    models.Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")
