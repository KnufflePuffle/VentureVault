# Add this to a new file called plot_vote.py

import discord
from discord import SelectOption, ButtonStyle
import db
import datetime

# Store active votes: channel_id -> vote_data
active_votes = {}


class PlotVotingView(discord.ui.View):
    def __init__(self, inactive_plots, vote_duration=48):
        super().__init__(timeout=None)  # No timeout for the vote view
        self.inactive_plots = inactive_plots
        self.vote_duration = vote_duration
        self.end_time = datetime.datetime.now() + datetime.timedelta(hours=vote_duration)

        # Add vote selection
        self._add_vote_select()

    def _add_vote_select(self):
        """Add a dropdown with inactive plots"""
        options = []

        for plot in self.inactive_plots:
            # Create a shortened description for the dropdown
            short_desc = plot['description'][:80] + "..." if len(plot['description']) > 80 else plot['description']

            options.append(SelectOption(
                label=f"{plot['id']}: {plot['title']}",
                value=plot['id'],
                description=short_desc
            ))

        # Split into groups of 25 if needed (Discord limit)
        for i in range(0, len(options), 25):
            select_options = options[i:i + 25]

            select = discord.ui.Select(
                placeholder="Wähle einen Plot Point",
                min_values=1,
                max_values=1,
                options=select_options,
                custom_id=f"plot_vote_select_{i}"
            )
            select.callback = self.vote_callback
            self.add_item(select)

    async def vote_callback(self, interaction):
        """Handle voting"""
        selected_plot_id = interaction.data["values"][0]
        channel_id = interaction.channel.id

        if channel_id not in active_votes:
            await interaction.response.send_message(
                "Diese Abstimmung ist nicht mehr aktiv.",
                ephemeral=True
            )
            return

        vote_data = active_votes[channel_id]
        user_id = interaction.user.id

        # Record the vote
        vote_data["votes"][user_id] = selected_plot_id

        # Update the vote count
        await update_vote_results(interaction.channel, vote_data)

        await interaction.response.send_message(
            f"Du hast für Plot Point {selected_plot_id} gestimmt.",
            ephemeral=True
        )


class EndVoteButton(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label="Abstimmung beenden", style=ButtonStyle.danger)
    async def end_vote_button(self, interaction, button):
        """End the vote early"""
        if self.channel_id not in active_votes:
            await interaction.response.send_message(
                "Diese Abstimmung ist bereits beendet.",
                ephemeral=True
            )
            return

        # End the vote
        await end_vote(interaction.channel, active_votes[self.channel_id], forced=True)
        await interaction.response.send_message(
            "Die Abstimmung wurde vorzeitig beendet.",
            ephemeral=True
        )


async def create_plot_vote(channel, duration=48):
    """Create a new vote for inactive plot points"""
    # Check if there's already an active vote in this channel
    if channel.id in active_votes:
        return False, "Es läuft bereits eine Abstimmung in diesem Kanal."

    # Get inactive plot points
    inactive_plots = [p for p in db.get_plotpoints() if p['status'] == 'Inactive']

    if not inactive_plots:
        return False, "Es gibt keine inaktiven Plot Points für eine Abstimmung."

    # Create vote data
    vote_data = {
        "start_time": datetime.datetime.now(),
        "end_time": datetime.datetime.now() + datetime.timedelta(hours=duration),
        "inactive_plots": inactive_plots,
        "votes": {},  # user_id -> plot_id
        "result_message_id": None
    }

    # Create the vote message
    embed = discord.Embed(
        title="📊 Plot Point Abstimmung",
        description=f"Stimme ab, welcher Plot Point als nächstes aktiviert werden soll!\n"
                    f"Die Abstimmung endet <t:{int(vote_data['end_time'].timestamp())}:R>.",
        color=discord.Color.gold()
    )

    # Add fields for each plot
    for plot in inactive_plots:
        embed.add_field(
            name=f"{plot['id']}: {plot['title']}",
            value=plot['description'][:200] + ("..." if len(plot['description']) > 200 else ""),
            inline=False
        )

    # Add voting view
    view = PlotVotingView(inactive_plots, duration)

    # Send the message
    message = await channel.send(embed=embed, view=view)

    # Create results message
    results_embed = discord.Embed(
        title="📊 Aktuelle Abstimmungsergebnisse",
        description="Hier sind die aktuellen Ergebnisse der Plot Point Abstimmung:",
        color=discord.Color.blue()
    )

    result_message = await channel.send(embed=results_embed)
    vote_data["result_message_id"] = result_message.id

    # Add admin controls
    admin_message = await channel.send(
        "Es haben alle abgestimmt:",
        view=EndVoteButton(channel.id)
    )

    # Store the vote
    active_votes[channel.id] = vote_data

    # Schedule end of vote
    import asyncio
    seconds_until_end = (vote_data["end_time"] - datetime.datetime.now()).total_seconds()
    if seconds_until_end > 0:
        asyncio.create_task(schedule_end_vote(channel, vote_data, seconds_until_end))

    # Update initial results
    await update_vote_results(channel, vote_data)

    return True, f"Abstimmung für {len(inactive_plots)} inaktive Plot Points wurde gestartet!"


async def update_vote_results(channel, vote_data):
    """Update the vote results message"""
    if "result_message_id" not in vote_data:
        return

    try:
        # Get the message
        message = await channel.fetch_message(vote_data["result_message_id"])

        # Count votes
        vote_counts = {}
        for plot in vote_data["inactive_plots"]:
            vote_counts[plot["id"]] = 0

        for user_id, plot_id in vote_data["votes"].items():
            if plot_id in vote_counts:
                vote_counts[plot_id] += 1

        # Sort by vote count (descending)
        sorted_votes = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)

        # Create results embed
        results_embed = discord.Embed(
            title="📊 Aktuelle Abstimmungsergebnisse",
            description=f"Hier sind die aktuellen Ergebnisse der Plot Point Abstimmung:\n"
                        f"Insgesamt haben {len(vote_data['votes'])} Spieler:innen abgestimmt.",
            color=discord.Color.blue()
        )

        # Add fields for results
        for plot_id, count in sorted_votes:
            # Find the plot title
            plot_title = next((p["title"] for p in vote_data["inactive_plots"] if p["id"] == plot_id), "Unbekannt")

            # Add bar graph visualization
            total_votes = len(vote_data["votes"])
            percentage = (count / total_votes * 100) if total_votes > 0 else 0
            bar_length = int(percentage / 10) if percentage > 0 else 0
            bar = "█" * bar_length + "░" * (10 - bar_length)

            results_embed.add_field(
                name=f"{plot_id}: {plot_title}",
                value=f"{bar} {count} Stimmen ({percentage:.1f}%)",
                inline=False
            )

        # Update the end time
        results_embed.set_footer(text=f"Abstimmung endet am {vote_data['end_time'].strftime('%d.%m.%Y um %H:%M Uhr')}")

        # Update the message
        await message.edit(embed=results_embed)
    except Exception as e:
        print(f"Error updating vote results: {e}")


async def schedule_end_vote(channel, vote_data, seconds):
    """Schedule the end of a vote after the specified seconds"""
    try:
        import asyncio
        await asyncio.sleep(seconds)
        # Check if the vote is still active
        if channel.id in active_votes and active_votes[channel.id] == vote_data:
            await end_vote(channel, vote_data)
    except Exception as e:
        print(f"Error in schedule_end_vote: {e}")


async def end_vote(channel, vote_data, forced=False):
    """End a vote and announce the results"""
    try:
        # Remove from active votes
        if channel.id in active_votes:
            del active_votes[channel.id]

        # Count final votes
        vote_counts = {}
        for plot in vote_data["inactive_plots"]:
            vote_counts[plot["id"]] = 0

        for user_id, plot_id in vote_data["votes"].items():
            if plot_id in vote_counts:
                vote_counts[plot_id] += 1

        # Find the winner(s)
        max_votes = 0
        winners = []

        for plot_id, count in vote_counts.items():
            if count > max_votes:
                max_votes = count
                winners = [plot_id]
            elif count == max_votes:
                winners.append(plot_id)

        # Create results announcement
        if not vote_data["votes"]:
            # No votes
            announcement = "Die Abstimmung ist beendet, aber niemand hat abgestimmt!"
        elif len(winners) == 1:
            # Clear winner
            winner_id = winners[0]
            winner_plot = next((p for p in vote_data["inactive_plots"] if p["id"] == winner_id), None)

            if winner_plot:
                announcement = (
                    f"## 🏆 Die Abstimmung ist beendet!\n\n"
                    f"**{winner_plot['id']}: {winner_plot['title']}** hat mit **{max_votes}** Stimmen gewonnen!\n\n"
                    f"*{winner_plot['description']}*\n\n"
                   # f"Administ diesen Plot Point jetzt aktivieren."
                )
            else:
                announcement = f"Die Abstimmung ist beendet. Plot Point {winner_id} hat gewonnen."
        else:
            # Tie
            winner_plots = [next((p for p in vote_data["inactive_plots"] if p["id"] == w_id), None) for w_id in winners]
            winner_plots = [p for p in winner_plots if p]  # Filter out None

            winners_text = ", ".join([f"**{p['id']}: {p['title']}**" for p in winner_plots])

            announcement = (
                f"## 🏆 Die Abstimmung ist beendet!\n\n"
                f"Es gibt ein Unentschieden mit **{max_votes}** Stimmen zwischen:\n"
                f"{winners_text}\n\n"
                f"Es muss anders entschieden werden, welche Plot Point bespielt wird."
            )

        # Send the announcement
        end_reason = "vorzeitig beendet" if forced else "beendet"
        await channel.send(f"# 📊 Die Abstimmung wurde {end_reason}!\n{announcement}")

        return True
    except Exception as e:
        print(f"Error ending vote: {e}")
        return False