# DISCORD INFORMATION GETTER!
# Listen to things and then submit them to discord bot.
# Quite the concept.
# A lot of notes were taken from the ShotGrid event plugin.

# FOR THOSE WONDERING ABOUT THE ABNORMAL SYNTAX:
# Deadline uses Python.NET which borrows a lot of stuff from C#
# Don't question it. They'll come get you.

import sys
import socket
from urllib import request, parse
import os
import time
import re
import json

from Deadline.Jobs import Job
from Deadline.Events import DeadlineEventListener
from Deadline.Scripting import ClientUtils

REGEX_FILE = re.compile(r"([\w]+)_([#]+).([\w]+)")

def _log_msg_to_server(message):
    with open(R"X:\_DEPLOY\log\dline_log.txt","a") as f:
        f.write(f"{message}\n")

def log_to_server(message, ip, port, extra_info = None):
    _adress = f"http://{ip}:{port}"
    _dict = {"message" : message}
    if extra_info:
        _dict.update(extra_info)
    _data = parse.urlencode(_dict).encode()
    _request = request.Request(_adress, data=_data, method="POST")
    try:
        request.urlopen(_request)
    except:
        print("it ain't workin' chief")

def log_jobinfo_to_server(job: Job, ip, port):
    _adress = f"http://{ip}:{port}"
    _dict = compose_job_dict(job,ip,port)
    _data = parse.urlencode(_dict).encode()
    _request = request.Request(_adress, data=_data, method="POST")
    try:
        request.urlopen(_request)
    except:
        print("it ain't workin' chief")

def request_prism_users(prism_project_name: str, ip: str, port):
    _adress = f"http://{ip}:{port}"
    _dict = {"request_prismusers" : prism_project_name}
    _data = parse.urlencode(_dict).encode()
    _request = request.Request(_adress, data=_data, method="POST")
    try:
        with request.urlopen(_request) as result:
            users = result.read().decode()
            print(users,prism_project_name)
        return users 
    except:
        print("it ain't workin' chief")
        return ""


class DiscordEventListener(DeadlineEventListener):

    def __init__(self):
        if sys.version_info.major == 3:
            super().__init__()

        # The bot needs to report only on finished jobs and on failed jobs.

        self.OnJobSubmittedCallback += self.OnJobSubmitted
        self.OnJobStartedCallback += self.OnJobStarted
        self.OnJobFinishedCallback += self.OnJobFinished
        self.OnJobRequeuedCallback += self.OnJobRequeued
        self.OnJobFailedCallback += self.OnJobFailed

    def cleanup(self):
        del self.OnJobStartedCallback
        del self.OnJobSubmittedCallback
        del self.OnJobFinishedCallback
        del self.OnJobRequeuedCallback
        del self.OnJobFailedCallback

    def OnJobSubmitted(self, job: Job):
        self._ip = self.get_ip()
        self._port = self.get_port()
        self.LogStdout("Discord event plugin noticed that a job has been submitted")

        owner = get_owner(job, self._ip, self._port)

        log_to_server(f"A job, `{job.JobName}`, has been submitted!",self._ip, self._port, {"id" : job.JobId, "name" : job.JobName, "owner": owner})
        pass

    def OnJobStarted(self, job: Job):
        self._ip = self.get_ip()
        self._port = self.get_port()
        self.LogStdout("Discord event plugin noticed that a job has started")

        prism_file = job.GetJobEnvironmentKeyValue("prism_project")
        self.LogStdout("prism file " + str(prism_file))

        owner = get_owner(job, self._ip, self._port)
    
        log_to_server(f"A job, `{job.JobName}`, has started!",self._ip,self._port,{"id" : job.JobId, "name" : job.JobName, "owner": owner, "time" : str(int(time.time()))})
        pass
    
    def OnJobFinished(self, job: Job):
        self._ip = self.get_ip()
        self._port = self.get_port()
        self.LogStdout("Discord event plugin noticed that a job has finished")
        #_log_msg_to_server(f"finished: {job.JobName}")
        log_jobinfo_to_server(job,self._ip,self._port)
        pass

    def OnJobRequeued(self, job: Job):
        self._ip = self.get_ip()
        self._port = self.get_port()

        owner = get_owner(job, self._ip, self._port)

        self.LogStdout("Discord event plugin noticed that a job has been requeued")
        log_to_server(f"Deadline noticed that `{job.JobName}` has been requeued",self._ip,self._port,{"id" : job.JobId, "name" : job.JobName, "owner": owner})
        pass

    def OnJobFailed(self, job: Job):
        self._ip = self.get_ip()
        self._port = self.get_port()
        self.LogStdout("Discord event plugin noticed that a job failed...")
        # log_to_server(f"Discord event plugin noticed that `{job.JobName}` failed... :fire:",self._ip)
        log_jobinfo_to_server(job,self._ip,self._port)
        pass

    def get_ip(self):
        name = self.GetConfigEntry("ServerName")
        return socket.gethostbyname(str(name))

    def get_port(self):
        port = self.GetConfigEntryWithDefault("ServerPort","1337")
        return port

def compose_job_dict(job: Job, ip, port):
    owner = get_owner(job, ip, port)
    
    return {
        "name" : job.JobName,
        "pool" : compose_poolstring(job.JobPool,job.JobSecondaryPool),
        "department" : job.JobDepartment,
        "tasks" : str(job.JobTaskCount),
        "status" : job.JobStatus,
        "id" : job.JobId,
        "thumbnail" : str(get_thumbnail(job)),
        "ping" : str(owner)
    }

def get_imagepaths(job: Job):
    dir = job.JobOutputDirectories[0]
    
    fname = job.GetJobInfoKeyValue("OutputFilename0")
    if not fname or not dir:
        return None

    print(f"output? {fname}")
    fname_match = re.match(REGEX_FILE,fname)
    strlookup = None
    if fname_match is not None:
        strlookup = fname_match.group(1)
        print(strlookup)

    _log_msg_to_server(f"{dir}\n{fname}\n{strlookup}")

    out = []
    for dpath, dname, fnames in os.walk(dir):
        if strlookup:
            out.extend([os.path.join(dir,f) for f in fnames if strlookup in f])
        else:
            out.extend([os.path.join(dir,f) for f in fnames])
        break

    _log_msg_to_server(f"{out}")

    return out

def get_thumbnail(job: Job):
    paths = get_imagepaths(job)
    if paths:
        if len(paths) == 1:
            return paths[0]
        return paths[int(len(paths)/2)]
    return ""

def compose_poolstring(pool: str, secondary_pool: str = None):
    if secondary_pool:
        return f"{pool}, {secondary_pool}"
    else:
        return pool

def GetDeadlineEventListener():
    return DiscordEventListener()

def CleanupDeadlineEventListener(event_listener: DiscordEventListener):
    event_listener.cleanup()

def detect_prism_job(job: Job):
    prism_file = job.GetJobEnvironmentKeyValue("prism_project")
    _log_msg_to_server(prism_file)
    if not prism_file:
        return None
    project_name = None
    _log_msg_to_server("accessing prism file")
    with open(prism_file,"r") as f:
        data = json.load(f)
        _log_msg_to_server(f"{data}")
        project_name = data["globals"]["project_name"]

    return project_name

def get_owner(job : Job, ip, port):
    owner = job.GetJobExtraInfoKeyValueWithDefault("JobPing","None")
    if owner == "None":
        # Chance it might be a prism job.
        if prism_name := detect_prism_job(job):
            print("getting prism users")
            owner = request_prism_users(prism_name,ip,port)
        else:
            owner = "everyone"

    return owner