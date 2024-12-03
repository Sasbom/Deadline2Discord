import time
from dataclasses import dataclass, field, fields
from typing import List, Optional
from uuid import uuid4

import psycopg2 as pg
import psycopg2.extensions as pgtypes

from ..secret import Secret


@dataclass
class bot_user:
    name: str
    discordid: str
    roles: List[str] = field(default_factory=list)
    uuid: str = field(default=None)


@dataclass
class bot_job:
    deadline_name: str
    deadline_id: str
    started: int
    ended: Optional[int]
    group_id: str
    frames: int
    frame_start: int
    frame_end: int
    root: str
    owners: List[str] = field(default_factory=list)
    officehours: bool = field(default=False)
    officehours_start: str = field(default="9:00")
    officehours_end: str = field(default="18:00")
    done: bool = field(default=False)
    active: bool = field(default=True)
    uuid: str = field(default=None)


@dataclass
class bot_group:
    name: str
    members: List[str]
    owners: List[str]
    locked: bool = field(default=False)
    prism: bool = field(default=False)
    uuid: str = field(default=None)


@dataclass
class bot_zip:
    deadline_id: str
    is_zipped: bool = field(default=False)
    is_made_available: bool = field(default=False)
    zip_location: str = field(default="")
    download_url: str = field(default="")
    download_since: int = field(default=0)
    download_expires: int = field(default=0)


# ENSURE PRESENCE OF STUFF
def ensure_schema_tables(db: pgtypes.connection):
    with db.cursor() as cursor:
        user = Secret.pg_user
        schema = Secret.pg_schema
        cursor.execute(
            f"CREATE SCHEMA IF NOT EXISTS {schema}\n"
            f"    AUTHORIZATION {user};\n"
            "\n"
            f"GRANT USAGE ON SCHEMA {schema} TO PUBLIC;\n"
            "\n"
            f"GRANT ALL ON SCHEMA {schema} TO {user};\n"
        )
        db.commit()
        # User table.
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {schema}.users\n"
            "(\n"
            "    name text,\n"
            "    uuid uuid NOT NULL DEFAULT gen_random_uuid(),\n"
            "    roles text[],\n"
            "    discordid text,\n"
            "    CONSTRAINT unique_username UNIQUE (name)\n"
            ")\n"
        )
        db.commit()
        # Function to get admin users if owner field is left empty.
        cursor.execute(
            f"CREATE OR REPLACE FUNCTION {schema}.get_admin_users(\n"
            "	)\n"
            "    RETURNS text[]\n"
            "    LANGUAGE 'sql'\n"
            "    COST 100\n"
            "    VOLATILE PARALLEL UNSAFE\n"
            "AS $BODY$\n"
            "SELECT ARRAY( SELECT name FROM bot.users WHERE 'admin'=ANY(roles));\n"
            "$BODY$;\n"
        )
        db.commit()
        # Function to get current unix timestamp
        cursor.execute(
            f"CREATE OR REPLACE FUNCTION {schema}.unix_time(\n"
            "	)\n"
            "    RETURNS bigint\n"
            "    LANGUAGE 'sql'\n"
            "    COST 100\n"
            "    VOLATILE PARALLEL UNSAFE\n"
            "AS $BODY$\n"
            "SELECT extract(epoch from now());\n"
            "$BODY$;\n"
        )
        db.commit()
        # Jobs table
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {schema}.jobs\n"
            "(\n"
            "    uuid uuid NOT NULL DEFAULT gen_random_uuid(),\n"
            "    deadline_name text,\n"
            "    deadline_id text,\n"
            f"    started bigint DEFAULT {schema}.unix_time(),\n"
            "    ended bigint DEFAULT NULL,\n"
            "    group_id uuid DEFAULT NULL,\n"
            "    frames int,\n"
            "    frame_start int,\n"
            "    frame_end int,\n"
            "    root text,\n"
            "    officehours boolean,\n"
            "    officehours_start text,\n"
            "    officehours_end text,\n"
            "    done boolean,\n"
            "    active boolean,\n"
            f"    owners text[] DEFAULT {schema}.get_admin_users()\n"
            ");\n"
        )
        db.commit()
        # Group table
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {schema}.groups\n"
            "(\n"
            "    uuid uuid NOT NULL DEFAULT gen_random_uuid(),\n"
            "    name text,\n"
            "    members text[],\n"
            "    owners text[],\n"
            "    locked boolean,\n"
            "    prism boolean,\n"
            "    CONSTRAINT unique_groupname UNIQUE (name)\n"
            ");\n"
        )
        db.commit()
        # Download table
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {schema}.zip\n"
            "(\n"
            "    deadline_id text NOT NULL,\n"
            "    is_zipped boolean,\n"
            "    is_made_available boolean,\n"
            "    zip_location text,\n"
            "    download_url text,\n"
            "    download_since bigint,\n"
            "    download_expires bigint,\n"
            "    CONSTRAINT unique_deadline_id UNIQUE (deadline_id)\n"
            ");\n"
        )

        db.commit()


def ensure_name_available(db: pgtypes.connection, name):
    with db.cursor() as cursor:
        cursor.execute(
            f"SELECT ARRAY(SELECT name FROM {Secret.pg_schema}.groups UNION SELECT name FROM {Secret.pg_schema}.users) as names"
        )
        allnames = cursor.fetchone()[0]
    return name not in allnames


def insert_user(db: pgtypes.connection, user: bot_user):
    if not ensure_name_available(db, user.name):
        print("Name not unique")
        return
    with db.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO {Secret.pg_schema}.users (name, roles, discordid) VALUES (%s,%s,%s)",
            (user.name, user.roles, user.discordid),
        )
    db.commit()


def remove_user(db: pgtypes.connection, user: bot_user):
    with db.cursor() as cursor:
        cursor.execute(
            f"DELETE FROM {Secret.pg_schema}.users WHERE 'uuid'=%s", (user.uuid,)
        )
    db.commit()


def insert_group(db: pgtypes.connection, group: bot_group):
    if not ensure_name_available(db, group.name):
        print("Name not unique")
        return
    with db.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO {Secret.pg_schema}.groups (name, members, owners) VALUES (%s,%s::uuid[],%s::uuid[])",
            (group.name, group.members, group.owners),
        )
    db.commit()


def remove_group(db: pgtypes.connection, group: bot_group):
    with db.cursor() as cursor:
        cursor.execute(
            f"DELETE FROM {Secret.pg_schema}.groups WHERE 'uuid'=%s", (group.uuid,)
        )
    db.commit()


def insert_job(db: pgtypes.connection, job: bot_job):
    with db.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO {Secret.pg_schema}.jobs "
            "(deadline_name, deadline_id, root, owners, frames, group_id, frame_start, frame_end, officehours, officehours_start, officehours_end, done, active) "
            "VALUES (%s,%s,%s,%s,%s,%s::uuid,%s,%s,%s,%s,%s,%s,%s)",
            (
                job.deadline_name,
                job.deadline_id,
                job.root,
                job.owners,
                job.frames,
                job.group_id,
                job.frame_start,
                job.frame_end,
                job.officehours,
                job.officehours_start,
                job.officehours_end,
                job.done,
                job.active
            ),
        )
    db.commit()


def _ensure_unique_args(args: tuple):
    return sum(1 if a else 0 for a in args) == 1


def _valid_arg_id(args: tuple):
    for i, a in enumerate(args):
        if a:
            return i


def _dataclass_query(cls):
    return ",".join(f.name for f in fields(cls))


def _dataclass_updatestr(cls):
    """Formats as: "field1"=%s, "field2"=%s, ... excluding UUID"""
    data = [f.name for f in fields(cls) if f.name != "uuid"]
    return (", ".join(f'"{f}"=%s' for f in data), data)


def get_user(db: pgtypes.connection, username=None, discordid=None):
    args = (username, discordid)
    if not _ensure_unique_args(args):
        print("Please use only 1 keyword argument")
    valid_arg = _valid_arg_id(args)

    selectfields = _dataclass_query(bot_user)
    with db.cursor() as cursor:
        if valid_arg == 0:
            cursor.execute(
                f"SELECT {selectfields} FROM {Secret.pg_schema}.users WHERE name=%s LIMIT 1",
                (args[0],),
            )
        else:
            cursor.execute(
                f"SELECT {selectfields} FROM {Secret.pg_schema}.users WHERE discordid=%s LIMIT 1",
                (args[1],),
            )
        userdata = cursor.fetchone()
    if userdata:
        return bot_user(*userdata)  # forward all data into bot user
    else:
        return None


def get_group(db: pgtypes.connection, groupname=None, isprism=False):
    if groupname is None:
        return

    selectfields = _dataclass_query(bot_group)
    with db.cursor() as cursor:
        cursor.execute(
            f'SELECT {selectfields} FROM {Secret.pg_schema}.groups WHERE "name"=%s AND prism=%s LIMIT 1',
            (groupname, isprism),
        )
        groupdata = cursor.fetchone()
    if groupdata:
        return bot_group(*groupdata)
    else:
        return None


def get_groups(db: pgtypes.connection, prism=None):
    filterprism = ""
    if prism is not None:
        if prism:
            filterprism = "WHERE prism='true'"
        else:
            filterprism = "WHERE prism='false'"

    selectfields = _dataclass_query(bot_group)
    with db.cursor() as cursor:
        cursor.execute(
            f"SELECT {selectfields} FROM {Secret.pg_schema}.groups {filterprism} LIMIT 1"
        )
        groupsdata = cursor.fetchall()
    if groupsdata:
        return [bot_group(*data) for data in groupsdata]
    return None


def get_job(db: pgtypes.connection, deadline_name=None, deadline_id=None, uuid=None):
    args = (deadline_name, deadline_id, uuid)
    if not _ensure_unique_args(args):
        print("Please use only 1 keyword argument")
        return
    valid_arg = _valid_arg_id(args)
    selectfields = _dataclass_query(bot_job)
    with db.cursor() as cursor:
        if valid_arg == 0:
            cursor.execute(
                f"SELECT {selectfields} FROM {Secret.pg_schema}.jobs WHERE deadline_name=%s LIMIT 1",
                (args[0],),
            )
        elif valid_arg == 1:
            cursor.execute(
                f"SELECT {selectfields} FROM {Secret.pg_schema}.jobs WHERE deadline_id=%s LIMIT 1",
                (args[1],),
            )
        elif valid_arg == 2:
            cursor.execute(
                f"SELECT {selectfields} FROM {Secret.pg_schema}.jobs WHERE uuid=%s::uuid LIMIT 1",
                (args[2],),
            )
        jobdata = cursor.fetchone()
    if jobdata:
        return bot_job(*jobdata)
    else:
        return None


def get_zip(db: pgtypes.connection, job: str | bot_job):
    if isinstance(job, bot_job):
        job = job.deadline_id

    selectfields = _dataclass_query(bot_zip)
    with db.cursor() as cursor:
        cursor.execute(
            f"SELECT {selectfields} FROM {Secret.pg_schema}.zip WHERE deadline_id=%s LIMIT 1",
            (job,),
        )
        zipdata = cursor.fetchone()
    if zipdata:
        return bot_zip(*zipdata)
    else:
        return None
    

def get_out_of_date_zips(db: pgtypes.connection) -> list[bot_zip]:
    selectfields = _dataclass_query(bot_zip)
    with db.cursor() as cursor:
        cursor.execute(
            f"SELECT {selectfields} FROM {Secret.pg_schema}.zip WHERE is_made_available='true' AND download_expires < {Secret.pg_schema}.unix_time()"
        )
        zipsdata = cursor.fetchall()
    if zipsdata:
        return [bot_zip(*data) for data in zipsdata]
    return None


def construct_zip_from_job(db: pgtypes.connection, job: bot_job):
    if z := get_zip(db, job):
        return z

    zipobj = bot_zip(job.deadline_id,False,False,fR"{job.root}\{job.deadline_name}_{uuid4()}_zip.zip","",0,0)

    with db.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO {Secret.pg_schema}.zip "
            "(deadline_id, is_zipped, is_made_available, "
            "zip_location, download_url, download_since, "
            "download_expires) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (zipobj.deadline_id, zipobj.is_zipped, zipobj.is_made_available, 
             zipobj.zip_location, zipobj.download_url, zipobj.download_since, 
             zipobj.download_expires),
        )
    db.commit()

    return zipobj


def update_zip(db, zip: bot_zip):
    data = [f.name for f in fields(zip.__class__) if f.name != "deadline_id"]
    update, attrs = (", ".join(f'"{f}"=%s' for f in data), data)
    vals = [getattr(zip, a) for a in attrs]
    vals.append(zip.deadline_id)
    t_vals = tuple(vals)
    with db.cursor() as cursor:
        cursor.execute(
            f"UPDATE {Secret.pg_schema}.zip SET {update} WHERE deadline_id=%s;", t_vals
        )
    db.commit()


def remove_zip(db: pgtypes.connection, zip: bot_zip):
    with db.cursor() as cursor:
        cursor.execute(
            f"DELETE FROM {Secret.pg_schema}.zip WHERE deadline_id=%s", (zip.deadline_id,)
        )
    db.commit()


def get_jobs_user(
    db: pgtypes.connection,
    user: bot_user,
    get_expired: bool = True,
    get_done: bool = True,
):
    now = int(time.time())
    expired = ""
    if not get_expired:
        expired = f" AND ended <= {now}"

    done = "AND done = 'false'"
    if not get_done:
        done = " AND done = 'true'"

    selectfields = _dataclass_query(bot_job)
    with db.cursor() as cursor:
        cursor.execute(
            f"SELECT {selectfields} FROM {Secret.pg_schema}.jobs WHERE %s = ANY(owners) {expired}{done};",
            (user.name,),
        )
        jobsdata = cursor.fetchall()
    if jobsdata:
        return [bot_job(*data) for data in jobsdata]
    return None


def get_officehours_jobs(db: pgtypes.connection):
    selectfields = _dataclass_query(bot_job)
    with db.cursor() as cursor:
        cursor.execute(
            f"SELECT {selectfields} FROM {Secret.pg_schema}.jobs WHERE officehours = 'true' AND 'done' = 'false';"
        )
        jobsdata = cursor.fetchall()
    if jobsdata:
        return [bot_job(*data) for data in jobsdata]
    return None


def get_jobids(db: pgtypes.connection):
    """Get all job ids not marked as done."""
    with db.cursor() as cursor:
        cursor.execute(
            f"SELECT deadline_id FROM {Secret.pg_schema}.jobs WHERE done = 'false';"
        )
        data = [job[0] for job in cursor.fetchall()]

    if data:
        return data
    return None


def update_job(db: pgtypes.connection, job: bot_job):
    update, attrs = _dataclass_updatestr(bot_job)
    vals = [getattr(job, a) for a in attrs]
    vals.append(job.uuid)
    t_vals = tuple(vals)
    with db.cursor() as cursor:
        cursor.execute(
            f"UPDATE {Secret.pg_schema}.jobs SET {update} WHERE uuid=%s;", t_vals
        )
    db.commit()


def update_group(db: pgtypes.connection, group: bot_group):
    update, attrs = _dataclass_updatestr(bot_group)
    vals = [getattr(group, a) for a in attrs]
    vals.append(group.uuid)
    t_vals = tuple(vals)
    with db.cursor() as cursor:
        cursor.execute(
            f"UPDATE {Secret.pg_schema}.groups SET {update} WHERE uuid=%s;", t_vals
        )
    db.commit()


def user_uuid(db: pgtypes.connection, name):
    with db.cursor() as cursor:
        cursor.execute(
            f"SELECT uuid FROM {Secret.pg_schema}.users WHERE name=%s;", (name,)
        )
        uuid = cursor.fetchone()[0]
    return uuid


def connect() -> pgtypes.connection:
    db = pg.connect(
        f"host={Secret.pg_address} user={Secret.pg_user} password={Secret.pg_password} dbname={Secret.pg_database} port={Secret.pg_port}"
    )
    ensure_schema_tables(db)
    return db
