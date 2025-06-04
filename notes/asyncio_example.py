import asyncio
import time

print("Starting test script...")


async def wait_some_time(marker: str, period_ms: int = 1000):
    print(f"Waiting {period_ms} ms for {marker}...")
    await asyncio.sleep(period_ms / 1000)
    print(f"Done waiting {marker} for {period_ms} ms.")
    return

async def series_fn():
    start_time = time.time()
    print("Series function started.")
    await wait_some_time("1A", 3000)
    await wait_some_time("2A", 1500)
    await wait_some_time("3A", 4500)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print("🔥Series function completed in %.2f seconds." % elapsed_time)

async def parallel_fn():
    start_time = time.time()
    print("parallel function started.")
    # Schedule all wait_some_time calls concurrently:
    task1 = asyncio.create_task(wait_some_time("1B", 3000))
    task2 = asyncio.create_task(wait_some_time("2B", 1500))
    task3 = asyncio.create_task(wait_some_time("3B", 4500))
    # Wait until all tasks complete in parallel.
    await asyncio.gather(task1, task2, task3)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print("🔥parallel function completed in %.2f seconds." % elapsed_time)

def run_free_fn():
    start_time = time.time()
    print("run free function started.")
    # Schedule tasks without awaiting them.
    asyncio.create_task(wait_some_time("1C", 3000))
    asyncio.create_task(wait_some_time("2C", 1500))
    asyncio.create_task(wait_some_time("3C", 4500))
    end_time = time.time()
    elapsed_time = end_time - start_time
    print("🔥run free function started in %.2f seconds." % elapsed_time)

async def main():
    print("Starting main function.")
    run_free_fn()
    await parallel_fn()
    await series_fn()
    print("Main function completed.")

asyncio.run(main())

print("Test script completed.")