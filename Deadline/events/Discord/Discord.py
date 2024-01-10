# DISCORD INFORMATION GETTER!
# Listen to things and then submit them to discord bot.
# Quite the concept.
# A lot of notes were taken from the ShotGrid event plugin.

# FOR THOSE WONDERING ABOUT THE ABNORMAL SYNTAX:
# Deadline uses Python.NET which borrows a lot of stuff from C#
# Don't question it. They'll come get you.

import sys
from urllib import request, parse
from Deadline.Jobs import Job

from Deadline.Events import DeadlineEventListener
from Deadline.Scripting import ClientUtils

IP = "10.2.40.81"

def log_to_server(message):
    _adress = f"http://{IP}:1337"
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
        # self.OnJobStartedCallback += self.OnJobStarted
        self.OnJobFinishedCallback += self.OnJobFinished
        self.OnJobRequeuedCallback += self.OnJobRequeued
        self.OnJobFailedCallback += self.OnJobFailed


    def cleanup(self):
        del self.OnJobSubmittedCallback
        del self.OnJobFinishedCallback
        del self.OnJobRequeuedCallback
        del self.OnJobFailedCallback

    def OnJobSubmitted(self, job: Job):
        self.LogStdout("Discord event plugin noticed that a job has started")
        log_to_server("Discord event plugin noticed that a job has started")
        pass
    
    def OnJobFinished(self, job: Job):
        self.LogStdout("Discord event plugin noticed that a job has finished")
        log_to_server(f"Discord event plugin noticed that a job has finished, {job.JobStatus}, {job.JobName}")
        pass

    def OnJobRequeued(self, job: Job):
        self.LogStdout("Discord event plugin noticed that a job has been requeued")
        log_to_server(f"Discord event plugin noticed that a job has been requeued, {job.JobName}")
        pass

    def OnJobFailed(self, job: Job):
        self.LogStdout("Discord event plugin noticed that a job failed...")
        log_to_server("Discord event plugin noticed that a job failed...")
        pass

def GetDeadlineEventListener():
    return DiscordEventListener()

def CleanupDeadlineEventListener(event_listener: DiscordEventListener):
    event_listener.cleanup()


        