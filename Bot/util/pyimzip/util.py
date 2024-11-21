import asyncio
import sys

from . import image_zip


class ImageZipProcess:
    def __init__(self, folder: str, archivename: str):
        self._folder = folder
        self._archivename = archivename
        self._process = None
        self._completion = None
        self._progress = None
        self._path = None
        self._done = False

    async def start_zipping(self):
        self._done = False
        self._process = await image_zip.start_async_process(
            self._folder, self._archivename
        )
        waiting = asyncio.Task(image_zip.await_completion(self._process))
        syncing = asyncio.Task(self._sync_with_process())

        await asyncio.gather(waiting, syncing)
        self._process = None
        self._done = True
        return self._path

    async def _sync_with_process(self):
        if self._process is None:
            return
        async for out in image_zip.yield_output_parsed(self._process):
            if out[1]:
                self._completion, self._progress = out
            elif "Done" not in out[0]:
                res = out[0]
                if sys.platform in ("win32", "cygwin", "nt"):
                    res = res.replace("/", "\\")
                self._path = res

    @property
    def progress(self):
        if self._process is None:
            return
        return self._progress

    @property
    def completion(self):
        if self._process is None:
            return
        return self._completion

    @property
    def path(self):
        if self._process is None or self._path is None:
            return
        return self._path

    @property
    def done(self):
        return self._done


async def demo_function():
    """Creates an ImageZipProcess and every 2 seconds, poll data from it"""
    zip = ImageZipProcess(
        R"..\Shots\SET_1B_SH_75\EXR_new",
        "SET_1B_SH_75.zip",
    )

    async def poll_zip_task(zip: ImageZipProcess):
        while not zip.done:
            print("progress:", zip.progress)
            await asyncio.sleep(2)

    waiting = asyncio.Task(zip.start_zipping())
    printing = asyncio.Task(poll_zip_task(zip))

    await asyncio.gather(waiting, printing)
