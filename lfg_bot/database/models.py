from peewee import *
from datetime import datetime

# Database setup for campaigns and characters
#db = SqliteDatabase('lfg_database.db')

#class BaseModel(Model):
#    class Meta:
#        database = db

#class Campaign(BaseModel):
#    name = CharField()
#    dm = CharField()
#    game_system = CharField(default='Pathfinder 2e')
#    max_players = IntegerField()
#    current_players = IntegerField(default=0)
#    description = TextField()
#    datetime = DateTimeField(default=datetime.now)

#class Character(BaseModel):
#    campaign = ForeignKeyField(Campaign, backref='characters')
#    player_id = CharField()  # Discord user ID
#    character_name = CharField()
#    character_class = CharField()
#    character_level = IntegerField()
from peewee import *
from datetime import datetime
from . import db, BaseModel


class Campaign(BaseModel):
    name = CharField()
    plot_category_id = CharField(null=True)
    created_at = DateTimeField(default=datetime.now)
    dm_id = CharField(null=True)  # Store the Discord ID of the DM

    def __str__(self):
        return f"{self.name} (ID: {self.id})"


class PlotPoint(BaseModel):
    campaign = ForeignKeyField(Campaign, backref='plot_points')
    number = CharField()
    title = CharField()
    description = TextField()
    status = CharField(default='Inactive')
    potential_players = TextField(null=True)
    channel_id = CharField(null=True)
    created_at = DateTimeField(default=datetime.now)

    def __str__(self):
        return f"{self.number}: {self.title} ({self.status})"