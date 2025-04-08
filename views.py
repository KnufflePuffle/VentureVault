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
        super().__init__(timeout=300)  # 5 Minuten Timeout
        self.plotpoint = plotpoint
        self.channel = channel
        self.activating_user = user
        self.poll_manager = poll_manager
        self.selected_gm = None

        # Füge ein Dropdown für Spielleiter-Auswahl hinzu
        self.gm_select = discord.ui.UserSelect(
            placeholder="Wähle eine Spielleitung aus",
            min_values=1,
            max_values=1,
        )
        self.gm_select.callback = self.gm_select_callback
        self.add_item(self.gm_select)

        # Oder-Button für "Ich selbst"
        self.self_button = discord.ui.Button(
            label="Ich selbst als Spielleitung",
            style=discord.ButtonStyle.primary
        )
        self.self_button.callback = self.self_button_callback
        self.add_item(self.self_button)

        # Abbrechen-Button
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

        # Create dummy context
        class DummyContext:
            def __init__(self, channel, author):
                self.channel = channel
                self.author = author
                self.guild = channel.guild

            async def send(self, *args, **kwargs):
                return await self.channel.send(*args, **kwargs)  # Hier 'self.channel' statt 'channel'

        dummy_ctx = DummyContext(self.channel, interaction.user)

        try:
            # Send poll message to the channel
            await self.poll_manager.create_poll(
                dummy_ctx,
                self.plotpoint['id'],
                self.plotpoint['title'],
                min_players=2,
                max_players=6,
                game_master_id=self.selected_gm
            )

            # Send a helpful message about poll commands
            await self.channel.send(
                "**Terminumfrage wurde erstellt!**\n\n"
                f"{'Spielleiter wurde festgelegt.' if self.selected_gm else 'Kein Spielleiter festgelegt.'}\n"
                "Verfügbare Befehle:\n"
                "- `!suggest_dates YYYY-MM-DD HH:MM` um zusätzliche Terminvorschläge zu machen\n"
                "- `!set_gamemaster @Benutzername` um eine Spielleitung festzulegen oder zu ändern"
            )
        except Exception as e:
            # Fehlerbehandlung
            print(f"Fehler beim Erstellen der Umfrage: {e}")
            await self.channel.send(f"**Fehler beim Erstellen der Terminumfrage**: {e}")