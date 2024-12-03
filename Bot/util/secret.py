import json
import os
import sys

from .singleton import SingletonMetaClass

# PG_USER=sas
# PG_PWD=sasword
# PG_DB=hku
# PG_ADMIN_MAIL="sas.vangulik@hku.nl"
# PG_ADMIN_PWD="pgadmin"


class Secrets(metaclass=SingletonMetaClass):
    bot_token: str = None
    channel: int = None
    guild: int = None
    deadline_port: int = None
    internal_http_port: int = None
    pg_user: str = None
    pg_password: str = None
    pg_database: str = None
    pg_schema: str = None
    pg_address: str = None
    pg_port: int = None
    dropbox_oauth2_accesstoken: str = None
    dropbox_refresh_token: str = None
    dropbox_app_key: str = None
    dropbox_app_secret: str = None

    def __init__(self, path: str):
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
                self.bot_token = data["bot_token"]
                self.channel = data["dedicated_channel_id"]
                self.guild = int(data["guild_id"])
                self.deadline_port = data["deadline_webserver_port"]
                self.internal_http_port = data["internal_http_port"]
                self.pg_user = data["pg_user"]
                self.pg_password = data["pg_password"]
                self.pg_database = data["pg_database"]
                self.pg_schema = data["pg_schema"]
                self.pg_address = data["pg_address"]
                self.pg_port = data["pg_port"]
                self.dropbox_refresh_token = data["dropbox_refresh_token"]
                self.dropbox_app_key = data["dropbox_app_key"]
                self.dropbox_app_secret = data["dropbox_app_secret"]
            print("Succesfully read secrets...")
        else:
            with open(path, "w") as f:
                data = {
                    "bot_token": "aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ123456789123456789.a",
                    "guild_id": 123456789123456789,
                    "dedicated_channel_id": 123456789123456789,
                    "deadline_webserver_port": 8081,
                    "internal_http_port": 1337,
                    "pg_user": "postgres",
                    "pg_password": "postgres",
                    "pg_database": "postgres",
                    "pg_schema": "bot",
                    "pg_address": "localhost",
                    "pg_port": 5432,
                    "dropbox_refresh_token": "",
                    "dropbox_app_key": "",
                    "dropbox_app_secret": ""
                }
                json.dump(data, f, indent="  ")
                print(
                    f"Created {os.path.abspath(path)}, please fill it out with the right data!"
                )
            sys.exit(0)


Secret = Secrets(f"{__file__}/../../secrets.json")
