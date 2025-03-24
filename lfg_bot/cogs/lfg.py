import discord
from discord.ext import commands
from peewee import *
from datetime import datetime
import uuid

# Database setup
db = SqliteDatabase('campaigns.db')


class BaseModel(Model):
    class Meta:
        database = db


class Campaign(BaseModel):
    id = CharField(primary_key=True)
    name = CharField()
    dm_id = CharField()
    game_system = CharField(default='Pathfinder 2E')
    max_players = IntegerField()
    current_players = IntegerField(default=1)
    description = TextField()
    created_at = DateTimeField(default=datetime.now)
    status = CharField(default='Open')  # Open, Full, In Progress, Completed


class Character(BaseModel):
    campaign = ForeignKeyField(Campaign, backref='characters')
    player_id = CharField()
    character_name = CharField()
    character_class = CharField()
    character_level = IntegerField()


class LFGCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        db.connect()
        db.create_tables([Campaign, Character])

    def cog_unload(self):
        db.close()

    @commands.command(name='create_campaign')
    async def create_campaign(self, ctx, max_players: int, *, description: str):
        """Create a new Pathfinder campaign"""
        # Generate unique campaign ID
        campaign_id = str(uuid.uuid4())[:8]

        # Create campaign
        campaign = Campaign.create(
            id=campaign_id,
            name=f"{ctx.author.name}'s Campaign",
            dm_id=str(ctx.author.id),
            max_players=max_players,
            description=description
        )

        # Create embed
        embed = discord.Embed(
            title=f"New Campaign: {campaign.name}",
            description=description,
            color=discord.Color.green()
        )
        embed.add_field(name="Campaign ID", value=campaign_id, inline=False)
        embed.add_field(name="DM", value=ctx.author.mention, inline=True)
        embed.add_field(name="Players", value=f"1/{max_players}", inline=True)

        await ctx.send(embed=embed)

    @commands.command(name='join_campaign')
    async def join_campaign(self, ctx, campaign_id: str, character_name: str, character_class: str,
                            character_level: int):
        """Join an existing campaign"""
        try:
            campaign = Campaign.get_by_id(campaign_id)

            # Check if campaign is full
            if campaign.current_players >= campaign.max_players:
                await ctx.send("Sorry, this campaign is full!")
                return

            # Create character and add to campaign
            Character.create(
                campaign=campaign,
                player_id=str(ctx.author.id),
                character_name=character_name,
                character_class=character_class,
                character_level=character_level
            )

            # Update campaign player count
            campaign.current_players += 1
            campaign.save()

            await ctx.send(f"📜 {ctx.author.mention} joined the campaign with {character_name} the {character_class}!")

        except Campaign.DoesNotExist:
            await ctx.send(f"No campaign found with ID {campaign_id}")

    @commands.command(name='list_campaigns')
    async def list_campaigns(self, ctx):
        """List all open campaigns"""
        open_campaigns = Campaign.select().where(Campaign.status == 'Open')

        if not open_campaigns:
            await ctx.send("No open campaigns at the moment!")
            return

        for campaign in open_campaigns:
            embed = discord.Embed(
                title=campaign.name,
                description=campaign.description,
                color=discord.Color.blue()
            )
            embed.add_field(name="Campaign ID", value=campaign.id, inline=False)
            embed.add_field(name="DM", value=f"<@{campaign.dm_id}>", inline=True)
            embed.add_field(name="Players", value=f"{campaign.current_players}/{campaign.max_players}", inline=True)

            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(LFGCog(bot))