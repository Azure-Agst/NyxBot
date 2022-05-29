import os
import glob
import sqlite3
import difflib
from tinytag import TinyTag

from .env import env, DB_NAME

_db_conn = None

def _init_db_conn():
    """Initializes the DB Connection"""

    # initialize connection
    global _db_conn
    _db_conn = sqlite3.connect(
        os.path.join(env.config_path, DB_NAME)
    )
    _db_conn.row_factory = sqlite3.Row

def validate_config():
    """Verifies configs are valid, and initializes them if needed"""

    # check to make sure config exists
    db_path = os.path.join(env.config_path, DB_NAME)
    if not os.path.exists(db_path):
        print("Config not found. Creating...")
        _init_db()

    # initialize connection
    _init_db_conn()

def _get_db_conn():
    """Makes a connection to the database"""

    # connect to database
    global _db_conn
    if _db_conn is None:
        _init_db_conn()
    return _db_conn

def _init_db():
    """Initializes the DB"""

    # connect to database
    with _get_db_conn() as conn:

        # create tables
        conn.execute('''CREATE TABLE "library" (
            "id"	    INTEGER NOT NULL,
            "title"	    TEXT,
            "artist"	TEXT,
            "album"	    TEXT,
            "tracknum"	INTEGER,
            "discnum"	INTEGER,
            "path"	    TEXT,
            PRIMARY KEY("id" AUTOINCREMENT)
        );''')

        # commit changes
        conn.commit()

async def poll_new_files(path: str = env.music_path):
    """
    Gets difference of cached files and current files, then adds new files
    Returns: Number of files added
    """

    # variable declarations
    files_changed = 0

    # step 1: get set of files from database
    with _get_db_conn() as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT path 
                FROM library
                WHERE lower(path) LIKE ?;
            ''', 
            (str(path + "%"),)
        )
        rows = cur.fetchall()
    old_files = set([row['path'] for row in rows])
    
    # step 2: get set of files from filesystem
    new_files = set()
    for entry in os.scandir(path):

        # skip extended attributes and recycle bin; synology thing
        if "@eaDir" in entry.name or "$RECYCLE.BIN" in entry.name:
            continue

        # if directory, step into it
        if entry.is_dir():
            files_changed += await poll_new_files(entry.path)

        # if file, add to set
        if entry.is_file(): 
            filename = os.path.basename(entry.path)
            if filename.lower().endswith(".mp3") or \
                filename.lower().endswith(".flac") or \
                filename.lower().endswith(".wav"):
                new_files.add(entry.path)

    # step 3: find new files
    to_be_added = new_files - old_files

    # step 4: add new files to database
    if len(to_be_added) > 0:
        await add_files_to_db(to_be_added)
        return len(to_be_added) + files_changed
    else:
        #print("No new files found.", path)
        return 0

async def add_files_to_db(file_list):
    """Iterates thru lists and adds file to db"""

    # connect to database
    with _get_db_conn() as conn:

        # iterate files
        for file in file_list:

            # get file info
            tag = TinyTag.get(file)

            # insert file info
            conn.execute('''INSERT INTO library(title, artist, album, tracknum, discnum, path)
                VALUES(?, ?, ?, ?, ?, ?)''',
                (
                    tag.title,
                    tag.artist,
                    tag.album,
                    tag.track,
                    tag.disc,
                    file
                )
            )

        # commit changes
        conn.commit()

def search_db(query: str):
    """Searches Database"""

    # connect to database
    with _get_db_conn() as conn:

        # get results
        cur = conn.cursor()
        cur.execute('''
        SELECT * FROM library WHERE lower(title) LIKE ?;
        ''',
            (
                '%' + query.lower() + '%',
            )
        )

        # sort results
        results = [dict(row) for row in cur.fetchall()]
        results.sort(
            key=lambda x: difflib.SequenceMatcher(
                None, query.lower(), 
                x['title'].lower()
            ).ratio(), 
            reverse=True
        )

        # return results
        return results[:9]
