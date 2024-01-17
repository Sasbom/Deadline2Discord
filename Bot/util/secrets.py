import os
import json
import sys

# meta class keeping track of instances
class SingletonMetaClass(type):
    _instances = {}

    def __call__(cls,*args,**kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]
    
class Secrets(metaclass=SingletonMetaClass):

    bot_token: str = None
    channel: int = None
    guild: int = None
    deadline_port: int = None
    internal_http_port: int = None

    def __init__(self,path:str):
        if os.path.exists(path):
            with open(path,"r") as f:
                data = json.load(f)
                self.bot_token = data["bot_token"]
                self.channel = data["dedicated_channel_id"]
                self.guild = int(data["guild_id"])
                self.deadline_port = data["deadline_webserver_port"]
                self.internal_http_port = data["internal_http_port"]
            print("Succesfully read secrets...")
        else:
            with open(path,"w") as f:
                data = {"bot_token" : "aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ123456789123456789.a",
                        "guild_id" : 123456789123456789,
                        "dedicated_channel_id" : 123456789123456789,
                        "deadline_webserver_port" : 8081,
                        "internal_http_port" : 1337
                        }
                json.dump(data,f,indent="  ")
                print(f"Created {os.path.abspath(path)}, please fill it out with the right data!")
            sys.exit(0)

        
Secret = Secrets(f"{__file__}/../../secrets.json")