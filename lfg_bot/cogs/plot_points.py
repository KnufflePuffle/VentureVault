import discord
from discord.ext import commands
from peewee import *
from datetime import datetime
import re

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

    def cog_unload(self):
        db.close()

    @commands.command(name='add_plot_point')
    async def add_plot_point(self, ctx, number: str = None, title: str = None, *, description: str = None):
        """Add a new plot point

        Usage: !add_plot_point <number> <title> <description>
        Example: !add_plot_point 01 "First Adventure" A thrilling start to our campaign
        """
        # Check if all required arguments are provided
        if not all([number, title, description]):
            await ctx.send(
                "❌ Invalid command format. Please use: "
                "`!add_plot_point <number> <title> <description>`\n\n"
                "Example: `!add_plot_point 01 \"First Adventure\" A thrilling start to our campaign`"
            )
            return

        try:
            # Validate plot point number format
            if not re.match(r'^\d+[a-z]?$', number):
                await ctx.send("❌ Invalid plot point number. Use format like '01', '02', '03a', '03b'")
                return

            # Find or create the campaign
            campaign = Campaign.select().order_by(Campaign.id.desc()).first()
            if not campaign:
                campaign = Campaign.create(name=f"Campaign {datetime.now().year}")

            # Create plot point in database
            plot_point = PlotPoint.create(
                campaign=campaign,
                number=number,
                title=title,
                description=description,
                status='Inactive'
            )

            # Create an embed for the plot point
            embed = discord.Embed(
                title=f"Plot Point {number}: {title}",
                description=description,
                color=discord.Color.blue()
            )
            embed.add_field(name="Status", value="🔘 Inactive", inline=False)

            # Find or create overview channel
            if not campaign.plot_category_id:
                category = await ctx.guild.create_category_channel(f"{campaign.name} Plot Points")
                campaign.plot_category_id = str(category.id)
                campaign.save()
            else:
                category = ctx.guild.get_channel(int(campaign.plot_category_id))

            overview_channel = discord.utils.get(category.text_channels, name="plot-overview")
            if not overview_channel:
                overview_channel = await ctx.guild.create_text_channel(
                    "plot-overview",
                    category=category
                )

            # Send the plot point message
            await overview_channel.send(embed=embed)

            await ctx.send(f"✅ Created plot point {number}: '{title}'")

        except Exception as e:
            await ctx.send(f"❌ Error creating plot point: {str(e)}")
            # Log the full error for debugging
            print(f"Plot Point Creation Error: {e}")


async def setup(bot):
    # Check if the cog is already loaded
    if not bot.get_cog('PlotPointCog'):
        await bot.add_cog(PlotPointCog(bot))
    else:
        print("PlotPointCog is already loaded. Skipping.")