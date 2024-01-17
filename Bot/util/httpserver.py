from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import parse
import json
import socket
import threading
import time

import discord
from tinydb import Query

from . import secret
from .message_cache import MESSAGES
from .database import DB

SECRET = secret.Secret

def compose_resultembed(data_dict : dict[str,str]) -> tuple[discord.Embed, str, discord.File, str]:
    has_failed = data_dict["status"] == "Failed"
    
    msg_color = discord.Colour.from_rgb(255,0,0) if has_failed else discord.Colour.from_rgb(0,255,0)
    embed_title = "Job Failed! :fire::fire::fire:" if has_failed else "Job Finished!"
    embed_title_emote = ":fire:" if has_failed else ":white_check_mark:" 
    embed_title = f"`{data_dict['name']}`{embed_title_emote}\n{embed_title}"

    embed_description = f"The farm has {data_dict['status'].lower()} job `{data_dict['name']}`."
    
    embed = discord.Embed(title=embed_title,color=msg_color,description=embed_description)
    
    embed.add_field(name=":abcd: Name: ", value=data_dict["name"])
    embed.add_field(name=":ocean: Pool: ", value=data_dict["pool"])

    if "department" not in data_dict.keys():
        data_dict["department"] = "[no department]"
    
    embed.add_field(name=":classical_building: Department: ", value=data_dict["department"],inline=False)
    embed.add_field(name=":pray: Status: ", value=data_dict["status"])
    embed.add_field(name=":1234: Tasks: ", value=data_dict["tasks"])
    embed.add_field(name=":calendar: Time finished:", value = get_timestamp_now())
    
    user_id = None
    tag_message = None
    if "ping" in data_dict.keys():
        if names := data_dict["ping"]:
            user = Query()
            
            # set comprehension for unique names
            name_list = {n.strip() for n in names.split(",")}
            user_ids = []
            for name in name_list:
                if user_id := DB.get(user.name == name):
                    user_ids.append(user_id)
                
            if user_ids:
                users = ", ".join(f"<@{user_id['id']}>" for user_id in user_ids)
                emote = "⚠" if data_dict["status"] == "Failed" else "🍳"
                embed.add_field(name=":speaking_head: User(s): ", value=users,inline=False)
                tag_message = f"{emote} Render {data_dict['status']}! {users}"


    file = None
    filename = None
    if "thumbnail" in data_dict.keys() and not has_failed:
        filename = data_dict["thumbnail"]
        file = discord.File(filename)

    return embed, tag_message, file, filename


def get_timestamp_now() -> str:
    return f"<t:{int(time.time())}:f>"


class RequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        data = self.rfile.read(length).decode()
        data_dict = parse.parse_qs(data)

        self.send_response(200)
        
        self.send_header("Content-type","application/json")
        self.end_headers()
        
        if "message" in data_dict.keys():
            print(f"Recieved message: {data_dict['message'][0]}")
            self.wfile.write(json.dumps({"message" : f"Message recieved: {data_dict['message'][0]}"}).encode())

            job_name = data_dict["name"][0]
            job_id = data_dict["id"][0]
            job_owner = data_dict["owner"][0]
            job_time = "0"
            if "time" in data_dict.keys():
                job_time = data_dict["time"][0]

            job = Query()
            job_info = DB.get(job.job_name == job_name)
            if not job_info:
                DB.insert({"job_name": f"{job_name}", "job_id" : f"{job_id}", "job_owner" : f"{job_owner}", "job_time" : f"{job_time}"})
            else:
                DB.update({"job_id" : f"{job_id}" },job.job_name == job_name)

                if job_time != "0":
                    DB.update({"job_time" : f"{job_time}"},job.job_name == job_name)

            
            MESSAGES.post_message(f"{data_dict['message'][0]} - :calendar:{get_timestamp_now()}")
        else:
            data_dict = {k : v[0] for k, v in data_dict.items()} # get first of all.
            embed, tag_txt, file, filename = compose_resultembed(data_dict=data_dict)
            
            embed_msg = tag_msg = pic_msg = label_msg = None
            
            embed_msg = MESSAGES.create_message(embed)
            
            if file:
                pic_msg = MESSAGES.create_message(file)
                label_msg = MESSAGES.create_message(f":frame_photo: `{filename}`")
            
            if tag_txt:
                tag_msg = MESSAGES.create_message(tag_txt)
                
            order = (tag_msg, pic_msg, label_msg)

            last_msg = embed_msg
            for m in order:
                if m is not None:
                    last_msg.then(m)
                    last_msg = m

            MESSAGES.post_message(embed_msg)


IP = socket.gethostbyname(socket.gethostname())

SERVER = ThreadingHTTPServer((IP,SECRET.internal_http_port),RequestHandler)

def run_server():
    SERVER.serve_forever()

THREAD = threading.Thread(target=run_server)

class DeadlineHTTPCatcher:
    def __init__(self):
        self.IP = IP

    def __enter__(self) -> ThreadingHTTPServer:
        THREAD.start()
        return SERVER
    
    def __exit__(self,*args):
        SERVER.shutdown()
        THREAD.join()