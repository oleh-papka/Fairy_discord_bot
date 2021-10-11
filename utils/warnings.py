from discord import Embed, Color

from config import BOT_PREFIX, OWNER_NAME

def create_warning_embed(warning_msg):
    embed = Embed(
        colour=Color.orange(),
        title='⚠️   What happend?!',
        description=warning_msg+f"\n\nNeed help? Use -'{BOT_PREFIX}help' to get more info."
    )

    return embed


def create_error_embed(error_msg):
    embed = Embed(
        colour=Color.red(),
        title='🛑  ERROR!!!',
        description=error_msg+f'\n\nWould you be so kind to open issue about this.\n\nThanks! ~{OWNER_NAME}',
        url='https://youtu.be/dQw4w9WgXcQ'
    )

    return embed
