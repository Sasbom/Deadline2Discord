# DISCORD INFORMATION GETTER!
# Listen to things and then submit them to discord bot.
# Quite the concept.
# A lot of notes were taken from the ShotGrid event plugin.

# FOR THOSE WONDERING ABOUT THE ABNORMAL SYNTAX:
# Deadline uses Python.NET which borrows a lot of stuff from C#
# Don't question it. They'll come get you.

import sys
from Deadline.Jobs import Job

from Deadline.events import DeadlineEventListener

class DiscordEventListener(DeadlineEventListener):

    def __init__(self):
        if sys.version_info.major == 3:
            super(self,DiscordEventListener).__init__()

        # The bot needs to report only on finished jobs and on failed jobs.

        self.OnJobSubmittedCallback += self.OnJobSubmitted
        # self.OnJobStartedCallback += self.OnJobStarted
        self.OnJobFinishedCallback += self.OnJobFinished
        # self.OnJobRequeuedCallback += self.OnJobRequeued
        self.OnJobFailedCallback += self.OnJobFailed

    def cleanup(self):
        del self.OnJobSubmittedCallback
        del self.OnJobFinishedCallback
        del self.OnJobFailedCallback

    def OnJobSubmitted(self, job: Job):
        print("Discord event plugin noticed that a job has started")
        pass
    
    def OnJobFinished(self, job: Job):
        print("Discord event plugin noticed that a job has finished")
        pass

    def OnJobFailed(self, job: Job):
        print("Discord event plugin noticed that a job failed...")
        pass

def GetDeadlineEventListener():
    return DiscordEventListener()

def CleanupDeadlineEventListener(event_listener: DiscordEventListener):
    event_listener.cleanup()


        