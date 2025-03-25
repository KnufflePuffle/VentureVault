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
    status = CharField(default='Inactive')  # Inactive, Active, Completed, Archived
    potential_players = TextField(null=True)  # Storing player IDs as comma-separated string
    channel_id = CharField(null=True)


class PlotPointCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        db.connect()
        db.create_tables([Campaign, PlotPoint])

    def cog_unload(self):
        db.close()

    @commands.command(name='add_inactive_plot_point')
    async def add_inactive_plot_point(self, ctx, number: str, title: str, *, description: str):
        """Add a new inactive plot point for future exploration"""
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

            # Create an embed for the inactive plot point
            embed = discord.Embed(
                title=f"Inactive Plot Point {number}: {title}",
                description=description,
                color=discord.Color.dark_grey()
            )
            embed.add_field(name="Status", value="🔘 Inactive", inline=False)
            embed.add_field(name="How to Activate", value="React with 👥 to show interest in this plot point!",
                            inline=False)

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

            # Send the inactive plot point message
            inactive_message = await overview_channel.send(embed=embed)

            # Add reaction for interest
            await inactive_message.add_reaction('👥')

            await ctx.send(f"Created inactive plot point {number}: '{title}'")

        except Exception as e:
            await ctx.send(f"Error creating inactive plot point: {str(e)}")

    @commands.command(name='activate_plot_point')
    async def activate_plot_point(self, ctx, number: str):
        """Activate an inactive plot point and create a discussion channel"""
        try:
            # Find the plot point
            plot_point = PlotPoint.get(
                (PlotPoint.number == number) &
                (PlotPoint.status == 'Inactive')
            )

            # Create channel for discussion
            campaign = plot_point.campaign
            category = ctx.guild.get_channel(int(campaign.plot_category_id))

            # Create activation channel
            activation_channel = await ctx.guild.create_text_channel(
                f"plot-{number}-activation",
                category=category
            )

            # Update plot point status and channel
            plot_point.status = 'Active'
            plot_point.channel_id = str(activation_channel.id)
            plot_point.save()

            # Send initial message in the activation channel
            await activation_channel.send(
                f"**Plot Point {number}: {plot_point.title}** is now active!\n\n"
                f"**Description:**\n{plot_point.description}\n\n"
                "👥 Who's interested in playing? Please comment below!"
            )

            # Update overview channel
            overview_channel = discord.utils.get(category.text_channels, name="plot-overview")
            await overview_channel.send(
                f"🟢 **Plot Point {number}:** {plot_point.title} has been activated!\n"
                f"Discussion Channel: {activation_channel.mention}"
            )

            await ctx.send(f"Activated plot point {number} and created discussion channel")

        except PlotPoint.DoesNotExist:
            await ctx.send(f"No inactive plot point found with number {number}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Track players interested in inactive plot points"""
        if user.bot:
            return

        # Check if the reaction is on an overview channel message
        if reaction.message.channel.name != "plot-overview":
            return

        # Check if the reaction is the interest reaction
        if str(reaction.emoji) == '👥':
            # Find the corresponding plot point
            try:
                # Extract plot point number from the embed
                embed = reaction.message.embeds[0]
                plot_point_number = embed.title.split(':')[0].replace("Inactive Plot Point ", "").strip()

                plot_point = PlotPoint.get(
                    (PlotPoint.number == plot_point_number) &
                    (PlotPoint.status == 'Inactive')
                )

                # Track interested players
                interested_players = plot_point.potential_players or ""
                player_id = str(user.id)

                if player_id not in interested_players.split(','):
                    if interested_players:
                        interested_players += f",{player_id}"
                    else:
                        interested_players = player_id

                plot_point.potential_players = interested_players
                plot_point.save()

                # Optionally, send a DM to the user
                await user.send(f"You've shown interest in Plot Point {plot_point_number}: {plot_point.title}")

            except PlotPoint.DoesNotExist:
                pass


async def setup(bot):
    await bot.add_cog(PlotPointCog(bot))