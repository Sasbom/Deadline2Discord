import asyncio
import subprocess as sp
import sys
from asyncio.subprocess import Process

_EXEC = None
if sys.platform in ("win32", "cygwin", "nt"):
    _EXEC = "zip_imagefolder.exe"
elif sys.platform == "linux":
    _EXEC = "zip_imagefolder"


def impzip_set_executable(location: str):
    """Modify executable location"""
    _EXEC = location


async def start_async_process(folder: str, archivename: str):
    """Schedules the Image Zip async process"""
    process = await asyncio.create_subprocess_exec(
        _EXEC,
        "-dir",
        folder,
        "-out",
        archivename,
        stdout=sp.PIPE,
    )
    return process


async def await_completion(process: Process):
    """Awaits process exit and prints code."""
    await process.wait()
    print("Process exited with exit code", process.returncode)


async def yield_output(process: Process):
    """Read output and return as strings"""
    while process.returncode is None:
        stdout_line = await process.stdout.readline()
        out = stdout_line.decode().strip()
        if out:
            yield out
        else:
            break


async def yield_output_parsed(process: Process):
    """Read output and return a tuple of item/total and percentage"""
    while process.returncode is None:
        stdout_line = await process.stdout.readline()
        out = stdout_line.decode().strip()
        if out:
            percent = ""
            if "/" in out and "\\" not in out:
                item, total = [float(a) for a in out.split("/")]
                percent = f"{(item/total)*100:.2f}%"
            yield (out, percent)
        else:
            break


async def print_out_process(process: Process):
    """Use the asynchronous iterator to print results as they come in"""
    async for out in yield_output_parsed(process):
        print(out)


async def _demo():
    # Gets a folder, zips it and prints out output from the executable
    proc = await start_async_process(
        R"..\04_Render\Shots\SET_1B_SH_75\EXR_new",
        "SET_1B_SH_75.zip",
    )
    waiting = asyncio.Task(await_completion(proc))
    printing = asyncio.Task(print_out_process(proc))
    print("stuff can run here uninterrupted")
    await asyncio.gather(waiting, printing)


# if __name__ == "__main__":
#     asyncio.run(main())
