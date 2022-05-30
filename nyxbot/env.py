import os
from dotenv import load_dotenv

DB_NAME = 'nyx_music.db'
CONFIG_MOUNT_PATH = '/var/lib/nyxbot'
MUSIC_MOUNT_PATH = '/mnt/music'

class EnvDict():
    """Class used for representing environment variables."""

    def __repr__(self):
        return f"{self.__class__.__name__}{self.__dict__}"

    def __init__(self):
        """Read in env vars"""
        
        # read in dotenv, if exists
        load_dotenv()

        # config path
        _env_config = os.getenv('CONFIG_PATH')
        self.config_path = _env_config if _env_config else CONFIG_MOUNT_PATH

        # music path
        _env_music = os.getenv('MUSIC_PATH')
        self.music_path = _env_music if _env_music else MUSIC_MOUNT_PATH

        # discord token
        self.token = os.getenv('DISCORD_TOKEN')

        # discord admin channel
        self.admin_channel = os.getenv('DISCORD_CHANNEL')
        self.admin_channel = int(self.admin_channel) \
            if self.admin_channel.isnumeric() else None

        # first run
        self.first_run = not os.path.exists(
            os.path.join(self.config_path, DB_NAME)
        )

env = EnvDict()
