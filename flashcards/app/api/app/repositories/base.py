import sqlite3


class BaseRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

