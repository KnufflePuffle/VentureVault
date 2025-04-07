import re
from discord.ext import commands
import db


def register_commands(bot, update_overview_message):
    """Register all bot commands"""

    @bot.command(name='add_plot_point')
    async def add_plot_point(ctx, plotpoint_id: str, *, rest_of_command: str):
        """
        Add a new plot point to the system
        Format: !add_plot_point <plotpoint_ID> <PLOTTITLE> <Description>
        """
        # Validate plotpoint_ID format (e.g., 01, 02, 03a, 03b, 04, 13, 99)
        if not re.match(r'^(0?[1-9]|[1-9][0-9])[a-z]?$', plotpoint_id):
            await ctx.reply('Invalid plot point ID format. It should be like 01, 02, 03a, 13, 27b, up to 99.')
            return

        # Split the rest into title (all caps) and description
        parts = rest_of_command.split(' ')
        if len(parts) < 2:
            await ctx.reply('Invalid format. Use `!add_plot_point <plotpoint_ID> <PLOTTITLE> <Description>`')
            return

        title_part = parts[0]
        description_start_idx = 1

        # Keep adding words to the title as long as they're all uppercase
        while (description_start_idx < len(parts) and
               parts[description_start_idx].isupper() and
               parts[description_start_idx].strip()):
            title_part += f" {parts[description_start_idx]}"
            description_start_idx += 1

        if description_start_idx >= len(parts):
            # No description provided or all words are uppercase
            await ctx.reply('Please provide a description after your all-caps title.')
            return

        title = title_part
        description = ' '.join(parts[description_start_idx:])

        # Ensure title is all uppercase
        if not title.isupper():
            await ctx.reply('The plot title must be in ALL CAPS.')
            return

        # Check if this ID already exists in the database
        if db.plotpoint_exists(plotpoint_id):
            await ctx.reply(f'A plot point with ID {plotpoint_id} already exists.')
            return

        # Insert new plotpoint
        if db.add_plot_point(plotpoint_id, title, description):
            await ctx.reply(f'Plot Point {plotpoint_id}: {title} has been added successfully!')

            # Update the overview message
            await update_overview_message(ctx.guild)
        else:
            await ctx.reply('An error occurred while adding the plot point. Check database connection.')

    @bot.command(name='create_poll')
    async def create_poll(ctx, plot_point_id: str, min_players: int = 2, max_players: int = 6):
        """
        Erstelle eine Terminumfrage für einen Plot Point
        Format: !create_poll <plot_point_ID> [min_spieler=2] [max_spieler=6]
        """
        # Hole Plot-Point-Daten aus der Datenbank
        plotpoint = db.get_plotpoint_by_id(plot_point_id)

        if not plotpoint:
            await ctx.reply(f'Plot Point mit ID {plot_point_id} nicht gefunden.')
            return

        # Prüfe Bereichsgrenzen für Spielerzahlen
        if min_players < 1:
            min_players = 1
        if max_players < min_players:
            max_players = min_players
        if max_players > 10:
            max_players = 10

        # Erstelle die Umfrage im aktuellen Kanal
        from poll import poll_manager
        await poll_manager.create_poll(
            ctx,
            plotpoint['id'],
            plotpoint['title'],
            min_players=min_players,
            max_players=max_players,
            game_master_id=ctx.author.id
        )

    @bot.command(name='set_gamemaster')
    async def set_gamemaster(ctx, user: discord.Member):
        """
        Setzt einen Spieler als Spielleiter für die aktuelle Terminumfrage
        Format: !set_gamemaster @Benutzername
        """
        # Prüfe, ob es eine aktive Umfrage gibt
        from poll import poll_manager

        if ctx.channel.id not in poll_manager.active_polls:
            await ctx.reply("Es gibt keine aktive Terminumfrage in diesem Kanal.")
            return

        # Prüfe Berechtigung (nur der Ersteller oder Admin)
        poll_data = poll_manager.active_polls[ctx.channel.id]
        is_creator = poll_data.get("created_by") == ctx.author.id
        is_admin = ctx.author.guild_permissions.administrator

        if not (is_creator or is_admin):
            await ctx.reply("Nur der Ersteller der Umfrage oder ein Admin kann den Spielleiter ändern.")
            return

        # Setze den neuen Spielleiter
        poll_data["game_master_id"] = user.id

        # Aktualisiere die Umfrage
        await poll_manager.update_poll(ctx.channel.id)

        await ctx.reply(f"{user.mention} wurde als Spielleiter:in festgelegt.")

    @bot.command(name='suggest_dates')
    async def suggest_dates(ctx, *dates):
        """
        Fügt Terminvorschläge zur aktuellen Umfrage hinzu
        Format: !suggest_dates YYYY-MM-DD HH:MM [YYYY-MM-DD HH:MM ...]
        Beispiel: !suggest_dates 2025-05-01 19:00 2025-05-02 20:00
        """
        from poll import poll_manager

        if ctx.channel.id not in poll_manager.active_polls:
            await ctx.reply("Es gibt keine aktive Terminumfrage in diesem Kanal.")
            return

        # Prüfe Berechtigung
        poll_data = poll_manager.active_polls[ctx.channel.id]
        is_creator = poll_data.get("created_by") == ctx.author.id
        is_gm = poll_data.get("game_master_id") == ctx.author.id
        is_admin = ctx.author.guild_permissions.administrator

        if not (is_creator or is_gm or is_admin):
            await ctx.reply("Nur der Ersteller, der Spielleiter oder ein Admin kann Termine vorschlagen.")
            return

        # Verarbeite die Datumsangaben (Format: YYYY-MM-DD HH:MM)
        new_dates = []
        i = 0
        while i < len(dates):
            if i + 1 < len(dates):
                try:
                    date_str = f"{dates[i]} {dates[i + 1]}"
                    date = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                    new_dates.append(date)
                    i += 2
                except ValueError:
                    await ctx.reply(
                        f"Ungültiges Datumsformat: {dates[i]} {dates[i + 1]}. Bitte verwende YYYY-MM-DD HH:MM")
                    return
            else:
                await ctx.reply("Fehlende Zeitangabe. Bitte gib Datum und Uhrzeit an.")
                return

        # Füge die neuen Termine hinzu
        if new_dates:
            poll_data["suggested_dates"].extend(new_dates)

    @bot.command(name='help_lfg')
    async def help_lfg(ctx):
        """Display help information for the LFG bot commands"""
        help_text = """
        
        
# Plot Point LFG Bot Commands

**!add_plot_point <ID> <TITLE> <Description>**
Add a new plot point to the system.
- ID: Must be in format like 01, 02, 03a, 13, 27b, etc. (1-99 with optional letter)
- TITLE: Must be ALL CAPS
- Description: Regular text describing the plot point

**!help_lfg**
Show this help message.

# Examples:
`!add_plot_point 01 THE BEGINNING This is where our adventure begins...`
`!add_plot_point 13a SIDE QUEST This optional quest involves finding the lost artifact.`

# Status Management:
Use the buttons in the Plot-Point-Overview channel to:
- Activate a plot point (creates a dedicated channel)
- Deactivate a plot point (removes the channel)
- Mark a plot point as finished (removes the channel)
        """
        await ctx.send(help_text)

