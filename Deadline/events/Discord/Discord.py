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

from Deadline.Jobs import Job
from Deadline.Events import DeadlineEventListener
from Deadline.Scripting import ClientUtils

def log_to_server(message, ip):
    _adress = f"http://{ip}:1337"
    _dict = {"message" : message}
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
        self._ip = self.GetConfigEntry("ServerIP")
        
        self.LogStdout("Discord event plugin noticed that a job has been submitted")
        log_to_server(f"Discord event plugin noticed that a job has been submitted",self._ip)
        pass

    def OnJobStarted(self, job: Job):
        self._ip = self.GetConfigEntry("ServerIP")

        self.LogStdout("Discord event plugin noticed that a job has started")
        log_to_server(f"Discord event plugin noticed that a job has started",self._ip)
        pass
    
    def OnJobFinished(self, job: Job):
        self._ip = self.GetConfigEntry("ServerIP")

        self.LogStdout("Discord event plugin noticed that a job has finished")
        log_to_server(f"Discord event plugin noticed that a job has finished, {job.JobStatus}, {job.JobName}",self._ip)
        pass

    def OnJobRequeued(self, job: Job):
        self._ip = self.GetConfigEntry("ServerIP")

        self.LogStdout("Discord event plugin noticed that a job has been requeued")
        log_to_server(f"Discord event plugin noticed that a job has been requeued, {job.JobName}",self._ip)
        pass

    def OnJobFailed(self, job: Job):
        self._ip = self.GetConfigEntry("ServerIP")

        self.LogStdout("Discord event plugin noticed that a job failed...")
        log_to_server("Discord event plugin noticed that a job failed...",self._ip)
        pass

def GetDeadlineEventListener():
    return DiscordEventListener()

def CleanupDeadlineEventListener(event_listener: DiscordEventListener):
    event_listener.cleanup()


        