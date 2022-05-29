import os
import sys
import logging

from .env import env
from .discord import bot
from .db import validate_config

def main():
    """Main function"""

    # set up logging
    if not os.path.exists(env.config_path):
        os.makedirs(env.config_path)

    # configure logging basics for file
    logging.basicConfig(
        format="%(asctime)s %(name)-20s %(levelname)s: %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
        level=logging.INFO,
        filename=os.path.join(env.config_path, "music.log")
    )

    # configure logging basics for console
    logging.getLogger().addHandler(logging.StreamHandler())
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.WARNING)

    # add console handler to logger
    logging.getLogger().addHandler(console)

    # initialize bot
    logging.getLogger('NyxBot.main').info("Starting up...")

    # check config
    validate_config()

    # start bot
    bot.run(env.token)

if __name__ == "__main__":
    exit(main())