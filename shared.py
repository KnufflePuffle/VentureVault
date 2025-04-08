poll_manager = None
bot = None

def init_poll_manager(bot_instance):
    """Initialize the poll manager with the bot instance"""
    from poll import GameSessionPoll
    global poll_manager, bot
    bot = bot_instance
    poll_manager = GameSessionPoll(bot)
    return poll_manager

def get_poll_manager():
    """Get the poll manager instance"""
    global poll_manager
    return poll_manager