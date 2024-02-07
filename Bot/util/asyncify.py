import asyncio


def asyncify(function: callable, *args, **kwargs):
    """
    Turn a normal function into a task wrapping a coroutine.
    
    example:
    ```py
    task = asyncify(function, *args, **kwargs)
    await task
    result = task.result()
    ```
    """
    loop = asyncio.get_event_loop() # get current event loop
    coroutine = asyncio.to_thread(function,*args,**kwargs) # create coroutine from function
    task = loop.create_task(coroutine) # create task from function
    return task


async def asyncify_and_run(function: callable, *args, **kwargs):
    """
    Run a normal function async on the main event loop.

    Either use: 
    ```py
    result = await asyncify_and_run(function, *args, **kwargs)
    ```
    or
    ```py
    promise = asyncify_and_run(function, *args, **kwargs)
    # -- do stuff in meantime --
    result = await promise
    ```
    """
    
    task = asyncify(function,*args,**kwargs)
    await task
    res = task.result()
    return res