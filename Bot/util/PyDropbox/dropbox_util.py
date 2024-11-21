import asyncio
import os
import threading
import time
from pathlib import Path
from typing import Union

import dropbox
from dropbox.files import CommitInfo, UploadSessionCursor

from ..secret import Secret

app_key = Secret.dropbox_app_key
app_secret = Secret.dropbox_app_secret
oauth2_access_token = Secret.dropbox_oauth2_accesstoken


async def dropbox_big_upload(
    file_path: Union[str, Path], dropbox_path: str, timeout: int = 800, chunk: int = 4
):
    # do everything in own context
    # so this can be fired off into a threading.Thread, potentially.
    dbx = dropbox.Dropbox(
        app_key=app_key,
        app_secret=app_secret,
        oauth2_access_token=oauth2_access_token,
        timeout=timeout,
    )
    chunksize = chunk * (1024**2)  # 1024^2 bytes = 1 mb (chunk default = 4 mb)

    filesize = os.path.getsize(file_path)

    if filesize <= chunksize:
        with open(file_path, "rb") as file:
            dbx.files_upload(file.read(), dropbox_path)
        yield f"{filesize}/{filesize}"
    else:
        with open(file_path, "rb") as file:
            session = dbx.files_upload_session_start(file.read(chunksize))
            ssid = session.session_id
            cursor = UploadSessionCursor(ssid, file.tell())
            commit = CommitInfo(path=dropbox_path)
            while file.tell() < filesize:
                if (filesize - file.tell()) <= chunksize:
                    dbx.files_upload_session_finish(
                        file.read(chunksize), cursor, commit
                    )
                    break
                else:
                    dbx.files_upload_session_append_v2(file.read(chunksize), cursor)
                    cursor.offset = file.tell()
                    yield f"{file.tell()}/{filesize}"
        yield f"{filesize}/{filesize}"

    # Create a shared link
    shared_link_metadata = dbx.sharing_create_shared_link_with_settings(dropbox_path)
    yield shared_link_metadata.url


class DropBoxUpload:
    def __init__(
        self,
        file_path: Union[str, Path],
        dropbox_path: str,
        timeout: int = 800,
        chunk: int = 4,
    ):
        self._file_path = file_path
        self._dropbox_path = dropbox_path
        self._timeout = timeout
        self._chunk = chunk
        self._progress = None
        self._completion = None
        self._url = None
        self._done = False

    async def start_upload(self):
        self._done = False
        async for report in dropbox_big_upload(
            self._file_path, self._dropbox_path, self._timeout, self._chunk
        ):
            if report.startswith("http"):
                self._url = report
                continue
            self._completion = report
            uploaded, total = [float(x) for x in report.split("/")]
            self._progress = f"{(uploaded/total)*100:.2f}%"
        self._done = True
        return self._url

    @property
    def progress(self):
        if self._progress:
            return self._progress

    @property
    def completion(self):
        if self._completion:
            return self._completion

    @property
    def url(self):
        if self._url:
            return self._url

    @property
    def done(self):
        return self._done

    def _upload_in_new_loop(self):
        # effectively de-async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.start_upload())
        loop.close()

    async def start_upload_thread(self):
        t = threading.Thread(target=self._upload_in_new_loop, daemon=True)
        t.start()


async def demo():
    path = R"X:\_PROJECTS\ANI2_3D\project_TheSearch\04_Render\Shots\SET_1B_SH_75\EXR_new\SET_1B_SH_75.zip"
    goal = "/BOT/SET_1B_SH_75_3.zip"
    goal_2 = "/BOT/SET_1B_SH_75_4.zip"

    upload = DropBoxUpload(path, goal)
    upload_2 = DropBoxUpload(path, goal_2)

    async def report(ongoing_upload: DropBoxUpload, interval: float = 5):
        # while not ongoing_upload.done:
        while not ongoing_upload.done:
            if ongoing_upload.progress:
                print(
                    f"{os.path.basename(ongoing_upload._dropbox_path)} upload at",
                    ongoing_upload.progress,
                )
            time.time()
            await asyncio.sleep(interval)
        print("Done")

    print("Uploading!")
    upload_task = asyncio.create_task(upload.start_upload_thread())
    upload_task_2 = asyncio.create_task(upload_2.start_upload_thread())
    report_task = asyncio.create_task(report(upload))
    report_task_2 = asyncio.create_task(report(upload_2))

    await asyncio.gather(upload_task, upload_task_2, report_task, report_task_2)

    print("Url:", upload.url)
