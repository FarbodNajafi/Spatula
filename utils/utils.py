import enum
import json
import os


def get_mode():
    return os.environ.get('MODE')


def get_prefix():
    with open('prefixes.json', 'r') as f:
        prefix = json.load(f)

    return prefix[(get_mode())]


class BotModes(enum.Enum):
    SHADOW = 'shadow_spatula'
    LIVE = 'spatula'
    DEV = 'spatula_dev'
