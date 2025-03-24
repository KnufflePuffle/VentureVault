from peewee import *
from datetime import datetime

# Database setup for campaigns and characters
db = SqliteDatabase('lfg_database.db')

class BaseModel(Model):
    class Meta:
        database = db

class Campaign(BaseModel):
    name = CharField()
    dm = CharField()
    game_system = CharField(default='Pathfinder 2e')
    max_players = IntegerField()
    current_players = IntegerField(default=0)
    description = TextField()
    datetime = DateTimeField(default=datetime.now)

class Character(BaseModel):
    campaign = ForeignKeyField(Campaign, backref='characters')
    player_id = CharField()  # Discord user ID
    character_name = CharField()
    character_class = CharField()
    character_level = IntegerField()
