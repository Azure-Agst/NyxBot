import os
import sys

from .env import env
from .discord import bot
from .db import validate_config

def main():
    """Main function"""

    print("Starting Music Player...")

    # check config
    validate_config()

    # start bot
    bot.run(env.token)

if __name__ == "__main__":
    exit(main())