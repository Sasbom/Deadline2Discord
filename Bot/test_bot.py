import discord
from discord import app_commands
import asyncio

from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from urllib import parse
import sys
import json
import socket
import threading

IP = socket.gethostbyname(socket.gethostname())

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
        print(f"Recieved message: {data_dict['message'][0]}")

        self.send_response(200)
        
        self.send_header("Content-type","application/json")
        self.end_headers()

        self.wfile.write(json.dumps({"message" : f"Message recieved: {data_dict['message'][0]}"}).encode())
        MESSAGES.post_message(data_dict['message'][0])

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


@client.event
async def on_ready():
    # When client is ready, register command tree
    await tree.sync(guild=discord.Object(id=858640120826560512))
    
SERVER_THREAD.start()

client.run(token="MTE5MzU2OTAzNTQ0NzcxMzk0Mw.Guyf72.ax5uzK769mpeY4OZqSgEYnS4ockxqSYxe6K9EA")
DEADLINE_CATCHER.shutdown()
SERVER_THREAD.join()