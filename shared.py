poll_manager = None

def init_poll_manager(bot):
    from poll import GameSessionPoll
    global poll_manager
    poll_manager = GameSessionPoll(bot)