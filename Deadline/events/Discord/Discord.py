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

from Deadline.Jobs import Job
from Deadline.Events import DeadlineEventListener
from Deadline.Scripting import ClientUtils

def log_to_server(message, ip, extra_info = None):
    _adress = f"http://{ip}:1337"
    _dict = {"message" : message}
    if extra_info:
        _dict.update(extra_info)
    _data = parse.urlencode(_dict).encode()
    _request = request.Request(_adress, data=_data, method="POST")
    try:
        request.urlopen(_request)
    except:
        print("it ain't workin' chief")

def log_jobinfo_to_server(job: Job, ip):
    _adress = f"http://{ip}:1337"
    _dict = compose_job_dict(job)
    _data = parse.urlencode(_dict).encode()
    _request = request.Request(_adress, data=_data, method="POST")
    try:
        request.urlopen(_request)
    except:
        print("it ain't workin' chief")


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
        
        self.LogStdout("Discord event plugin noticed that a job has been submitted")
        log_to_server(f"A job, `{job.JobName}`, has been submitted!",self._ip, {"id" : job.JobId, "name" : job.JobName, "owner": job.GetJobExtraInfoKeyValueWithDefault("JobPing","everyone")})
        pass

    def OnJobStarted(self, job: Job):
        self._ip = self.get_ip()

        self.LogStdout("Discord event plugin noticed that a job has started")
        log_to_server(f"A job, `{job.JobName}`, has started",self._ip,{"id" : job.JobId, "name" : job.JobName, "owner": job.GetJobExtraInfoKeyValueWithDefault("JobPing","everyone"), "time" : str(int(time.time()))})
        pass
    
    def OnJobFinished(self, job: Job):
        self._ip = self.get_ip()
        
        self.LogStdout("Discord event plugin noticed that a job has finished")
        log_jobinfo_to_server(job,self._ip)
        pass

    def OnJobRequeued(self, job: Job):
        self._ip = self.get_ip()

        self.LogStdout("Discord event plugin noticed that a job has been requeued")
        log_to_server(f"Deadline noticed that `{job.JobName}` has been requeued",self._ip,{"id" : job.JobId, "name" : job.JobName, "owner": job.GetJobExtraInfoKeyValueWithDefault("JobPing","everyone")})
        pass

    def OnJobFailed(self, job: Job):
        self._ip = self.get_ip()

        self.LogStdout("Discord event plugin noticed that a job failed...")
        # log_to_server(f"Discord event plugin noticed that `{job.JobName}` failed... :fire:",self._ip)
        log_jobinfo_to_server(job,self._ip)
        pass

    def get_ip(self):
        name = self.GetConfigEntry("ServerName")
        return socket.gethostbyname(str(name))

def compose_job_dict(job: Job):
    return {
        "name" : job.JobName,
        "pool" : compose_poolstring(job.JobPool,job.JobSecondaryPool),
        "department" : job.JobDepartment,
        "tasks" : str(job.JobTaskCount),
        "status" : job.JobStatus,
        "id" : job.JobId,
        "thumbnail" : get_thumbnail(job),
        "ping" : job.GetJobExtraInfoKeyValueWithDefault("JobPing","")
    }

def get_imagepaths(job: Job):
    dir = job.JobOutputDirectories[0]
    out = []
    for dpath, dname, fnames in os.walk(dir):
        out.extend([os.path.join(dir,f) for f in fnames])
        break

    return out

def get_thumbnail(job: Job):
    paths = get_imagepaths(job)
    return paths[int(len(paths)/2)]

def compose_poolstring(pool: str, secondary_pool: str = None):
    if secondary_pool:
        return f"{pool}, {secondary_pool}"
    else:
        return pool

def GetDeadlineEventListener():
    return DiscordEventListener()

def CleanupDeadlineEventListener(event_listener: DiscordEventListener):
    event_listener.cleanup()


        