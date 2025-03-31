import discord
from discord.ext import commands
from peewee import *
from datetime import datetime
import re

# Database setup remains the same as in the original code
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
    status = CharField(default='Inactive')  # Possible values: Inactive, Active, Finished
    channel_id = CharField(null=True)


class PlotPointManagementView(discord.ui.View):
    def __init__(self, plot_point, bot):
        super().__init__()
        self.plot_point = plot_point
        self.bot = bot

    @discord.ui.button(label="Activate", style=discord.ButtonStyle.green)
    async def activate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Fetch the campaign and category
            campaign = self.plot_point.campaign
            category = self.bot.get_channel(int(campaign.plot_category_id))

            # Create a new channel for the plot point
            plot_channel = await interaction.guild.create_text_channel(
                f"plot-{self.plot_point.number}-{self.plot_point.title.lower().replace(' ', '-')}",
                category=category
            )

            # Update the plot point in the database
            self.plot_point.status = 'Active'
            self.plot_point.channel_id = str(plot_channel.id)
            self.plot_point.save()

            # Send initial description to the new channel
            await plot_channel.send(
                f"**Plot Point {self.plot_point.number}: {self.plot_point.title}**\n{self.plot_point.description}")

            # Update the overview message
            await interaction.message.edit(
                embed=self.create_embed(),
                view=self.create_view_for_status()
            )

            await interaction.response.send_message(f"Activated plot point {self.plot_point.number}", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"Error activating plot point: {str(e)}", ephemeral=True)

    @discord.ui.button(label="Deactivate", style=discord.ButtonStyle.gray)
    async def deactivate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # If the channel exists, delete it
            if self.plot_point.channel_id:
                channel = self.bot.get_channel(int(self.plot_point.channel_id))
                if channel:
                    await channel.delete()

            # Update the plot point in the database
            self.plot_point.status = 'Inactive'
            self.plot_point.channel_id = None
            self.plot_point.save()

            # Update the overview message
            await interaction.message.edit(
                embed=self.create_embed(),
                view=self.create_view_for_status()
            )

            await interaction.response.send_message(f"Deactivated plot point {self.plot_point.number}", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"Error deactivating plot point: {str(e)}", ephemeral=True)

    @discord.ui.button(label="Finished", style=discord.ButtonStyle.red)
    async def finished_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Close all related channels
            campaign = self.plot_point.campaign
            category = self.bot.get_channel(int(campaign.plot_category_id))

            # Delete the specific plot point channel
            if self.plot_point.channel_id:
                channel = self.bot.get_channel(int(self.plot_point.channel_id))
                if channel:
                    await channel.delete()

            # Update the plot point in the database
            self.plot_point.status = 'Finished'
            self.plot_point.channel_id = None
            self.plot_point.save()

            # Find the overview channel and update the message
            overview_channel = discord.utils.get(category.text_channels, name="plot-overview")

            # Update the overview embed to show finished status
            embed = discord.Embed(
                title=f"Plot Point {self.plot_point.number}: {self.plot_point.title}",
                description=self.plot_point.description,
                color=discord.Color.green()
            )
            embed.add_field(name="Status", value="Finished ✅")

            # Edit the original message to reflect finished status
            await interaction.message.edit(embed=embed, view=None)

            await interaction.response.send_message(f"Marked plot point {self.plot_point.number} as Finished",
                                                    ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"Error marking plot point as finished: {str(e)}", ephemeral=True)

    def create_embed(self):
        # Create an embed with plot point details
        embed = discord.Embed(
            title=f"Plot Point {self.plot_point.number}: {self.plot_point.title}",
            description=self.plot_point.description,
            color=discord.Color.blue()
        )
        embed.add_field(name="Status", value=self.plot_point.status)
        return embed

    def create_view_for_status(self):
        # Create a view with buttons enabled/disabled based on current status
        view = PlotPointManagementView(self.plot_point, self.bot)

        # Disable activate button if already active
        if self.plot_point.status == 'Active':
            for item in view.children:
                if item.label == "Activate":
                    item.disabled = True

        # Disable deactivate button if inactive
        if self.plot_point.status == 'Inactive':
            for item in view.children:
                if item.label == "Deactivate":
                    item.disabled = True

        return view


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
                campaign = Campaign.create(name=f"Westmarch {datetime.now().year}")

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

            # Create plot point in database (initially Inactive)
            plot_point = PlotPoint.create(
                campaign=campaign,
                number=number,
                title=title,
                description=description or "No description provided.",
                status='Inactive'  # Start in Inactive state
            )

            # Find or create overview channel
            overview_channel = discord.utils.get(category.text_channels, name="plot-overview")
            if not overview_channel:
                overview_channel = await ctx.guild.create_text_channel(
                    "plot-overview",
                    category=category
                )

            # Create view for the plot point
            view = PlotPointManagementView(plot_point, self.bot)

            # Create embed for the plot point
            embed = discord.Embed(
                title=f"Plot Point {number}: {title}",
                description=description or "No description provided.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Status", value="Inactive")

            # Send message to overview channel with buttons
            await overview_channel.send(embed=embed, view=view)

            await ctx.send(f"Created plot point {number}: '{title}' in Inactive state")

        except Exception as e:
            await ctx.send(f"Error creating plot point: {str(e)}")


async def setup(bot):
    await bot.add_cog(PlotPointCog(bot))