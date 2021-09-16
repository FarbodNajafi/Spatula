import enum
import json
import os


def get_mode():
    return os.environ.get('MODE')


def get_prefix():
    return os.environ.get('PREFIX')


class BotModes(enum.Enum):
    LIVE = 'spatula'
    DEV = 'shadow_spatula'
    NIGHTLY = 'spooky_urf'
    FEATURE = 'spooky_gangplank'
