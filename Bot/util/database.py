from psycopg2.extensions import connection

from .pg import postgrease
from .singleton import SingletonMetaClass


class DB_holder(metaclass=SingletonMetaClass):
    def __init__(self):
        self._DB = postgrease.connect()

    @property
    def DB(self):
        return self._DB


holder = DB_holder()
DB: connection = holder.DB
