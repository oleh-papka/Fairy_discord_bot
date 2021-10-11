from discord.ext.commands import CommandError


class IncorrectVoiceChannel(CommandError):
    pass

class NotConnected(CommandError):
    pass
