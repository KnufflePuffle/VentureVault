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
    number = CharField()  # Allows for 01, 02, 03a, 03b, etc.
    title = CharField()
    description = TextField()
    status = CharField(default='Active')  # Active, Completed, Archived
    channel_id = CharField(null=True)


class PlotPointCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        db.connect()
        db.create_tables([Campaign, PlotPoint])

    def cog_unload(self):
        db.close()

    @commands.command(name='add_plot_point')
    async def add_plot_point(self, ctx, number: str, title: str, *, description: str = None):
        """Add a new plot point with a specific numbering system"""
        # Find the most recent campaign (or create one if none exists)
        try:
            campaign = Campaign.select().order_by(Campaign.id.desc()).first()
            if not campaign:
                campaign = Campaign.create(name=f"Campaign {datetime.now().year}")

            # Validate plot point number format
            if not re.match(r'^\d+[a-z]?$', number):
                await ctx.send("Invalid plot point number. Use format like '01', '02', '03a', '03b'")
                return

            # Create category if not exists
            if not campaign.plot_category_id:
                category = await ctx.guild.create_category_channel(f"{campaign.name} Plot Points")
                campaign.plot_category_id = str(category.id)
                campaign.save()
            else:
                category = ctx.guild.get_channel(int(campaign.plot_category_id))

            # Create plot point channel
            plot_channel = await ctx.guild.create_text_channel(
                f"plot-{number}-{title.lower().replace(' ', '-')}",
                category=category
            )

            # Create plot point in database
            plot_point = PlotPoint.create(
                campaign=campaign,
                number=number,
                title=title,
                description=description,
                channel_id=str(plot_channel.id)
            )

            # Send initial description to plot point channel
            await plot_channel.send(f"**Plot Point {number}: {title}**\n{description}")

            # Find or create overview channel
            overview_channel = discord.utils.get(category.text_channels, name="plot-overview")
            if not overview_channel:
                overview_channel = await ctx.guild.create_text_channel(
                    "plot-overview",
                    category=category
                )

            # Update overview channel
            await overview_channel.send(
                f"📝 **Plot Point {number}:** {title}\n"
                f"Channel: {plot_channel.mention}\n"
                f"Status: 🟢 Active"
            )

            await ctx.send(f"Created plot point {number}: '{title}' with dedicated channel")

        except Exception as e:
            await ctx.send(f"Error creating plot point: {str(e)}")

    @commands.command(name='complete_plot_point')
    async def complete_plot_point(self, ctx, number: str):
        """Mark a plot point as completed"""
        try:
            # Find the plot point
            plot_point = PlotPoint.get(PlotPoint.number == number)
            plot_point.status = 'Completed'
            plot_point.save()

            # Find the plot point's channel
            channel = self.bot.get_channel(int(plot_point.channel_id))

            if channel:
                # Update channel name to show completion
                await channel.edit(name=f"completed-{channel.name}")

                # Send completion message
                await channel.send("🏁 **Plot Point Completed!**")

            # Update overview channel
            category = self.bot.get_channel(int(plot_point.campaign.plot_category_id))
            overview_channel = discord.utils.get(category.text_channels, name="plot-overview")

            await overview_channel.send(f"✅ **Plot Point {number} Completed:** {plot_point.title}")

            await ctx.send(f"Plot point {number} '{plot_point.title}' marked as completed")

        except PlotPoint.DoesNotExist:
            await ctx.send(f"No plot point found with number {number}")


async def setup(bot):
    await bot.add_cog(PlotPointCog(bot))