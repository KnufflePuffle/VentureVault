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
    created_at = DateTimeField(default=datetime.now)
    dm_id = CharField(null=True)  # Store the Discord ID of the DM


class PlotPoint(BaseModel):
    campaign = ForeignKeyField(Campaign, backref='plot_points')
    number = CharField()
    title = CharField()
    description = TextField()
    status = CharField(default='Inactive')
    potential_players = TextField(null=True)
    channel_id = CharField(null=True)
    created_at = DateTimeField(default=datetime.now)


class PlotPointCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        db.connect()
        db.create_tables([Campaign, PlotPoint])

    def cog_unload(self):
        db.close()

    @commands.command(name='create_campaign')
    async def create_campaign(self, ctx, *, name: str = None):
        """Create a new campaign

        Usage: !create_campaign <name>
        Example: !create_campaign Curse of Strahd
        """
        if not name:
            await ctx.send("❌ Please provide a campaign name: `!create_campaign <name>`")
            return

        try:
            # Create new campaign
            campaign = Campaign.create(
                name=name,
                dm_id=str(ctx.author.id)
            )

            # Create category for the campaign
            category = await ctx.guild.create_category_channel(f"{name} Plot Points")
            campaign.plot_category_id = str(category.id)
            campaign.save()

            # Create overview channel
            overview_channel = await ctx.guild.create_text_channel(
                "plot-overview",
                category=category
            )

            await ctx.send(f"✅ Created campaign '{name}' with ID: {campaign.id}")

        except Exception as e:
            await ctx.send(f"❌ Error creating campaign: {str(e)}")
            print(f"Campaign Creation Error: {e}")

    @commands.command(name='list_campaigns')
    async def list_campaigns(self, ctx):
        """List all campaigns you have created

        Usage: !list_campaigns
        """
        try:
            # Find campaigns created by this user
            campaigns = Campaign.select().where(Campaign.dm_id == str(ctx.author.id))

            if not campaigns:
                await ctx.send("You haven't created any campaigns yet.")
                return

            embed = discord.Embed(
                title="Your Campaigns",
                description="Here are the campaigns you've created:",
                color=discord.Color.blue()
            )

            for campaign in campaigns:
                plot_count = PlotPoint.select().where(PlotPoint.campaign == campaign).count()
                embed.add_field(
                    name=f"ID: {campaign.id} - {campaign.name}",
                    value=f"Created: {campaign.created_at.strftime('%Y-%m-%d')}\nPlot Points: {plot_count}",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error listing campaigns: {str(e)}")
            print(f"List Campaigns Error: {e}")

    @commands.command(name='add_plot_point')
    async def add_plot_point(self, ctx, campaign_id: int = None, number: str = None, title: str = None, *,
                             description: str = None):
        """Add a new plot point to a specific campaign

        Usage: !add_plot_point <campaign_id> <number> <title> <description>
        Example: !add_plot_point 1 01 "First Adventure" A thrilling start to our campaign
        """
        # Check if all required arguments are provided
        if not all([campaign_id, number, title, description]):
            await ctx.send(
                "❌ Invalid command format. Please use: "
                "`!add_plot_point <campaign_id> <number> <title> <description>`\n\n"
                "Example: `!add_plot_point 1 01 \"First Adventure\" A thrilling start to our campaign`"
            )
            return

        try:
            # Validate plot point number format
            if not re.match(r'^\d+[a-z]?$', number):
                await ctx.send("❌ Invalid plot point number. Use format like '01', '02', '03a', '03b'")
                return

            # Find the campaign
            try:
                campaign = Campaign.get(Campaign.id == campaign_id)

                # Check if the user is the DM of this campaign
                if campaign.dm_id and campaign.dm_id != str(ctx.author.id):
                    await ctx.send("❌ You don't have permission to add plot points to this campaign.")
                    return

            except DoesNotExist:
                await ctx.send(f"❌ Campaign with ID {campaign_id} not found.")
                return

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
            category = None
            if campaign.plot_category_id:
                category = ctx.guild.get_channel(int(campaign.plot_category_id))

            if not category:
                category = await ctx.guild.create_category_channel(f"{campaign.name} Plot Points")
                campaign.plot_category_id = str(category.id)
                campaign.save()

            overview_channel = discord.utils.get(category.text_channels, name="plot-overview")
            if not overview_channel:
                overview_channel = await ctx.guild.create_text_channel(
                    "plot-overview",
                    category=category
                )

            # Send the plot point message
            await overview_channel.send(embed=embed)

            await ctx.send(f"✅ Created plot point {number}: '{title}' for campaign '{campaign.name}'")

        except Exception as e:
            await ctx.send(f"❌ Error creating plot point: {str(e)}")
            # Log the full error for debugging
            print(f"Plot Point Creation Error: {e}")

    @commands.command(name='list_plot_points')
    async def list_plot_points(self, ctx, campaign_id: int):
        """List all plot points for a specific campaign

        Usage: !list_plot_points <campaign_id>
        Example: !list_plot_points 1
        """
        try:
            # Find the campaign
            try:
                campaign = Campaign.get(Campaign.id == campaign_id)
            except DoesNotExist:
                await ctx.send(f"❌ Campaign with ID {campaign_id} not found.")
                return

            # Get plot points for this campaign
            plot_points = PlotPoint.select().where(PlotPoint.campaign == campaign).order_by(PlotPoint.number)

            if not plot_points:
                await ctx.send(f"No plot points found for campaign '{campaign.name}'")
                return

            # Create embed
            embed = discord.Embed(
                title=f"Plot Points for {campaign.name}",
                description=f"Campaign ID: {campaign.id}",
                color=discord.Color.blue()
            )

            for plot in plot_points:
                # Create status emoji
                status_emoji = "🔘"  # Default Inactive
                if plot.status == "Active":
                    status_emoji = "🟢"
                elif plot.status == "Complete":
                    status_emoji = "✅"

                embed.add_field(
                    name=f"{plot.number}: {plot.title} ({status_emoji} {plot.status})",
                    value=f"{plot.description[:100]}..." if len(plot.description) > 100 else plot.description,
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Error listing plot points: {str(e)}")
            print(f"List Plot Points Error: {e}")

    @commands.command(name='update_plot_status')
    async def update_plot_status(self, ctx, plot_id: int, status: str):
        """Update the status of a plot point

        Usage: !update_plot_status <plot_id> <status>
        Valid statuses: Inactive, Active, Complete
        Example: !update_plot_status 1 Active
        """
        valid_statuses = ["Inactive", "Active", "Complete"]

        # Validate status
        if status not in valid_statuses:
            await ctx.send(f"❌ Invalid status. Please use one of: {', '.join(valid_statuses)}")
            return

        try:
            # Find the plot point
            try:
                plot_point = PlotPoint.get(PlotPoint.id == plot_id)
            except DoesNotExist:
                await ctx.send(f"❌ Plot point with ID {plot_id} not found.")
                return

            # Check if user is the DM
            campaign = plot_point.campaign
            if campaign.dm_id and campaign.dm_id != str(ctx.author.id):
                await ctx.send("❌ You don't have permission to update this plot point.")
                return

            # Update status
            old_status = plot_point.status
            plot_point.status = status
            plot_point.save()

            # Create status emoji
            status_emoji = "🔘"  # Default Inactive
            if status == "Active":
                status_emoji = "🟢"
            elif status == "Complete":
                status_emoji = "✅"

            await ctx.send(
                f"✅ Updated plot point {plot_point.number}: '{plot_point.title}' status from '{old_status}' to '{status_emoji} {status}'")

            # Update message in overview channel if possible
            if campaign.plot_category_id and plot_point.channel_id:
                try:
                    category = ctx.guild.get_channel(int(campaign.plot_category_id))
                    if category:
                        overview_channel = discord.utils.get(category.text_channels, name="plot-overview")
                        if overview_channel:
                            # Create updated embed
                            embed = discord.Embed(
                                title=f"Plot Point {plot_point.number}: {plot_point.title}",
                                description=plot_point.description,
                                color=discord.Color.blue()
                            )
                            embed.add_field(name="Status", value=f"{status_emoji} {status}", inline=False)

                            # Note: This would require storing message IDs to update specific messages
                            # For now, just send a status update
                            await overview_channel.send(
                                f"**Status Update**: Plot point {plot_point.number} is now {status_emoji} {status}")
                except Exception as e:
                    print(f"Error updating overview message: {e}")

        except Exception as e:
            await ctx.send(f"❌ Error updating plot point: {str(e)}")
            print(f"Update Plot Status Error: {e}")

    @commands.command(name='delete_plot_point')
    async def delete_plot_point(self, ctx, plot_id: int):
        """Delete a plot point

        Usage: !delete_plot_point <plot_id>
        Example: !delete_plot_point 1
        """
        try:
            # Find the plot point
            try:
                plot_point = PlotPoint.get(PlotPoint.id == plot_id)
            except DoesNotExist:
                await ctx.send(f"❌ Plot point with ID {plot_id} not found.")
                return

            # Check if user is the DM
            campaign = plot_point.campaign
            if campaign.dm_id and campaign.dm_id != str(ctx.author.id):
                await ctx.send("❌ You don't have permission to delete this plot point.")
                return

            # Store info for confirmation message
            plot_number = plot_point.number
            plot_title = plot_point.title

            # Delete the plot point
            plot_point.delete_instance()

            await ctx.send(f"✅ Deleted plot point {plot_number}: '{plot_title}'")

        except Exception as e:
            await ctx.send(f"❌ Error deleting plot point: {str(e)}")
            print(f"Delete Plot Point Error: {e}")


async def setup(bot):
    # Check if the cog is already loaded
    if not bot.get_cog('PlotPointCog'):
        await bot.add_cog(PlotPointCog(bot))
    else:
        print("PlotPointCog is already loaded. Skipping.")
