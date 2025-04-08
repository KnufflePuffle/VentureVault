import discord
from discord import SelectOption, ButtonStyle
import datetime
from typing import List, Dict, Optional


class GameSessionPoll:
    def __init__(self, bot):
        self.bot = bot
        # Store active polls: channel_id -> poll_data
        self.active_polls = {}

    async def create_poll(self, ctx, plot_point_id, plot_title,
                          min_players=3, max_players=7,
                          game_master_id=None, suggested_dates=None):
        """
        Create a new game session poll in the specified channel

        Parameters:
        - ctx: Command context or channel object
        - plot_point_id: ID of the plot point
        - plot_title: Title of the plot point
        - min_players: Minimum number of players needed
        - max_players: Maximum number of players allowed
        - game_master_id: User ID of the game master (optional)
        - suggested_dates: List of datetime objects for suggested dates (optional)
        """
        # Handle different types of ctx parameter
        if hasattr(ctx, 'channel'):
            channel = ctx.channel
            author_id = ctx.author.id if hasattr(ctx, 'author') else game_master_id
        else:
            channel = ctx  # ctx is the channel directly
            author_id = game_master_id

        # Generate default dates if none provided
        if suggested_dates is None:
            suggested_dates = self.generate_custom_dates(3)

        # Store poll information
        poll_data = {
            "plot_point_id": plot_point_id,
            "plot_title": plot_title,
            "min_players": min_players,
            "max_players": max_players,
            "game_master_id": game_master_id,
            "suggested_dates": suggested_dates,
            "participants": {},  # user_id -> {date -> availability}
            "poll_message_id": None,
            "created_at": datetime.datetime.now(),
            "created_by": author_id
        }

        # Create initial poll embed
        embed = await self._create_poll_embed(poll_data)

        # Send poll message with components
        if hasattr(ctx, 'send'):
            message = await ctx.send(
                "## 📅 Spieltermin-Umfrage für Plot Point erstellt!",
                embed=embed,
                view=GameSessionPollView(self, poll_data)
            )
        else:
            message = await channel.send(
                "## 📅 Spieltermin-Umfrage für Plot Point erstellt!",
                embed=embed,
                view=GameSessionPollView(self, poll_data)
            )

        # Store message ID
        poll_data["poll_message_id"] = message.id
        self.active_polls[channel.id] = poll_data

        # If GM is specified, ask them to select availability first
        if game_master_id:
            guild = channel.guild
            gm_user = guild.get_member(game_master_id)
            if gm_user:
                await channel.send(
                    f"{gm_user.mention} Als Spielleitung wirst du gebeten, zuerst deine Verfügbarkeit anzugeben. "
                    f"Nur Zeiten, die du auswählst, werden für andere Spieler:in zur Verfügung stehen."
                )

        return message

    def generate_custom_dates(self, weeks=3):
        """
        Generate custom date suggestions for:
        - The next three Saturdays at 09:00 and 15:00
        - Sundays at 09:00 and 15:00
        - Fridays at 17:00

        Args:
            weeks (int): Number of weeks to generate dates for (default: 3)

        Returns:
            list: List of datetime objects with the requested dates and times
        """
        suggested_dates = []
        today = datetime.datetime.now()

        # Find the next Friday, Saturday and Sunday
        days_ahead = {
            4: "Friday",  # 4 represents Friday (0 is Monday in the datetime module)
            5: "Saturday",  # 5 represents Saturday
            6: "Sunday"  # 6 represents Sunday
        }

        # Calculate days until next Friday, Saturday, and Sunday
        current_weekday = today.weekday()
        days_until = {}

        for day_num, day_name in days_ahead.items():
            # Calculate days until the next occurrence of this weekday
            days_until[day_name] = (day_num - current_weekday) % 7
            # If today is the day and we've already passed the desired times, add 7 days
            if days_until[day_name] == 0 and today.hour >= 17:  # Using 17 as the latest time slot
                days_until[day_name] = 7

        # Generate dates for the specified number of weeks
        for week in range(weeks):
            # Friday at 17:00
            friday_date = today + datetime.timedelta(days=days_until["Friday"] + week * 7)
            suggested_dates.append(friday_date.replace(hour=17, minute=0, second=0, microsecond=0))

            # Saturday at 09:00 and 15:00
            saturday_date = today + datetime.timedelta(days=days_until["Saturday"] + week * 7)
            suggested_dates.append(saturday_date.replace(hour=9, minute=0, second=0, microsecond=0))
            suggested_dates.append(saturday_date.replace(hour=15, minute=0, second=0, microsecond=0))

            # Sunday at 09:00 and 15:00
            sunday_date = today + datetime.timedelta(days=days_until["Sunday"] + week * 7)
            suggested_dates.append(sunday_date.replace(hour=9, minute=0, second=0, microsecond=0))
            suggested_dates.append(sunday_date.replace(hour=15, minute=0, second=0, microsecond=0))

        # Sort dates chronologically
        suggested_dates.sort()

        return suggested_dates

    async def _create_poll_embed(self, poll_data):
        """Create an embed for the poll"""
        embed = discord.Embed(
            title=f"Spieltermin für '{poll_data['plot_title']}'",
            description="Bitte wähle die Termine, an denen du teilnehmen kannst, und ob du als Spieler:in teilnehmen möchtest.",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Plot Point",
            value=f"ID: {poll_data['plot_point_id']}",
            inline=True
        )

        embed.add_field(
            name="Spieler:innen",
            value=f"Min: {poll_data['min_players']} / Max: {poll_data['max_players']}",
            inline=True
        )

        # Add game master if available
        if poll_data["game_master_id"]:
            embed.add_field(
                name="Spielleitung",
                value=f"<@{poll_data['game_master_id']}>",
                inline=True
            )
        else:
            embed.add_field(
                name="Spielleitung",
                value="Noch nicht festgelegt",
                inline=True
            )

        # Create date availability overview
        date_table = await self._create_date_table(poll_data)
        if date_table:
            embed.add_field(
                name="Terminübersicht",
                value=date_table,
                inline=False
            )

        # Add participant list
        participant_list = await self._create_participant_list(poll_data)
        if participant_list:
            embed.add_field(
                name="Interessierte Spieler:innen",
                value=participant_list,
                inline=False
            )
        else:
            embed.add_field(
                name="Interessierte Spieler:innen",
                value="Noch keine Anmeldungen.",
                inline=False
            )

        # Add footer with creation date
        embed.set_footer(text=f"Erstellt am {poll_data['created_at'].strftime('%d.%m.%Y um %H:%M Uhr')}")

        return embed

    async def _create_date_table(self, poll_data):
        """Create a formatted date table showing availability"""
        if not poll_data.get("suggested_dates"):
            return "Keine Termine vorgeschlagen."

        # Filter dates based on GM availability if GM has responded
        available_dates = poll_data["suggested_dates"]
        gm_id = poll_data.get("game_master_id")
        if gm_id and gm_id in poll_data["participants"]:
            gm_avail = poll_data["participants"][gm_id]
            available_dates = [date for date in available_dates if gm_avail.get(date.isoformat(), False)]

            # If GM hasn't selected any dates yet
            if not available_dates and gm_id in poll_data["participants"]:
                return "Spielleitung hat noch keine Termine ausgewählt."

        # Build date table
        table = []
        for date in available_dates:
            # Format: Mon, 01.01. 19:00 | 👍 3
            formatted_date = date.strftime("%a, %d.%m. %H:%M")
            count = sum(1 for p in poll_data["participants"].values()
                         if p.get(date.isoformat(), False))

            # Add emoji indicators
            if count >= poll_data["min_players"]:
                status = "✅"  # Green checkmark for enough players
            elif count > 0:
                status = "👍"  # Thumbs up for some players
            else:
                status = "⬜"  # White square for no players

            table.append(f"{status} {formatted_date} | {count} Spieler:innen")

        return "\n".join(table) if table else "Keine verfügbaren Termine."

    async def _create_participant_list(self, poll_data):
        """Create a list of participants who want to join the game"""
        if not poll_data["participants"]:
            return None

        participants = []
        for user_id, availability in poll_data["participants"].items():
            # Count how many dates they're available
            available_count = sum(1 for v in availability.values() if v)

            # Skip users who haven't marked any dates
            if available_count == 0:
                continue

            is_gm = user_id == poll_data.get("game_master_id")
            role = "👑 Spielleitung" if is_gm else "👤 Spieler:in"

            participants.append(f"<@{user_id}> ({role}) - {available_count} Termine möglich")

        return "\n".join(participants) if participants else None

    async def update_poll(self, channel_id):
        """Update the poll message with current information"""
        if channel_id not in self.active_polls:
            return

        poll_data = self.active_polls[channel_id]
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        try:
            # Get the message
            message = await channel.fetch_message(poll_data["poll_message_id"])

            # Update embed
            embed = await self._create_poll_embed(poll_data)

            # Update message
            await message.edit(embed=embed, view=GameSessionPollView(self, poll_data))
        except Exception as e:
            print(f"Error updating poll: {e}")

    async def register_availability(self, user_id, channel_id, selected_dates):
        """Register a user's availability for the given dates"""
        if channel_id not in self.active_polls:
            return False

        poll_data = self.active_polls[channel_id]

        # Initialize user in participants dict if not exists
        if user_id not in poll_data["participants"]:
            poll_data["participants"][user_id] = {}

        # Update availability
        for date in poll_data["suggested_dates"]:
            date_str = date.isoformat()
            poll_data["participants"][user_id][date_str] = date_str in selected_dates

        # Update the poll
        await self.update_poll(channel_id)
        return True

    async def finalize_session(self, channel_id, selected_date):
        """Finalize the game session with the selected date"""
        if channel_id not in self.active_polls:
            return False

        poll_data = self.active_polls[channel_id]
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return False

        # Get participants who are available on this date
        available_participants = []
        for user_id, availability in poll_data["participants"].items():
            if availability.get(selected_date.isoformat(), False):
                available_participants.append(user_id)

        # Create confirmation message
        date_formatted = selected_date.strftime("%A, %d.%m.%Y um %H:%M Uhr")

        # Create embed for the scheduled session
        embed = discord.Embed(
            title=f"Spieltermin für '{poll_data['plot_title']}' festgelegt!",
            description=f"Der Spieltermin wurde festgelegt auf **{date_formatted}**.",
            color=discord.Color.green()
        )

        # Add game master
        if poll_data["game_master_id"]:
            embed.add_field(
                name="Spielleitung",
                value=f"<@{poll_data['game_master_id']}>",
                inline=False
            )

        # Add participant list
        if available_participants:
            participants_str = "\n".join([f"<@{user_id}>" for user_id in available_participants
                                          if user_id != poll_data["game_master_id"]])
            embed.add_field(
                name=f"Teilnehmende ({len(available_participants)})",
                value=participants_str or "Keine Teilnehmer:innen verfügbar.",
                inline=False
            )

        # Send confirmation
        await channel.send(
            "## 🎮 Spieltermin bestätigt!",
            embed=embed
        )

        # Mention all participants
        mentions = " ".join([f"<@{user_id}>" for user_id in available_participants])
        if mentions:
            await channel.send(
                f"{mentions} Bitte merkt euch den Termin vor: **{date_formatted}**"
            )

        # Remove the poll from active polls
        del self.active_polls[channel_id]

        return True

    async def cancel_poll(self, channel_id):
        """Cancel the poll in the specified channel"""
        if channel_id not in self.active_polls:
            return False

        # Remove the poll
        del self.active_polls[channel_id]
        return True


class DateSelectView(discord.ui.View):
    def __init__(self, poll_manager, poll_data, user_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.poll_manager = poll_manager
        self.poll_data = poll_data
        self.user_id = user_id
        self.selected_dates = []

        # Add date select menu
        self._add_date_select()

    def _add_date_select(self):
        # Get available dates
        available_dates = self.poll_data["suggested_dates"]

        # Filter by GM availability if necessary
        gm_id = self.poll_data.get("game_master_id")
        if gm_id and gm_id in self.poll_data["participants"] and self.user_id != gm_id:
            gm_avail = self.poll_data["participants"][gm_id]
            available_dates = [date for date in available_dates
                               if gm_avail.get(date.isoformat(), False)]

        # If no dates available
        if not available_dates:
            return

        # User's previous selections
        user_availability = {}
        if self.user_id in self.poll_data["participants"]:
            user_availability = self.poll_data["participants"][self.user_id]

        # Create options for select menu
        options = []
        for date in available_dates:
            date_str = date.isoformat()
            formatted_date = date.strftime("%a, %d.%m. %H:%M")

            # Check if this date was previously selected by the user
            default = user_availability.get(date_str, False)
            if default:
                self.selected_dates.append(date_str)

            options.append(SelectOption(
                label=formatted_date,
                value=date_str,
                default=default
            ))

        # Split into groups of 25 if needed (Discord limit)
        for i in range(0, len(options), 25):
            select_options = options[i:i + 25]

            # Add a select menu for this group of options
            select = discord.ui.Select(
                placeholder=f"Wähle verfügbare Termine ({i + 1}-{i + len(select_options)})",
                min_values=0,
                max_values=len(select_options),
                options=select_options
            )

            # Set callback
            select.callback = self.select_callback
            self.add_item(select)

    async def select_callback(self, interaction):
        """Handle date selection"""
        # Ensure only the right user can interact
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Du kannst nicht die Verfügbarkeit anderer Benutzer ändern.",
                ephemeral=True
            )
            return

        # Update selected dates
        self.selected_dates = []
        for child in self.children:
            if isinstance(child, discord.ui.Select):
                self.selected_dates.extend(child.values)

        # Register availability
        await self.poll_manager.register_availability(
            self.user_id,
            interaction.channel.id,
            self.selected_dates
        )

        await interaction.response.send_message(
            f"Deine Verfügbarkeit wurde aktualisiert. Du hast {len(self.selected_dates)} Termine ausgewählt.",
            ephemeral=True
        )


class FinalizeDateView(discord.ui.View):
    def __init__(self, poll_manager, poll_data):
        super().__init__(timeout=300)  # 5 minute timeout
        self.poll_manager = poll_manager
        self.poll_data = poll_data

        # Add date select
        self._add_date_select()

    def _add_date_select(self):
        """Add date selection dropdown"""
        # Get available dates that meet minimum player count
        available_dates = []
        for date in self.poll_data["suggested_dates"]:
            date_str = date.isoformat()
            count = sum(1 for p in self.poll_data["participants"].values()
                        if p.get(date_str, False))

            if count >= self.poll_data["min_players"]:
                formatted_date = date.strftime("%a, %d.%m. %H:%M")
                available_dates.append((date, formatted_date, count))

        # Sort by number of participants (descending)
        available_dates.sort(key=lambda x: x[2], reverse=True)

        # Create options
        options = []
        for date, formatted_date, count in available_dates:
            options.append(SelectOption(
                label=formatted_date,
                value=date.isoformat(),
                description=f"{count} Spieler:innen verfügbar"
            ))

        # If no viable dates
        if not options:
            # Add dummy option
            options.append(SelectOption(
                label="Keine passenden Termine gefunden",
                value="none"
            ))

        # Add select menu
        select = discord.ui.Select(
            placeholder="Wähle einen Termin für die Spielsession",
            options=options,
            disabled=len(options) == 1 and options[0].value == "none"
        )
        select.callback = self.select_callback
        self.add_item(select)

        # Add cancel button
        cancel_button = discord.ui.Button(
            label="Abbrechen",
            style=ButtonStyle.secondary
        )
        cancel_button.callback = self.cancel_callback
        self.add_item(cancel_button)

    async def select_callback(self, interaction):
        """Handle date selection"""
        value = interaction.data["values"][0]

        # Handle no viable dates
        if value == "none":
            await interaction.response.send_message(
                "Es gibt keine Termine, an denen genügend Spieler:innen teilnehmen können.",
                ephemeral=True
            )
            return

        # Get the date object
        for date in self.poll_data["suggested_dates"]:
            if date.isoformat() == value:
                # Finalize the session
                success = await self.poll_manager.finalize_session(interaction.channel.id, date)

                if success:
                    await interaction.response.send_message(
                        "Der Spieltermin wurde erfolgreich festgelegt!",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "Es gab ein Problem beim Festlegen des Termins.",
                        ephemeral=True
                    )
                break
        else:
            await interaction.response.send_message(
                "Ungültiger Termin ausgewählt.",
                ephemeral=True
            )

    async def cancel_callback(self, interaction):
        """Handle cancel button"""
        await interaction.response.send_message(
            "Terminauswahl abgebrochen.",
            ephemeral=True
        )
        self.stop()


class GameSessionPollView(discord.ui.View):
    def __init__(self, poll_manager, poll_data):
        super().__init__(timeout=None)  # No timeout for the main poll view
        self.poll_manager = poll_manager
        self.poll_data = poll_data

    @discord.ui.button(label="Verfügbarkeit angeben", style=ButtonStyle.primary, emoji="📅")
    async def availability_button(self, interaction, button):
        """Handle availability selection button"""
        # Show availability modal
        await interaction.response.send_message(
            "Wähle die Termine, an denen du verfügbar bist:",
            view=DateSelectView(self.poll_manager, self.poll_data, interaction.user.id),
            ephemeral=True
        )

    @discord.ui.button(label="Termin festlegen", style=ButtonStyle.success, emoji="✅")
    async def finalize_button(self, interaction, button):
        """Handle finalize session button"""
        # Check if user is authorized (GM or creator)
        is_gm = self.poll_data.get("game_master_id") == interaction.user.id
        is_creator = self.poll_data.get("created_by") == interaction.user.id
        is_admin = interaction.user.guild_permissions.administrator

        if not (is_gm or is_creator or is_admin):
            await interaction.response.send_message(
                "Nur Spielleitung, Ersteller:innen der Umfrage oder Admins können den Termin festlegen.",
                ephemeral=True
            )
            return

        # Show finalize view
        await interaction.response.send_message(
            "Wähle einen Termin für die Spielsession:",
            view=FinalizeDateView(self.poll_manager, self.poll_data),
            ephemeral=True
        )

    @discord.ui.button(label="Umfrage abbrechen", style=ButtonStyle.danger, emoji="❌")
    async def cancel_button(self, interaction, button):
        """Handle cancel poll button"""
        # Check if user is authorized
        is_creator = self.poll_data.get("created_by") == interaction.user.id
        is_admin = interaction.user.guild_permissions.administrator

        if not (is_creator or is_admin):
            await interaction.response.send_message(
                "Nur Ersteller:innen der Umfrage oder Admins können die Umfrage abbrechen.",
                ephemeral=True
            )
            return

        # Confirm cancellation
        confirm_view = ConfirmCancelView(self.poll_manager, interaction.channel.id)
        await interaction.response.send_message(
            "Bist du sicher, dass du die Umfrage abbrechen möchtest?",
            view=confirm_view,
            ephemeral=True
        )


class ConfirmCancelView(discord.ui.View):
    def __init__(self, poll_manager, channel_id):
        super().__init__(timeout=60)  # 1 minute timeout
        self.poll_manager = poll_manager
        self.channel_id = channel_id

    @discord.ui.button(label="Ja, abbrechen", style=ButtonStyle.danger)
    async def confirm_button(self, interaction, button):
        """Handle confirm button"""
        success = await self.poll_manager.cancel_poll(self.channel_id)

        if success:
            await interaction.response.send_message(
                "Die Umfrage wurde abgebrochen.",
                ephemeral=True
            )

            # Send message to channel that poll was cancelled
            channel = interaction.client.get_channel(self.channel_id)
            if channel:
                await channel.send("**Die Terminumfrage wurde abgebrochen.**")
        else:
            await interaction.response.send_message(
                "Es gab ein Problem beim Abbrechen der Umfrage.",
                ephemeral=True
            )

    @discord.ui.button(label="Nein, behalten", style=ButtonStyle.secondary)
    async def cancel_button(self, interaction, button):
        """Handle cancel button"""
        await interaction.response.send_message(
            "Abbruch der Umfrage wurde abgebrochen.",
            ephemeral=True
        )