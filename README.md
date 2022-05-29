# Nyx Music Bot (NyxBot)

Bot to play Music from my NAS, called Nyx!

## Commands

- `>join` - joins a channel, or moves if already in one
- `>leave` - leaves a channel, if in one
- `>play` - joins user's channel if not already in one, then plays a song
- `>stop` - pauses a song, if playing one
- `>stop` - stops a song, if playing one
- `>search` - search the library and print results
- `>volume` - change volume (default is 20%)

## Env Vars

- `CONFIG_PATH` - Location of config on image, defaults to `/var/lib/nyxbot`
- `MUSIC_PATH` - Location of mounted music library, defaults to `/mnt/music`
- `DISCORD_TOKEN` - Discord Bot Token
- `DISCORD_CHANNEL` - Bot Spam Channel ID

## Required Mounts

- `/mnt/music`: Your Music Library
  - SMB or NFS works here, although I recommend NFS
- `/var/lib/nyxbot`: Config Storage
