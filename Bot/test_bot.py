from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from urllib import parse
import sys
import json
import socket
import threading
import asyncio
import time
import datetime
import ast
import subprocess
from typing import Optional
import os

import discord
from discord import app_commands
from discord.ext import commands
from tinydb import TinyDB, Query

from Deadline.DeadlineConnect import DeadlineCon

# Establish connection with deadline server
CON = DeadlineCon(socket.gethostname(),8081)

IP = socket.gethostbyname(socket.gethostname())

DB = TinyDB(f"{__file__}/../register.db")

DEADLINE_CMD = R"C:\Program Files\Thinkbox\Deadline10\bin\deadlinecommand"

DEADLINE_ORANGE = discord.Colour.from_str("#f49221")

def get_timestamp_now() -> str:
    return f"<t:{int(time.time())}:f>"

def parse_deadlinetime(timestr: str, is_render: bool = False) -> str:
    h, m, s = (int(round(float(t))) for t in timestr.split(":"))
    
    if is_render and (h,m,s) == (0,0,0):
        return "Not done yet."

    return f"{int(h):02d} hr, {int(m):02d} min, {int(s):02d} sec."

def parse_deadlinetime_as_seconds(timestr: str):
    h, m, s = (int(round(float(t))) for t in timestr.split(":"))
    return h * 3600 + m * 60 + s

def get_timedelta(starttime):
    t = float(starttime)
    return str(datetime.timedelta(seconds=int(time.time()-t)))

def seconds_to_hms(seconds: int):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d} hr, {int(m):02d} min, {int(s):02d} sec."

def get_job_status(jobid):
    details = CON.Jobs.GetJobDetails(jobid)
    json_details = ast.literal_eval(f"{details}")
    return json_details[jobid]["Job"]["Status"]

def get_job(jobid):
    details = CON.Jobs.GetJob(jobid)
    return ast.literal_eval(f"{details}")
    
def dictify_dline_cmdout(out: str) -> dict:
    file = out.split("\n")
    obj = '{'
    
    for line in file:
        
        line = line.replace('\n', '')
        line = line.replace('\t', '')
        
        tokens = line.split("=",1)
        if len(tokens) == 2:
            obj = obj + '"'+tokens[0].strip()+'":"'+tokens[1].strip()+'",'
        
    obj = obj[:-1]
    
    obj = obj + '}'
    return ast.literal_eval(f"{obj}")

def get_job_cmd(jobid):
    job_proc = subprocess.run([DEADLINE_CMD, "-JobSubmissionInfoFromJob", str(jobid)],capture_output=True, text=True)
    job_out = job_proc.stdout
    plug_proc = subprocess.run([DEADLINE_CMD, "-PluginSubmissionInfoFromJob", jobid],capture_output=True, text=True)
    plug_out = plug_proc.stdout
    return dictify_dline_cmdout(job_out), dictify_dline_cmdout(plug_out)

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

MESSAGES = MessageCache()

# testing out an embed.
embed_msg = discord.Embed(title="Deadline bot v0.1\nby Sas van Gulik; @sasbom",
                          description="Discord integration for AWS Thinkbox Deadline :brain:", color=DEADLINE_ORANGE)
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


def stats_to_embed(stat_json_string) -> discord.Embed:
    stat_obj = json.loads(stat_json_string)
    job_id = stat_obj["JobID"]
    name = stat_obj["Name"]
    from_machine = stat_obj["Mach"]
    plugin = stat_obj["Plug"]
    priority = stat_obj["Pri"]
    tasks_total = stat_obj["Tasks"]
    tasks_complete = stat_obj["CompletedTaskCount"]
    tasks_render_average = parse_deadlinetime(stat_obj["AvgFrameRend"])
    job_q = Query()
    job_object = DB.get(job_q.job_id == job_id)
    running_time_raw = get_timedelta(job_object["job_time"])
    running_time = parse_deadlinetime(running_time_raw)
    render_time = parse_deadlinetime(stat_obj["RendTime"],True)
    status = get_job_status(job_id)
    job_dict, plugin_dict = get_job_cmd(job_id)

    directory = job_dict["OutputDirectory0"]
    filename = job_dict["OutputFilename0"]
    scene_file = plugin_dict["SceneFile"]

    # Use running time to approximate time left
    if render_time == "Not done yet.":
        tasks_left = int(float(tasks_total)) - int(float(tasks_complete))
        time_pertask = float(parse_deadlinetime_as_seconds(running_time_raw))/max(float(tasks_complete),0.001)
        time_left = seconds_to_hms(time_pertask * tasks_left)
    else:
        time_left = seconds_to_hms(0)
        running_time = render_time

    embed_msg = discord.Embed(title=f":chart_with_upwards_trend: Stats for `{name}`",
                              description=f"Analytics gathered from :wireless: Deadline API.\n:calendar: {get_timestamp_now()}",
                              color=DEADLINE_ORANGE)
    embed_msg.add_field(name=":information_source: Metadata",value=f"**ID:** {job_id}\n**Plugin:** {plugin}\n**Job priority:** {priority}\n**Submitted from:** {from_machine}\n**Status:** {status}",inline=False)
    embed_msg.add_field(name=f":pencil: Task info:",value=f"**Processed** {tasks_complete} **out of** {tasks_total} **tasks.**"
                                                          f"\n**Average time/frame:** {tasks_render_average}"
                                                          f"\n**Running time:** {running_time}"
                                                          f"\n**Estimated time left:** {time_left}"
                                                          f"\n**Total render time:** {render_time}"
                                                           "\n\n(Time estimate is based on task time, and time since the submission started. It may not be accurate, especially after a requeue. Requeues don't update the start time.)"
                                                          f"\n\n**Output directory:**\n`{directory}`\n**Output filename:**\n`{filename}`\n**Rendering Scene:**\n`{scene_file}`",
                                                           inline=False)
    
    return embed_msg

job_group = app_commands.Group(name="job",description="All commands that are to do with jobs")

@job_group.command(
    name = "stat",
    description = "Get a job's statistics",
)
async def renderjob_stats(interaction: discord.Interaction, job_name: str):
    name = interaction.user.name
    
    job = Query()
    job_info = DB.get(job.job_name == job_name)
    if job_info:
        owners = job_info["job_owner"]
        if name in owners or owners == "everyone":
            # let discord know i'm thinking rlly hard u m u
            await interaction.response.defer(ephemeral=True,thinking=True)

            response_stat = CON.Jobs.CalculateJobStatistics(job_info["job_id"])
            response_stat = str(response_stat).replace("'",'"')
            response_stat = response_stat.replace('None','"None"')

            msg = stats_to_embed(response_stat)
            
            # send the message
            await interaction.followup.send(embed=msg,ephemeral=True)
        else:
            await interaction.response.send_message(f"Your username is not associated with this job.",ephemeral=True)
    else:
        await interaction.response.send_message(f"Job {job_name} doesn't exist or is improperly registered.",ephemeral=True) 

@job_group.command(
    name="requeue",
    description="Requeue all tasks in an existing job"
)
async def renderjob_requeue(interaction: discord.Interaction, job_name: str):
    name = interaction.user.name
    
    job = Query()
    job_info = DB.get(job.job_name == job_name)
    if job_info:
        owners = job_info["job_owner"]
        if name in owners or owners == "everyone":
            await interaction.response.defer(ephemeral=True,thinking=True)
            CON.Jobs.UpdateJobSubmissionDate(job_info["job_id"])
            CON.Jobs.RequeueJob(job_info["job_id"])
            await interaction.followup.send(f"Requested to requeue all tasks in `{job_name}`.",ephemeral=True)
        else:
            await interaction.response.send_message(f"Your username is not associated with this job.",ephemeral=True)
    else:
        await interaction.response.send_message(f"Job {job_name} doesn't exist or is improperly registered.",ephemeral=True) 


@job_group.command(
    name="fail",
    description="Deliberately Fail all tasks in an existing job"
)
async def renderjob_fail(interaction: discord.Interaction, job_name: str):
    name = interaction.user.name
    
    job = Query()
    job_info = DB.get(job.job_name == job_name)
    if job_info:
        owners = job_info["job_owner"]
        if name in owners or owners == "everyone":
            await interaction.response.defer(ephemeral=True,thinking=True)
            CON.Jobs.FailJob(job_info["job_id"])
            await interaction.followup.send(f"Requested to fail all tasks in `{job_name}`.",ephemeral=True)
        else:
            await interaction.response.send_message(f"Your username is not associated with this job.",ephemeral=True)
    else:
        await interaction.response.send_message(f"Job {job_name} doesn't exist or is improperly registered.",ephemeral=True) 


@job_group.command(
    name="suspend",
    description="Suspend a job, putting it on pause."
)
async def renderjob_suspend(interaction: discord.Interaction, job_name: str):
    name = interaction.user.name
    
    job = Query()
    job_info = DB.get(job.job_name == job_name)
    if job_info:
        owners = job_info["job_owner"]
        if name in owners or owners == "everyone":
            await interaction.response.defer(ephemeral=True,thinking=True)
            CON.Jobs.SuspendJob(job_info["job_id"])
            await interaction.followup.send(f"Suspended `{job_name}`.",ephemeral=True)
        else:
            await interaction.response.send_message(f"Your username is not associated with this job.",ephemeral=True)
    else:
        await interaction.response.send_message(f"Job {job_name} doesn't exist or is improperly registered.",ephemeral=True) 


@job_group.command(
    name="resume",
    description="Resume a job, releasing it from suspended state"
)
async def renderjob_suspend(interaction: discord.Interaction, job_name: str):
    name = interaction.user.name
    
    job = Query()
    job_info = DB.get(job.job_name == job_name)
    if job_info:
        owners = job_info["job_owner"]
        if name in owners or owners == "everyone":
            await interaction.response.defer(ephemeral=True,thinking=True)
            CON.Jobs.ResumeJob(job_info["job_id"])
            await interaction.followup.send(f"Resumed `{job_name}`.",ephemeral=True)
        else:
            await interaction.response.send_message(f"Your username is not associated with this job.",ephemeral=True)
    else:
        await interaction.response.send_message(f"Job {job_name} doesn't exist or is improperly registered.",ephemeral=True) 


@job_group.command(
    name="reschedule",
    description="Reschedule existing job as a new job. Can take a fair bit.\nAdditionally, you can specify a new scenefile to render, a new filename to use, and a new directory to render to."
)
async def renderjob_reschedule(interaction: discord.Interaction, job_name: str, job_new_name: str, job_new_scenefile: Optional[str] = None, job_new_filename: Optional[str] = None,job_new_directory: Optional[str] = None ):
    name = interaction.user.name
    
    job = Query()
    job_info = DB.get(job.job_name == job_name)
    
    if job_info:

        if job_name == job_new_name:
            await interaction.response.send_message(f"Please rename your job something else than `{job_name}` for clarity.",ephemeral=True)
            return

        owners = job_info["job_owner"]
        if name in owners or owners == "everyone":
            await interaction.response.defer(ephemeral=True,thinking=True)
    
            props, plug = get_job_cmd(job_info["job_id"])
            props["Name"] = job_new_name

            if job_new_scenefile:
                plug["SceneFIle"] = job_new_scenefile
            
            if job_new_filename:
                props["OutputFilename0"] = job_new_filename
        
            if job_new_directory:
                props["OutputDirectory0"] = job_new_directory
            
            plug["OutputFile"] = os.path.join(props["OutputDirectory0"],props["OutputFilename0"])

            CON.Jobs.SubmitJob(props,plug)

            await interaction.followup.send(f"Requested to reschedule tasks in `{job_name}` as `{job_new_name}`.",ephemeral=True)
        else:
            await interaction.response.send_message(f"Your username is not associated with this job.",ephemeral=True)
    else:
        await interaction.response.send_message(f"Job {job_name} doesn't exist or is improperly registered.",ephemeral=True) 


@job_group.command(
    name="mine",
    description="Show owned jobs and their states. Can take a while!"
)
async def renderjob_showmine(interaction: discord.Interaction):
    name = interaction.user.name
    job = Query()
    search_in = lambda s : name in s
    job_info = DB.search(job.job_owner.test(search_in))
    if job_info:
        await interaction.response.defer(ephemeral=True,thinking=True)
        response_txt = ["### All jobs found in your name:"]
        for job in job_info:
            status = get_job_status(job["job_id"])
            response_txt.append(f"> `{job['job_name']}`,  Status: **{status}**")
        await interaction.followup.send("\n".join(response_txt))
    else:
        await interaction.response.send_message(f"No jobs were found in your name... :skull:",ephemeral=True) 



@job_group.command(
    name = "finish",
    description = "Deregister a Completed/Failed job that you own."
)
async def job_deregister_command(interaction: discord.Interaction, job_name: str):
    name = interaction.user.name
    
    job = Query()
    job_info = DB.get(job.job_name == job_name)
    if job_info:
        owners = job_info["job_owner"]
        if name in owners or owners == "everyone":
            await interaction.response.defer(ephemeral=True,thinking=True)
            status = get_job_status(job_info["job_id"])
            if status in ["Completed", "Failed"]:
                DB.remove(job.job_name == job_name)
                await interaction.followup.send(f"Unregistered `{job_name}` from internal registry!",ephemeral=True)
            else:
                await interaction.followup.send(f"`{job_name}` couldn't be removed, status is **{status}**. \nTip: Use `/job fail {job_name}` to make it available for finishing!",ephemeral=True)
        else:
            await interaction.response.send_message(f"Your username is not associated with this job.",ephemeral=True)
    else:
        await interaction.response.send_message(f"Job {job_name} doesn't exist or is improperly registered.",ephemeral=True) 


@job_group.command(
    name="finish_all",
    description="Deregister ALL Completed/Failed jobs that you explicitly own. Can take a while."
)
async def job_deregister_all(interaction: discord.Interaction):
    name = interaction.user.name
    job = Query()
    search_in = lambda s : name in s
    job_info = DB.search(job.job_owner.test(search_in))
    if job_info:
        await interaction.response.defer(ephemeral=True,thinking=True)
        response_txt = ["### Deregistered:"]
        for job in job_info:
            status = get_job_status(job_info["job_id"])
            job_name = job_info["job_name"]
            if status in ["Completed", "Failed"]:
                DB.remove(job.job_name == job_name)
            response_txt.append(f"> `{job['job_name']}`")
        await interaction.followup.send(",\n".join(response_txt))
    else:
        await interaction.response.send_message(f"No jobs were found in your name... :skull:",ephemeral=True) 


@job_group.command(
    name="help",
    description="Help page for job commands, also availale in dutch with nederlands = True"
)
async def job_help(interaction: discord.Interaction, nederlands: Optional[bool] = False):
    if not nederlands:
        help_txt = "**All /job commands, explained.**\n\n\
                    **/job mine:** Shows you all jobs that are yours, and their status.\n\
                    **/job stat:** Shows you useful info about a specific job.\n\n\
                    **/job suspend:** Pause a job. Time will keep elapsing, but it won't render.\n\
                    **/job resume:** Unpause a job if it's paused. It will start rendering again!\n\
                    **/job fail:** Mark a job as failed! You won't be able to requeue this, but rescheduling works.\n\n\
                    **/job requeue:** Re-queue up all the tasks within de job, effectively rendering it again.\n\
                    **/job reschedule:** Repost a job, but with a different name, + other options."
    else:
        help_txt = "**Alle /job opdrachten, uitgelegd.**\n\n\
                    **/job mine:** Laat alle renderopdrachten zien die van jou zijn, en hun status.\n\
                    **/job stat:** Laat handige informatie zien over een specifieke renderopdracht.\n\n\
                    **/job suspend:** Zet een opdracht op pauze!\n\
                    **/job resume:** Als een opdracht op pauze staat, zet je 'm met deze weer aan.\n\
                    **/job fail:** Markeer een opdracht als gefaald. Hierdoor kan je hem niet meer 'requeue'-en, maar wel reschedulen.\n\n\
                    **/job requeue:** Zet alle taken in de opdracht op dezelfde manier aan, waardoor je 'm opnieuw rendert.\n\
                    **/job reschedule:** Maak een kopie van de opdracht met een andere naam, en post hem opnieuw met extra opties."
    embed = discord.Embed(title="Job help",color=DEADLINE_ORANGE, description=help_txt)
    await interaction.response.send_message(embed=embed,ephemeral=True)

    

tree.add_command(job_group,guild=discord.Object(id=858640120826560512),)

@client.event
async def on_ready():
    # When client is ready, register command tree
    await tree.sync(guild=discord.Object(id=858640120826560512))
    
SERVER_THREAD.start()

client.run(token="MTE5MzU2OTAzNTQ0NzcxMzk0Mw.Guyf72.ax5uzK769mpeY4OZqSgEYnS4ockxqSYxe6K9EA")
DEADLINE_CATCHER.shutdown()
SERVER_THREAD.join()