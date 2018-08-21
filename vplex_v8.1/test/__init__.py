import asyncio
from asyncio import Future

async def a(future):
    await asyncio.sleep(1)
    future.set_result("add future result")

    return 2

async def b(x):
    await asyncio.sleep(1)
    return x


if __name__ =="__main__":
    loop = asyncio.get_event_loop()
    future =Future()
    asyncio.ensure_future(a(future))

    loop.run_until_complete(future)

    print(future.result())
    loop = asyncio.get_event_loop()
    task = loop.create_task(b(222))
    loop.run_until_complete(task)
    print (task.result())


