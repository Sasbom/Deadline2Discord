from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from urllib import parse
import sys
import json
import socket
import threading
import asyncio

import discord
from discord import app_commands
from tinydb import TinyDB, Query

IP = socket.gethostbyname(socket.gethostname())

DB = TinyDB(f"{__file__}/../register.db")

class MessageCache:

    class MessageContent:
        def __init__(self, message: str = "", embed: discord.Embed = None, file: discord.File = None, followup = None):
            self._message = message
            self._embed = embed
            self._file = file
            self._followup = followup

        async def send_to_channel(self, channel: discord.TextChannel):
            args, kwargs = self._compose_args()
            await channel.send(*args, **kwargs)
            if self._followup and isinstance(self._followup,MessageCache.MessageContent):
                await self._followup.send_to_channel(channel)

        def create_async_task(self, channel: discord.TextChannel):
            return asyncio.create_task(self.send_to_channel(channel))
            
        def _compose_args(self) -> tuple[list, dict]:
            args = [self._message] if self._message else []
            kwargs = {}
            if self._embed is not None:
                kwargs.update({"embed" : self._embed})
            if self._file is not None:
                kwargs.update({"file" : self._file})
            return args, kwargs

    def __init__(self):
        self._messages: list[MessageCache.MessageContent] = []

    def create_message(self, message):
        if isinstance(message,discord.Embed):
            msg = self.MessageContent(embed=message)
        elif isinstance(message,discord.File):
            msg = self.MessageContent(file=message)
        else:
            msg = self.MessageContent(message)
       
        return msg
        
    def post_message(self, message):
        msg = message
        if not isinstance(message,MessageCache.MessageContent):
            msg = self.create_message(message)
        self._messages.append(msg)

    def clear_messages(self):
        self._messages.clear()

    @property
    def messages(self):
        while self._messages:
            yield self._messages.pop()

    @property
    def has_messages(self):
        return bool(self._messages)

def compose_resultembed(data_dict : dict[str,str]) -> tuple[discord.Embed, str, discord.File, str]:
    has_failed = data_dict["status"] == "Failed"
    
    msg_color = discord.Colour.from_rgb(255,0,0) if has_failed else discord.Colour.from_rgb(0,255,0)
    embed_title = "Job Failed! :fire::fire::fire:" if has_failed else "Job Finished!"
    embed_title_emote = ":fire:" if has_failed else ":white_check_mark:" 
    embed_title = f"`{data_dict['name']}`{embed_title_emote}\n{embed_title}"

    embed_description = f"The farm has {data_dict['status'].lower()} job `{data_dict['name']}`."
    
    embed = discord.Embed(title=embed_title,color=msg_color,description=embed_description)
    
    embed.add_field(name=":abcd: Name: ", value=data_dict["name"],inline=False)
    embed.add_field(name=":ocean: Pool: ", value=data_dict["pool"],inline=False)
    embed.add_field(name=":classical_building: Department: ", value=data_dict["department"],inline=False)
    embed.add_field(name=":pray: Status: ", value=data_dict["status"])
    embed.add_field(name=":1234: Tasks: ", value=data_dict["tasks"])
    
    user_id = None
    tag_message = None
    if "ping" in data_dict.keys():
        if name := data_dict["ping"]:
            user = Query()
            user_id = DB.get(user.name == name)
            if user_id:
                emote = ":warning:" if data_dict["status"] == "Failed" else ":cooking:"
                embed.add_field(name=":speaking_head: User: ", value=f"<@{user_id['id']}>",inline=False)
                tag_message = f"{emote} Render {data_dict['status']}! <@{user_id['id']}>"

    file = None
    filename = None
    if "thumbnail" in data_dict.keys() and not has_failed:
        filename = data_dict["thumbnail"]
        file = discord.File(filename)

    return embed, tag_message, file, filename

MESSAGES = MessageCache()

# testing out an embed.
embed_msg = discord.Embed(title="Deadline bot v0.1\nby Sas van Gulik; @sasbom",
                          description="Discord integration for AWS Thinkbox Deadline :brain:", color=discord.Colour.from_str("#f49221"))
MESSAGES.post_message(embed_msg)
# end embed test

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
            MESSAGES.post_message(data_dict['message'][0])
        else:
            data_dict = {k : v[0] for k, v in data_dict.items()} # get first of all.
            embed, tag_msg, file, filename = compose_resultembed(data_dict=data_dict)
            
            if file:
                pic_msg = MESSAGES.create_message(file)
                label_msg = MESSAGES.create_message(f":frame_photo: `{filename}`")
                pic_msg._followup=label_msg
                MESSAGES.post_message(pic_msg)
            
            MESSAGES.post_message(embed)
            
            if tag_msg:
                MESSAGES.post_message(tag_msg)
                

            

            

DEADLINE_CATCHER = ThreadingHTTPServer((IP,1337),RequestHandler)

def run_server():
    DEADLINE_CATCHER.serve_forever()

SERVER_THREAD = threading.Thread(target=run_server)

async def server_task():
    await client.wait_until_ready()
    channel: discord.TextChannel = client.get_channel(1194649493501653173)
    while not client.is_closed():
        if MESSAGES.has_messages:
            await asyncio.wait([message.create_async_task(channel) for message in MESSAGES.messages])
        await asyncio.sleep(0.01)

class MyClient(discord.Client):
    async def setup_hook(self):
        self.loop.create_task(server_task())

intents = discord.Intents.default()
client = MyClient(intents=intents)
tree = app_commands.CommandTree(client)

@tree.command(
    name = "ping",
    guild=discord.Object(id=858640120826560512),
    description = "Check connection to bot."
)
async def ping_command(interaction: discord.Interaction, argument: str):
    await interaction.response.send_message(f"Pong!: {argument}")

@tree.command(
    name = "register",
    guild=discord.Object(id=858640120826560512),
    description = "Register your handle (allows you to be pinged!)"
)
async def register_command(interaction: discord.Interaction):
    name = interaction.user.name
    user = Query()
    id = DB.get(user.name == name)
    if id:
        await interaction.response.send_message(f"Your username has already been registered! :star:",ephemeral=True)
    else:
        DB.insert({"name": f"{name}", "id" : f"{interaction.user.id}"})
        await interaction.response.send_message(f"Your username has succesfully been registered! :white_check_mark:",ephemeral=True)

@tree.command(
    name = "deregister",
    guild=discord.Object(id=858640120826560512),
    description = "Deregister your handle (no more pings!)"
)
async def deregister_command(interaction: discord.Interaction):
    name = interaction.user.name
    user = Query()
    id = DB.get(user.name == name)
    if id:
        DB.remove(user.name == name)
        await interaction.response.send_message(f"Your username has been deregistered! :fire:",ephemeral=True)
    else:
        await interaction.response.send_message(f"Your username doesn't exist in the registry. :nail_care:",ephemeral=True)

@client.event
async def on_ready():
    # When client is ready, register command tree
    await tree.sync(guild=discord.Object(id=858640120826560512))
    
SERVER_THREAD.start()

client.run(token="MTE5MzU2OTAzNTQ0NzcxMzk0Mw.Guyf72.ax5uzK769mpeY4OZqSgEYnS4ockxqSYxe6K9EA")
DEADLINE_CATCHER.shutdown()
SERVER_THREAD.join()