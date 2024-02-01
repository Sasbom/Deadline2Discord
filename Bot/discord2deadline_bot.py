from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
import re

import discord
from discord import app_commands
from discord.ext.commands import has_permissions
from tinydb import TinyDB, Query

from Deadline.DeadlineConnect import DeadlineCon

import util.secret as secret
from util.message_cache import MESSAGES

from util.httpserver import DeadlineHTTPCatcher

SECRET = secret.Secret
GUILD = discord.Object(id=SECRET.guild)

# Establish connection with deadline server
CON = DeadlineCon(socket.gethostname(),SECRET.deadline_port)

IP = socket.gethostbyname(socket.gethostname())

DB = TinyDB(f"{__file__}/../register.db")

DEADLINE_CMD = R"C:\Program Files\Thinkbox\Deadline10\bin\deadlinecommand"

DEADLINE_ORANGE = discord.Colour.from_str("#f49221")

REGEX_FLOAT = re.compile(r"\d+[.]?[\d+]?")

REGEX_TIME_HHMMSS = re.compile(r"\d{1,}[:][0-5]{1}\d{1}[:][0-5]{1}\d{1}")
REGEX_TIME_MMSS = re.compile(r"[0-5]{0,1}\d{1}[:][0-5]{1}\d{1}")
REGEX_FRAMERANGE = re.compile(r"(?:[\d]+\s*\-{1}\s*[\d]+|[\d]+)")
REGEX_TIME_HHMM = re.compile(r"(?:[2][0-3]:[0-5][\d]|[0-1]?[\d]:[0-5][\d])")

def get_timestamp_now() -> str:
    return f"<t:{int(time.time())}:f>"

def parse_deadlinetime(timestr: str, is_render: bool = False) -> str:
    dayhours = 0
    if "," in timestr:
        days, timestr = timestr.split(",")
        dayhours = int(days.split(" ")[0])*24
    h, m, s = (int(round(float(t))) for t in timestr.split(":"))
    h += dayhours
    if is_render and (h,m,s) == (0,0,0):
        return "Not done yet."

    return f"{int(h):02d} hr, {int(m):02d} min, {int(s):02d} sec."

def parse_deadlinetime_as_seconds(timestr: str):
    dayhours = 0
    if "," in timestr:
        days, timestr = timestr.split(",")
        dayhours = int(days.split(" ")[0])*24
    h, m, s = (int(round(float(t))) for t in timestr.split(":"))
    h += dayhours
    return h * 3600 + m * 60 + s

def get_timedelta(starttime):
    t = float(starttime)
    return str(datetime.timedelta(seconds=int(time.time()-t)))

def seconds_to_hms(seconds: int):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d} hr, {int(m):02d} min, {int(s):02d} sec."

def get_job_status(jobid):
    try:
        details = (CON.Jobs.GetJobDetails(jobid))
        details = str(details).replace("\\","/")
        json_details = ast.literal_eval(f"{details}")
        return json_details[jobid]["Job"]["Status"]
    except:
        return None

def get_job(jobid):
    details = CON.Jobs.GetJob(jobid).replace("\\","/")
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
    obj = obj.replace("\\","/")
    return ast.literal_eval(f"{obj}")

def fix_path(path):
    path = path.replace("\r","/r")
    path = path.replace("\t","/t")
    for i in range(99):
        if i < 10:
            path = path.replace(f"\{i}",f"/{i}")
        path = path.replace(f"\{i:02d}",f"/{i:02d}")
    path = path.replace("\\","/")
    return path

def get_job_cmd(jobid):
    job_proc = subprocess.run([DEADLINE_CMD, "-JobSubmissionInfoFromJob", str(jobid)],capture_output=True, text=True)
    job_out = job_proc.stdout
    plug_proc = subprocess.run([DEADLINE_CMD, "-PluginSubmissionInfoFromJob", jobid],capture_output=True, text=True)
    plug_out = plug_proc.stdout
    return dictify_dline_cmdout(job_out), dictify_dline_cmdout(plug_out)

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


def get_user_pingable(username: str):
    user = Query()
    id = DB.get(user.name == username)
    return bool(id)

# testing out an embed.
embed_msg = discord.Embed(title="Deadline bot v0.2\nby Sas van Gulik; @sasbom",
                          description="Discord integration for AWS Thinkbox Deadline :brain:", color=DEADLINE_ORANGE)
MESSAGES.post_message(embed_msg)
# end embed test

GC_AUTO_ENABLED = False
GC_HOURS_INTERVAL = 24

async def server_task():
    await client.wait_until_ready()
    channel: discord.TextChannel = client.get_channel(SECRET.channel)
    while not client.is_closed():
        if MESSAGES.has_messages:
            await asyncio.wait([message.create_async_task(channel) for message in MESSAGES.messages])
        await asyncio.sleep(0.01)


async def server_task_cleanup_logs():
    await client.wait_until_ready()
    channel: discord.TextChannel = client.get_channel(SECRET.channel)
    while not client.is_closed():
        if GC_AUTO_ENABLED:
            channel.send(f"Checking for deleted jobs and deleting them. Any queries made during this time will not be responsive. :clock:\n"
                            f"This task is executed every {GC_HOURS_INTERVAL} hours, to ensure database sanity.\n"
                            "Admins can enable/disable this check with /farm garbagecollect set [True/False] [Optional Time in hours].")
            garbage_collect()
        await asyncio.sleep(60*60*GC_HOURS_INTERVAL) # every specified hours.

def garbage_collect():
    """
    Garbage collection cycle. Checks if jobs have been deleted.
    """
    print("Starting deleted job cleaup cycle...")
    jobs = Query()
    search_invalid = lambda s : get_job_status(s) is None
    job_info = DB.search(jobs.job_id.test(search_invalid))
    for job in job_info:
        print(job["job_name"])
        DB.remove(jobs.job_name == job["job_name"])
    MESSAGES.post_message("Database cleaned up. Degenerate tasks removed!\nHappy rendering! :rocket:")
    print("Finished deleted job cleanup cycle.")


async def server_task_suspensionmanager():
    await client.wait_until_ready()
    channel: discord.TextChannel = client.get_channel(SECRET.channel)
    job_q = Query()
    while not client.is_closed():
        time_now = datetime.datetime.now()
        jobs = DB.search(job_q.resumeflag.exists())

        for j in jobs:
            suspendtime = j["suspendtime"]
            resumetime = j["resumetime"]
            resumeflag = j["resumeflag"] # is "True" if job is running
            job_id = j["job_id"]

            if resumeflag == "False":
                hours, minutes = [int(i) for i in resumetime.split(":")]
                if time_now.hour == hours and time_now.minute == minutes:
                    CON.Jobs.ResumeJob(job_id)
                    DB.update({"resumeflag" : "True"},jobs.job_id == job_id)
            elif resumeflag == "True":
                hours, minutes = [int(i) for i in suspendtime.split(":")]
                if time_now.hour == hours and time_now.minute == minutes:
                    CON.Jobs.SuspendJob(job_id)
                    DB.update({"resumeflag" : "False"},jobs.job_id == job_id)
        await asyncio.sleep(10)

class MyClient(discord.Client):
    async def setup_hook(self):
        self.loop.create_task(server_task())
        self.loop.create_task(server_task_cleanup_logs())
        self.loop.create_task(server_task_suspensionmanager())

intents = discord.Intents.default()
client = MyClient(intents=intents)
tree = app_commands.CommandTree(client)


@tree.command(
    name = "register",
    guild=GUILD,
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
    guild=GUILD,
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

    directory = os.path.normpath(job_dict["OutputDirectory0"]).replace("\\","/")
    filename = os.path.normpath(job_dict["OutputFilename0"]).replace("\\","/")
    
    scene_file = "No scene file could be extracted."
    if "SceneFile" in plugin_dict.keys():
        scene_file = plugin_dict["SceneFile"]
    elif "EnvironmentKeyValue1" in job_dict.keys():
        scene_file = job_dict["EnvironmentKeyValue1"].split("=")[1]
    scene_file = os.path.normpath(scene_file).replace("\\","/")

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

job_group = app_commands.Group(name="job",description="All commands that have something to do or manipulate jobs")

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
    description="Reschedule existing job as a new job. Can take a fair bit."
)
async def renderjob_reschedule(interaction: discord.Interaction, 
                               job_name: str, job_new_name: str, 
                               job_new_scenefile: Optional[str] = None, 
                               job_new_filename: Optional[str] = None,
                               job_new_directory: Optional[str] = None,
                               job_new_frames: Optional[str] = None,
                               submit_suspended: Optional[bool] = None):
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
                plug["SceneFile"] = job_new_scenefile
            
            if job_new_filename:
                props["OutputFilename0"] = job_new_filename
        
            if job_new_directory:
                props["OutputDirectory0"] = job_new_directory

            if job_new_frames:
                # validate new frames
                split_f = job_new_frames.split(",")
                if not all(re.fullmatch(REGEX_FRAMERANGE,m.strip()) for m in split_f):
                    await interaction.response.send_message(f"Given framerange `{job_new_frames}` is not valid.\nUse valid syntax; `15, 20-25, 100`.",ephemeral=True)
                    return
                else:
                    props["Frames"] = job_new_frames
                    

            plug["OutputFile"] = os.path.join(props["OutputDirectory0"],props["OutputFilename0"])
                
            newjob = CON.Jobs.SubmitJob(props,plug)
            if submit_suspended:
                newjob_dict = ast.literal_eval(f"{newjob}")
                print("putting", newjob_dict["_id"], "in suspended state")
                CON.Jobs.SuspendJob(newjob_dict["_id"])


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
            if status is None:
                status = "Job is not present on server anymore."
            response_txt.append(f"> `{job['job_name']}`,  Status: **{status}**")
        await interaction.followup.send("\n".join(response_txt))
    else:
        await interaction.response.send_message(f"No jobs were found in your name... :skull:",ephemeral=True) 


activehours_group = app_commands.Group(name="activehours",description="Options for active hours of job",parent=job_group)

@activehours_group.command(
    name="set",
    description="Set active hours of this job in military time, 06:00 for 6 am, and 19:30 for half past 7 pm."
)
async def job_set_activehours(interaction: discord.Interaction, job_name: str, time_suspend: str = "08:00", time_resume: str = "19:00"):
    name = interaction.user.name
    
    if not re.fullmatch(REGEX_TIME_HHMM,time_suspend):
        await interaction.response.send_message(f"Suspend time improperly formatted. `{time_suspend}` doesn't conform to HH:MM, 6:00, 00:00, 23:59, etc.",ephemeral=True)
        return
    if not re.fullmatch(REGEX_TIME_HHMM,time_resume):
        await interaction.response.send_message(f"Resume time improperly formatted. `{time_resume}` doesn't conform to HH:MM, 6:00, 00:00, 23:59, etc.",ephemeral=True)
        return
    
    job = Query()
    job_info = DB.get(job.job_name == job_name)
    if job_info:
        owners = job_info["job_owner"]
        if name in owners or owners == "everyone":
            await interaction.response.defer(ephemeral=True,thinking=True)
            import tinydb.operations as dbop
            status = get_job_status(job_info["job_id"])
            flag = "True" if not status == "Suspended" else "False"
            DB.update(dbop.set("resumetime",time_resume),job.job_name == job_name)
            DB.update(dbop.set("suspendtime",time_suspend),job.job_name == job_name)
            DB.update(dbop.set("resumeflag",flag),job.job_name == job_name)
            await interaction.followup.send(f"Set `{job_name}` to activate at `{time_resume}` and pause at `{time_suspend}`.",ephemeral=True)
        else:
            await interaction.response.send_message(f"Your username is not associated with this job.",ephemeral=True)
    else:
        await interaction.response.send_message(f"Job {job_name} doesn't exist or is improperly registered.",ephemeral=True) 


@activehours_group.command(
    name="clear",
    description="Remove task from automatic suspension/resuming scheduling"
)
async def job_set_activehours(interaction: discord.Interaction, job_name: str):
    name = interaction.user.name
    
    job = Query()
    job_info = DB.get(job.job_name == job_name)
    if job_info:
        owners = job_info["job_owner"]
        if name in owners or owners == "everyone":
            await interaction.response.defer(ephemeral=True,thinking=True)
            import tinydb.operations as dbop
            try:
                DB.update(dbop.delete("resumetime"),job.job_name == job_name)
                DB.update(dbop.delete("suspendtime"),job.job_name == job_name)
                DB.update(dbop.delete("resumeflag"),job.job_name == job_name)
            except BaseException as e:
                print(e)
            await interaction.followup.send(f"Set `{job_name}` to no longer be susceptible to suspension/resuming scheduling.",ephemeral=True)
        else:
            await interaction.response.send_message(f"Your username is not associated with this job.",ephemeral=True)
    else:
        await interaction.response.send_message(f"Job {job_name} doesn't exist or is improperly registered.",ephemeral=True) 
        

@job_group.command(
    name = "finish",
    description = "Deregister a Completed/Failed/Deleted job that you own."
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
            if status in ["Completed", "Failed", None]:
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
            if status in ["Completed", "Failed", None]:
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

prism_group = app_commands.Group(name="prism",description="Offers integration with Prism projects submitted to Deadline.")

@prism_group.command(
    name = "register",
    description="Register the name of a Prism project."
)
async def create_prismproject(interaction: discord.Interaction, prism_project: str):
    prism_project = prism_project.strip() # normalize name
    user = interaction.user.name
    project = Query()
    p = DB.get(project.prism_name == prism_project)
    if p is not None:
        await interaction.response.send_message(f"Prism project `{prism_project}` is already present in the system.",ephemeral=True)
    else:
        DB.insert({"prism_name" : prism_project, "subscribed_users" : "", "is_locked" : "False", "prism_owner" : user})
        await interaction.response.send_message(f"Registered Prism project `{prism_project}` in the system, with you ,`@{user}` being the owner.",ephemeral=True)


@prism_group.command(
    name = "deregister",
    description="Deregister the name of a Prism project."
)
async def remove_prismproject(interaction: discord.Interaction, prism_project: str):
    prism_project = prism_project.strip() # normalize name
    user = interaction.user.name
    is_admin = interaction.user.guild_permissions.administrator
    project = Query()
    p = DB.get(project.prism_name == prism_project)
    if p is not None and (p["prism_owner"] == user or is_admin):
        DB.remove(project.prism_name == prism_project)
        admin_msg = "`Admin override`: " if (p["prism_owner"] != user and is_admin) else ""
        await interaction.response.send_message(f"{admin_msg}Prism project `{prism_project}` has been removed from the system.",ephemeral=True)
    elif p is not None and (p["prism_owner"] != user or not is_admin):   
        await interaction.response.send_message(f"Prism project `{prism_project}` is not yours! You can't remove it.",ephemeral=True)
    else:
        await interaction.response.send_message(f"No records of Prism project `{prism_project}` found.",ephemeral=True)

        
@prism_group.command(
    name = "subscribe",
    description="Subscribe to a Prism project"
)
async def user_join_prismproject(interaction: discord.Interaction, prism_project: str):
    prism_project = prism_project.strip() # normalize name
    user = interaction.user.name
    if not get_user_pingable(user):
        await interaction.response.send_message(f"To perform this action, you must register yourself first!\nUse `/register` to register your username to be pingable.",ephemeral=True)
    project = Query()
    p = DB.get(project.prism_name == prism_project)
    if p is not None and p["is_locked"] == "False":
        users: list[str] = p["subscribed_users"].split(",") if p["subscribed_users"] else []
        if user in users:
            await interaction.response.send_message(f"You are already subscribed to `{prism_project}`.",ephemeral=True)
        else:
            users.append(user)
            DB.update({"subscribed_users" : ",".join(users)}, project.prism_name == prism_project)
            await interaction.response.send_message(f"Succesfully subscribed to `{prism_project}`!",ephemeral=True)
    elif p is not None and p["is_locked"] == "True":
        await interaction.response.send_message(f"Prism Project: `{prism_project}` is not able to be subscribed to, because the owner locked it.",ephemeral=True)
    else:
       await  interaction.response.send_message(f"Register Prism project `{prism_project}` before subscribing to it!",ephemeral=True)


@prism_group.command(
    name = "unsubscribe",
    description="Unsubscribe from a Prism project"
)
async def user_leave_prismproject(interaction: discord.Interaction, prism_project: str):
    prism_project = prism_project.strip() # normalize name
    user = interaction.user.name
    project = Query()
    p = DB.get(project.prism_name == prism_project)
    if p is not None and p["is_locked"] == "False":
        users: list[str] = p["subscribed_users"].split(",")
        if user not in users:
            await interaction.response.send_message(f"You are not subscribed to `{prism_project}`.",ephemeral=True)
        elif user in users:
            users = [u for u in users if not u == user] # Recompose list without user in it
            DB.update({"subscribed_users" : ",".join(users)}, project.prism_name == prism_project)         
            await interaction.response.send_message(f"Succesfully unsubscribed from `{prism_project}`!",ephemeral=True)
    elif p is not None and p["is_locked"] == "True":
        await interaction.response.send_message(f"Prism Project: `{prism_project}` is not able to be unsubscribed from, because the owner locked it.",ephemeral=True)
    else:
       await  interaction.response.send_message(f"Register Prism project `{prism_project}` before subscribing to it!",ephemeral=True)


@prism_group.command(
    name = "lock",
    description="Lock Prism project, allowing no more subscribers."
)
async def lock_prismproject(interaction: discord.Interaction, prism_project: str):
    prism_project = prism_project.strip() # normalize name
    user = interaction.user.name
    is_admin = interaction.user.guild_permissions.administrator
    project = Query()
    p = DB.get(project.prism_name == prism_project)
    if p is not None and (p["prism_owner"] == user or is_admin):
        DB.update({"is_locked" : "True"},project.prism_name == prism_project)
        admin_msg = "`Admin override`: " if (p["prism_owner"] != user and is_admin) else ""
        await interaction.response.send_message(f"{admin_msg}Prism project `{prism_project}` has been locked!\nNo one can subscribe/unsubscribe anymore.",ephemeral=True)
    elif p is not None and (p["prism_owner"] != user or not is_admin):   
        await interaction.response.send_message(f"Prism project `{prism_project}` is not yours! You can't lock it.",ephemeral=True)
    else:
        await interaction.response.send_message(f"No records of Prism project `{prism_project}` found.",ephemeral=True)

@prism_group.command(
    name = "unlock",
    description="UnLock Prism project, allowing subscribers."
)
async def lock_prismproject(interaction: discord.Interaction, prism_project: str):
    prism_project = prism_project.strip() # normalize name
    user = interaction.user.name
    is_admin = interaction.user.guild_permissions.administrator
    project = Query()
    p = DB.get(project.prism_name == prism_project)
    if p is not None and (p["prism_owner"] == user or is_admin):
        DB.update({"is_locked" : "False"},project.prism_name == prism_project)
        admin_msg = "`Admin override`: " if (p["prism_owner"] != user and is_admin) else ""
        await interaction.response.send_message(f"{admin_msg}Prism project `{prism_project}` has been unlocked!\nPeople can subscribe/unsubscribe again.",ephemeral=True)
    elif p is not None and (p["prism_owner"] != user or not is_admin):   
        await interaction.response.send_message(f"Prism project `{prism_project}` is not yours! You can't unlock it.",ephemeral=True)
    else:
        await interaction.response.send_message(f"No records of Prism project `{prism_project}` found.",ephemeral=True)


@prism_group.command(
    name = "list",
    description="List all registered Prism projects, their owners, and their subscribers."
)
async def list_prismprojects(interaction: discord.Interaction):   
    projects = Query()
    search_in = lambda s : s != ""
    prism_info = DB.search(projects.prism_name.test(search_in))
    if prism_info:
        await interaction.response.defer(ephemeral=True,thinking=True)
        response_txt = ["### All Prism projects in the system:"]
        for p in prism_info:
            locked = "`Locked` :locked:" if p["is_locked"] == "True" else "`Unlocked` :unlock:"
            owner = p["prism_owner"]
            subs = ", ".join(p["subscribed_users"].split(",")) if p["subscribed_users"] else "No one has subbed yet..."
            response_txt.append(f"> `{p['prism_name']}`,  Owned by: `{owner}`, {locked}\n> - Subscribers: `{subs}`\n")
        await interaction.followup.send("\n".join(response_txt))
    else:
        await interaction.response.send_message(f"No Prism projects were found. :skull:",ephemeral=True) 
        

@prism_group.command(
    name="help",
    description="Help page for /prism commands, also availale in dutch with nederlands = True"
)
async def job_help(interaction: discord.Interaction, nederlands: Optional[bool] = False):
    if not nederlands:
        help_txt = "**All /prism commands, explained.**\n\n\
                    **/prism register:** Register a Prism project with you as the owner.\n\
                    **/prism deregister:** If you are the owner of a Prism project, deregister it\n\n\
                    **/prism subscribe:** Subscribe to a Prism project. If you are in this list, any completed job within the project will ping you.\n\
                    **/prism unsubscribe:** Unsubscribe from a project. No more pings!\n\n\
                    **/prism lock:** Locks a project from getting new subscribers. Can only be done if you own the project.\n\
                    **/prism unlock:** Unlocks a project, allowing subscribers again. Can only be done if you own the project.\n\n\
                    **/prism list:** List all registered prism projects."
    else:
        help_txt = "**Alle /prism commands, uitgelegd.**\n\n\
                    **/prism register:** Registreer een Prism project, met jou als eigenaar.\n\
                    **/prism deregister:**Als je de eigenaar bent van een Prism project, haal 'm uit het systeem.\n\n\
                    **/prism subscribe:** Meld je aan om gepingt te worden voor alle renders uit dit Prism project.\n\
                    **/prism unsubscribe:** Meld je af van een Prism project. Geen pings meer!\n\n\
                    **/prism lock:** Zet een project op slot. Als je de eigenaar bent, voorkom je zo ongewenste registraties.\n\
                    **/prism unlock:** Hal een project van slot. Als je de eigenaar bent, kan je zo mensen weer de optie geven om aan te melden.\n\n\
                    **/prism list:** Laat alle geregistreerde prism projecten zien!"
    embed = discord.Embed(title="Prism help",color=DEADLINE_ORANGE, description=help_txt)
    await interaction.response.send_message(embed=embed,ephemeral=True)

calc_group = app_commands.Group(name="calculate",description="Calculate things!")

@calc_group.command(
    name="rendertime",
    description="Estimate render time in a sequence of some FPS and duration. Time in HH:MM:SS"
)
async def calculate_frames_fromseconds(interaction: discord.Interaction, 
                                       fps: str = "24.0",
                                       frame_rendertime: str = "00:00:00",
                                       sequence_duration: str = "00:00:00",
                                       pc_amt: int = 1):
    if re.fullmatch(REGEX_FLOAT,fps):
        fps = float(fps)
    else:
        await interaction.response.send_message("Please enter a valid number for fps, frames per second. This can be a decimal number e.g. (23.994)",ephemeral=True)
        return
    
    timecodes = [frame_rendertime, sequence_duration]
    for i, t in enumerate(timecodes):
        if not re.fullmatch(REGEX_TIME_HHMMSS,t):
            if re.fullmatch(REGEX_TIME_MMSS,t):
                t = f"00:{t}"
                timecodes[i] = t
            else:
                await interaction.response.send_message(f"Time: {t} could not be properly interpreted.\nPlease format time as HH:MM:SS, or MM:SS e.g. (01:05:54, 12:10, 1:30).",ephemeral=True)
                return
    frame_rendertime, sequence_duration = timecodes

    rendersec = parse_deadlinetime_as_seconds(frame_rendertime)
    durationsec = parse_deadlinetime_as_seconds(sequence_duration)
    pc_amt = max(1,pc_amt)
    sequence_frames = round(fps*float(durationsec))
    sequence_rendertime = (rendersec * sequence_frames) / float(pc_amt)
    
    message = f"A sequence of length `{seconds_to_hms(durationsec)}` at `{fps} frames per second`,\nhas `{int(sequence_frames)} frames` total,\nand will render for `{seconds_to_hms(sequence_rendertime)}` on `{pc_amt} workers`\nwith each frame taking `{seconds_to_hms(rendersec)}`"
    
    await interaction.response.send_message(message,ephemeral=True)

farm_group = app_commands.Group(name="farm",description="Manage the farm in different ways.")
garbage_collect_group = app_commands.Group(name="garbagecollect",description="Garbage collection settings", parent=farm_group)

@garbage_collect_group.command(
    name="set",
    description="Turn automatic garbage collection of deleted jobs on/off, and optionally set the time interval."
)
@has_permissions(administrator=True)
async def auto_gc(interaction: discord.Interaction, enabled: bool, hour_interval: Optional[int] = None):
    GC_AUTO_ENABLED = enabled
    reportstr = f"Garbage collection enabled: {GC_AUTO_ENABLED}"
    if hour_interval is not None:
        GC_HOURS_INTERVAL = hour_interval
        reportstr += f"\nGarbage collection interval: {GC_HOURS_INTERVAL}"
    await interaction.response.send_message(reportstr,ephemeral=True)

@garbage_collect_group.command(
    name="force",
    description="Turn automatic garbage collection of deleted jobs on/off, and optionally set the time interval."
)
@has_permissions(administrator=True)
async def force_gc(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    channel: discord.TextChannel = client.get_channel(SECRET.channel)
    await channel.send(f"Checking for deleted jobs and deleting them. Any queries made during this time will not be responsive. :clock:")
    garbage_collect()
    await interaction.followup.send("Forced GC cycle completed.",ephemeral=True)


tree.add_command(job_group,guild=GUILD)
tree.add_command(prism_group,guild=GUILD) # prism integration
tree.add_command(calc_group,guild=GUILD)
tree.add_command(farm_group,guild=GUILD)

@client.event
async def on_ready():
    # When client is ready, register command tree
    await tree.sync(guild=GUILD)
    

with DeadlineHTTPCatcher() as srv:
    client.run(token=SECRET.bot_token)
