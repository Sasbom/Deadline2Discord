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
    def __init__(self):
        self._messages = []

    def post_message(self, message):
        self._messages.append(message)
    
    def clear_messages(self):
        self._messages.clear()

    @property
    def messages(self):
        while self._messages:
            yield self._messages.pop()

    @property
    def has_messages(self):
        return bool(self._messages)


MESSAGES = MessageCache()

# testing out an embed.
embed_msg = discord.Embed(title="Deadline bot!", color=discord.Colour.from_str("#f49221"))
embed_msg.add_field(name=":abcd: Name: ", value="render_name",inline=False)
embed_msg.add_field(name=":ocean: Pool: ", value="render_pool",inline=False)

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
            msg_color = discord.Colour.from_rgb(255,0,0) if data_dict["status"] == "Failed" else discord.Colour.from_rgb(0,255,0)
            embed_title = "Job Failed! :fire::fire::fire:" if data_dict["status"] == "Failed" else "Job Finished!"
            embed = discord.Embed(title=embed_title,color=msg_color)
            embed.add_field(name=":abcd: Name: ", value=data_dict["name"],inline=False)
            embed.add_field(name=":ocean: Pool: ", value=data_dict["pool"],inline=False)
            embed.add_field(name=":classical_building: Department: ", value=data_dict["department"],inline=False)
            embed.add_field(name=":pray: Status: ", value=data_dict["status"])
            embed.add_field(name=":1234: Tasks: ", value=data_dict["tasks"])
            id = None
            if "ping" in data_dict.keys():
                if name := data_dict["ping"]:
                    user = Query()
                    id = DB.get(user.name == name)
                    if id:
                        emote = ":warning:" if data_dict["status"] == "Failed" else ":cooking:"
                        embed.add_field(name=":speaking_head: User: ", value=f"<@{id['id']}>",inline=False)
                        MESSAGES.post_message(f"{emote} Render {data_dict['status']}! <@{id['id']}>")
            
            MESSAGES.post_message(embed)
                

DEADLINE_CATCHER = ThreadingHTTPServer((IP,1337),RequestHandler)

def run_server():
    DEADLINE_CATCHER.serve_forever()

SERVER_THREAD = threading.Thread(target=run_server)

async def server_task():
    await client.wait_until_ready()
    channel: discord.TextChannel = client.get_channel(1194649493501653173)
    while not client.is_closed():
        if MESSAGES.has_messages:
            await asyncio.wait([asyncio.create_task(channel.send(message)) 
                                if not isinstance(message,discord.Embed) 
                                else asyncio.create_task(channel.send(embed=message)) 
                                for message in MESSAGES.messages])
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