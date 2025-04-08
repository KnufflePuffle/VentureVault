import discord
from discord import ButtonStyle, ui


# Status buttons
class PlotpointButtons(ui.View):
    def __init__(self, plotpoint_id, current_status):
        super().__init__(timeout=None)
        self.plotpoint_id = plotpoint_id

        # Add appropriate buttons based on current status
        if current_status != 'Active' and current_status != 'Finished':
            activate_button = ui.Button(
                style=ButtonStyle.success,
                label="Activate",
                custom_id=f"activate_{plotpoint_id}"
            )
            self.add_item(activate_button)

        if current_status != 'Inactive':
            deactivate_button = ui.Button(
                style=ButtonStyle.secondary,
                label="Deactivate",
                custom_id=f"deactivate_{plotpoint_id}"
            )
            self.add_item(deactivate_button)

        if current_status != 'Finished':
            finish_button = ui.Button(
                style=ButtonStyle.danger,
                label="Mark Finished",
                custom_id=f"finish_{plotpoint_id}"
            )
            self.add_item(finish_button)

        # Always add the delete button
        delete_button = ui.Button(
            style=ButtonStyle.secondary,
            label="❌",
            custom_id=f"delete_{plotpoint_id}"
        )
        self.add_item(delete_button)


# Game Master Selection View
class GameMasterSelectionView(discord.ui.View):
    def __init__(self, plotpoint, channel, user, poll_manager):
        super().__init__(timeout=300)  # 5 minute timeout
        self.plotpoint = plotpoint
        self.channel = channel
        self.activating_user = user
        self.poll_manager = poll_manager
        self.selected_gm = None

        # Add dropdown for GM selection
        self.gm_select = discord.ui.UserSelect(
            placeholder="Wähle eine Spielleitung aus",
            min_values=1,
            max_values=1,
        )
        self.gm_select.callback = self.gm_select_callback
        self.add_item(self.gm_select)

        # "Self" button
        self.self_button = discord.ui.Button(
            label="Ich selbst als Spielleitung",
            style=discord.ButtonStyle.primary
        )
        self.self_button.callback = self.self_button_callback
        self.add_item(self.self_button)

        # Cancel button
        self.cancel_button = discord.ui.Button(
            label="Ohne Spielleitung fortfahren",
            style=discord.ButtonStyle.secondary
        )
        self.cancel_button.callback = self.cancel_button_callback
        self.add_item(self.cancel_button)

    async def gm_select_callback(self, interaction):
        """Handle GM selection from dropdown"""
        self.selected_gm = interaction.data["values"][0]
        selected_user = await interaction.client.fetch_user(int(self.selected_gm))
        await interaction.response.edit_message(
            content=f"Du hast {selected_user.display_name} als Spielleitung ausgewählt. Poll wird erstellt...",
            view=None
        )
        await self.create_poll(interaction)

    async def self_button_callback(self, interaction):
        """Handle self-selection as GM"""
        self.selected_gm = interaction.user.id
        await interaction.response.edit_message(
            content=f"Du übernimmst selbst die Rolle der Spielleitung. Poll wird erstellt...",
            view=None
        )
        await self.create_poll(interaction)

    async def cancel_button_callback(self, interaction):
        """Handle continuing without GM"""
        await interaction.response.edit_message(
            content="Du erstellst die Umfrage ohne festgelegte Spielleitung. Poll wird erstellt...",
            view=None
        )
        await self.create_poll(interaction)

    async def create_poll(self, interaction):
        """Create the poll with the selected game master"""
        try:
            # Create dummy context
            class DummyContext:
                def __init__(self, channel, author):
                    self.channel = channel
                    self.author = author
                    self.guild = channel.guild

                async def send(self, *args, **kwargs):
                    return await self.channel.send(*args, **kwargs)

            dummy_ctx = DummyContext(self.channel, interaction.user)

            # Send poll message to the channel
            # Ensure poll_manager is accessible
            if not self.poll_manager:
                # Add error handling for missing poll_manager
                import shared
                self.poll_manager = shared.poll_manager

                if not self.poll_manager:
                    await self.channel.send(
                        "**ERROR:** Poll manager is not initialized. Please contact an administrator.")
                    return

            # Try to create the poll
            await self.poll_manager.create_poll(
                dummy_ctx,
                self.plotpoint['id'],
                self.plotpoint['title'],
                min_players=2,
                max_players=6,
                game_master_id=self.selected_gm
            )

            # Send helpful message about poll commands
            await self.channel.send(
                "**Terminumfrage wurde erstellt!**\n\n"
                f"{'Spielleiter wurde festgelegt.' if self.selected_gm else 'Kein Spielleiter festgelegt.'}\n"
                "Verfügbare Befehle:\n"
                "- `!suggest_dates YYYY-MM-DD HH:MM` um zusätzliche Terminvorschläge zu machen\n"
                "- `!set_gamemaster @Benutzername` um eine Spielleitung festzulegen oder zu ändern"
            )
        except Exception as e:
            # Better error handling
            import traceback
            print(f"Error creating poll: {e}")
            print(traceback.format_exc())
            await self.channel.send(f"**Fehler beim Erstellen der Terminumfrage**: {e}")

            # Try to provide more diagnostics
            if hasattr(self.poll_manager, 'active_polls'):
                poll_count = len(self.poll_manager.active_polls)
                await self.channel.send(f"Diagnostic info: Poll manager has {poll_count} active polls")


# Confirmation view for delete action
class ConfirmDeleteView(discord.ui.View):
    def __init__(self, plotpoint_id, update_overview_callback, guild):
        super().__init__(timeout=60)  # 1 minute timeout
        self.plotpoint_id = plotpoint_id
        self.update_overview = update_overview_callback
        self.guild = guild

    @discord.ui.button(label="Ja, löschen", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Delete the channel if it exists
        import db
        plotpoint = db.get_plotpoint_by_id(self.plotpoint_id)
        if plotpoint and plotpoint['channel_id']:
            channel = self.guild.get_channel(int(plotpoint['channel_id']))
            if channel:
                await channel.delete(reason=f"Plot point {self.plotpoint_id} gelöscht")

        # Delete the plot point from the database
        if db.delete_plotpoint(self.plotpoint_id):
            await interaction.response.edit_message(
                content=f"Plot Point {self.plotpoint_id} wurde dauerhaft gelöscht!",
                view=None  # Remove the buttons
            )
            # Update the overview
            await self.update_overview(self.guild)
        else:
            await interaction.response.edit_message(
                content=f"Fehler beim Löschen des Plot Points {self.plotpoint_id}.",
                view=None
            )

    @discord.ui.button(label="Abbrechen", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="Löschvorgang abgebrochen.",
            view=None  # Remove the buttons
        )