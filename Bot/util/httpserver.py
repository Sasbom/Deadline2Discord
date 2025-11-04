import json
import socket
import threading
import time
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import parse
import discord

from . import secret
from .database import DB
from .message_cache import MESSAGES
from .pg import postgrease as pg
from . import exr_helper as exr
from .image_optimize import optimize_image
SECRET = secret.Secret


def compose_resultembed(
    data_dict: dict[str, str],
) -> tuple[discord.Embed, str, discord.File, str]:
    has_failed = data_dict["status"] == "Failed"

    msg_color = (
        discord.Colour.from_rgb(255, 0, 0)
        if has_failed
        else discord.Colour.from_rgb(0, 255, 0)
    )
    embed_title = "Job Failed! :fire::fire::fire:" if has_failed else "Job Finished!"
    embed_title_emote = ":fire:" if has_failed else ":white_check_mark:"
    embed_title = f"`{data_dict['name']}`{embed_title_emote}\n{embed_title}"

    embed_description = (
        f"The farm has {data_dict['status'].lower()} job `{data_dict['name']}`."
    )

    embed = discord.Embed(
        title=embed_title, color=msg_color, description=embed_description
    )

    embed.add_field(name=":abcd: Name: ", value=data_dict["name"])
    embed.add_field(name=":ocean: Pool: ", value=data_dict["pool"])

    if "department" not in data_dict.keys():
        data_dict["department"] = "[no department]"

    embed.add_field(
        name=":classical_building: Department: ",
        value=data_dict["department"],
        inline=False,
    )
    embed.add_field(name=":pray: Status: ", value=data_dict["status"])
    embed.add_field(name=":1234: Tasks: ", value=data_dict["tasks"])
    embed.add_field(name=":calendar: Time finished:", value=get_timestamp_now())

    user_id = None
    tag_message = None
    if "ping" in data_dict.keys():
        if names := data_dict["ping"]:
            # set comprehension for unique names
            name_list = {n.strip() for n in names.split(",")}
            user_ids = []
            for name in name_list:
                # if user_id := DB.get(user.name == name):
                if user_id := pg.get_user(DB, username=name):
                    user_ids.append(user_id.discordid)

            if user_ids:
                users = ", ".join(f"<@{user_id}>" for user_id in user_ids)
                emote = "⚠" if data_dict["status"] == "Failed" else "🍳"
                embed.add_field(
                    name=":speaking_head: User(s): ", value=users, inline=False
                )
                tag_message = f"{emote} Render {data_dict['status']}! {users}"
    if "group" in data_dict.keys():
        embed.add_field(name=":factory: Channel:", value=data_dict["group"])

    file = None
    filename = None
    if "thumbnail" in data_dict.keys() and not has_failed:
        filename = data_dict["thumbnail"]
        # EXR conversion.
        filename_path = Path(filename)
        if not filename_path.suffix:
            # sometimes, some unfortunate people publish things without an extension.
            folder = filename_path.parent
            files = os.listdir(folder)
            filename_it = iter(f for f in files if str(filename_path) in f)
            file = next(filename_it, None)
            if file:
                filename_path = folder / file
                filename = str(filename_path)
        
        file_upload = filename

        if filename_path.suffix in (".exr",".EXR"):
            result = exr.convert_exr_to_png(file_upload)
            if result:
                exr_filename = str(result)
                if (os.stat(filename_path).st_size/ 1_000_000) > 7.5:
                    exr_filename = str(optimize_image(result))
                file = discord.File(exr_filename)
            else:
                if (os.stat(filename_path).st_size/ 1_000_000) > 7.5:
                    file_upload = str(optimize_image(filename_path))
                file = discord.File(file_upload)
        else:
            if (os.stat(filename_path).st_size/ 1_000_000) > 7.5:
                file_upload = str(optimize_image(filename_path))
            file = discord.File(file_upload)

    return embed, tag_message, file, filename


def get_timestamp_now() -> str:
    return f"<t:{int(time.time())}:f>"


def framelist(framestr: str):
    parts = [p.strip() for p in framestr.split(",")]
    collect = []
    for p in parts:
        if "-" in p:
            i, o = [int(x) for x in p.split("-")]
            collect.extend(range(i,o+1))
        else:
            collect.append(int(p))
    return collect


class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        data = self.rfile.read(length).decode()
        data_dict = parse.parse_qs(data)

        self.send_response(200)

        self.send_header("Content-type", "application/json")
        self.end_headers()

        if "message" in data_dict.keys():
            print(f"Recieved message: {data_dict['message'][0]}")
            self.wfile.write(
                json.dumps(
                    {"message": f"Message recieved: {data_dict['message'][0]}"}
                ).encode()
            )

            job_group_id = None
            job_name = data_dict["name"][0]
            job_id = data_dict["id"][0]
            job_owner = SECRET.default_user
            if "owner" in data_dict.keys():
                job_owner = data_dict["owner"][0]
            job_time = "0"
            if "time" in data_dict.keys():
                job_time = data_dict["time"][0]
            job_frames = [0]
            if "frames" in data_dict.keys():
                job_frames = sorted(framelist(data_dict["frames"][0]))
            if "prism_project" in data_dict.keys():
                job_prism_project = data_dict["prism_project"][0]
                job_group_id = pg.get_group(DB, job_prism_project, True).uuid

            job_info = pg.get_job(DB, deadline_name=job_name)


            if not job_info:
                # DB.insert(
                #     {
                #         "job_name": f"{job_name}",
                #         "job_id": f"{job_id}",
                #         "job_owner": f"{job_owner}",
                #         "job_time": f"{job_time}",
                #     }
                # )
                owner_list_raw = [o.strip() for o in job_owner.split(",")]
                owner_list = list()
                #print(job_group_id)
                for owner in owner_list_raw:
                    if owner.startswith("project:") and job_group_id is None:
                        group = owner.removeprefix("project:")
                        #print(group)
                        grp = pg.get_group(DB,group,isprism=False)
                        #print(grp)
                        if grp is None:
                            continue
                        members = grp.members
                        job_group_id = grp.uuid
                        owner_list.extend(members)
                        continue
                    owner_list.append(owner)

                new_job = pg.bot_job(
                    deadline_name=job_name,
                    deadline_id=job_id,
                    started=int(job_time),
                    owners=owner_list,
                    ended=None,
                    frames=len(job_frames),
                    frame_start=job_frames[0],
                    frame_end=job_frames[-1],
                    group_id=job_group_id,
                    root=data_dict["dir"][0],
                    done=False,
                )
                pg.insert_job(DB, new_job)
            else:
                job: pg.bot_job = pg.get_job(DB,deadline_name=job_name)
                job.deadline_id = job_id

                if job_time != "0":
                    job.started = int(job_time)
                pg.update_job(DB, job)

            MESSAGES.post_message(
                f"{data_dict['message'][0]} - :calendar:{get_timestamp_now()}"
            )
        elif "request_prismusers" in data_dict.keys():
            print(
                f"Recieved request for users associated with Prism project {data_dict['request_prismusers'][0]}"
            )
            users = ""
            prism_project_name = data_dict["request_prismusers"][0]

            p: pg.bot_group = pg.get_group(DB, prism_project_name, isprism=True)
            if p is not None:
                users = ",".join(p.members)

            self.wfile.write(users.encode())

        else:
            data_dict = {k: v[0] for k, v in data_dict.items()}  # get first of all.

            owner_list_raw = [o.strip() for o in data_dict["ping"].split(",")]
            owner_list = list()
            #print(job_group_id)
            has_group = False
            for owner in owner_list_raw and not has_group:
                if owner.startswith("project:"):
                    group = owner.removeprefix("project:")
                    #print(group)
                    grp = pg.get_group(DB,group,isprism=False)
                    #print(grp)
                    if grp is None:
                        continue
                    members = grp.members
                    job_group_id = grp.uuid
                    owner_list.extend(members)
                    has_group = True
                    data_dict["group"] = grp.name
                    continue
                owner_list.append(owner)
            data_dict["ping"] = ", ".join(owner_list)

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


IP = socket.gethostbyname(socket.gethostname())

SERVER = ThreadingHTTPServer((IP, SECRET.internal_http_port), RequestHandler)


def run_server():
    SERVER.serve_forever()


THREAD = threading.Thread(target=run_server)


class DeadlineHTTPCatcher:
    def __init__(self):
        self.IP = IP

    def __enter__(self) -> ThreadingHTTPServer:
        THREAD.start()
        return SERVER

    def __exit__(self, *args):
        SERVER.shutdown()
        THREAD.join()
