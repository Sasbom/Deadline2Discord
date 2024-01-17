import asyncio

from .singleton import SingletonMetaClass
import discord
from discord import app_commands

class MessageCache(metaclass=SingletonMetaClass):

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
        
        def then(self, followup):
            if isinstance(followup,MessageCache.MessageContent):
                self._followup = followup
    
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
    
MESSAGES = MessageCache()