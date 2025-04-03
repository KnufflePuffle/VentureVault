from discord import ButtonStyle, ui


# Status buttons
class PlotpointButtons(ui.View):
    def __init__(self, plotpoint_id, current_status):
        super().__init__(timeout=None)
        self.plotpoint_id = plotpoint_id

        # Add appropriate buttons based on current status
        if current_status != 'Active':
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
