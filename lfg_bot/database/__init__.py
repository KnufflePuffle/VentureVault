from peewee import *
import os

# Get the directory where the database file should be located
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(base_dir, 'campaigns_plotpoints.db')

# Create database connection
db = SqliteDatabase(db_path)

class BaseModel(Model):
    class Meta:
        database = db


# Import models to make them available
from .models import Campaign, PlotPoint

def init_db():
    """Initialize the database by creating all tables"""
    db.connect()
    db.create_tables([Campaign, PlotPoint])
    print("Database initialized successfully")
    db.close()