import discord
from discord.ext import commands
from peewee import *
from datetime import datetime
import re
import logging

# Configure logging
logger = logging.getLogger('plot_points')

# Database setup
db = SqliteDatabase('campaigns_plotpoints.db')


class BaseModel(Model):
    class Meta:
        database = db


class Campaign(BaseModel):
    name = CharField()
    plot_category_id = CharField(null=True)


class PlotPoint(BaseModel):
    campaign = ForeignKeyField(Campaign, backref='plot_points')
    number = CharField()
    title = CharField()
    description = TextField()
    status = CharField(default='Inactive')
    potential_players = TextField(null=True)
    channel_id = CharField(null=True)


class PlotPointCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        db.connect()
        db.create_tables([Campaign, PlotPoint])
        logger.info("PlotPointCog initialized")

    def cog_unload(self):
        db.close()

    @commands.command(name='add_plot_point')
    async def add_plot_point(self, ctx, number: str, title: str, *, description: str):
        """Add a new plot point"""
        logger.info(f"add_plot_point command called by {ctx.author}")
        try:
            # Find or create the campaign
            campaign = Campaign.select().order_by(Campaign.id.desc()).first()
            if not campaign:
                campaign = Campaign.create(name=f"Campaign {datetime.now().year}")

            # Validate plot point number format
            if not re.match(r'^\d+[a-z]?$', number):
                await ctx.send("Invalid plot point number. Use format like '01', '02', '03a', '03b'")
                return

            # Create plot point in database
            plot_point = PlotPoint.create(
                campaign=campaign,
                number=number,
                title=title,
                description=description,
                status='Inactive'
            )

            # Send confirmation
            await ctx.send(f"Created plot point {number}: '{title}'")

        except Exception as e:
            logger.error(f"Error in add_plot_point: {e}")
            await ctx.send(f"Error creating plot point: {str(e)}")


async def setup(bot):
    logger.info("Setting up PlotPointCog")
    await bot.add_cog(PlotPointCog(bot))