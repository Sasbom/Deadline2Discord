from tinydb import TinyDB
from .singleton import SingletonMetaClass

class DB_holder(metaclass=SingletonMetaClass):
    def __init__(self):
        path = f"{__file__}/../../register.db"
        self._DB = TinyDB(path)
    
    @property
    def DB(self):
        return self._DB
    
holder = DB_holder()
DB: TinyDB = holder.DB