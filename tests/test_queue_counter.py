import asyncio
import importlib


def test_queue_counts():
    import ioc_checker.queue as queue
    importlib.reload(queue)

    async def run():
        await queue.add_task("ioc1", token="A")
        await queue.add_task("ioc2", token="A")
        await queue.add_task("ioc3", token="B")
        assert queue.get_queue_size("A") == "2/3"
        assert queue.get_queue_size("B") == "1/3"
        task_id = await queue.queue.get()
        task = queue.get_task(task_id)
        task.status = "processing"
        queue.queue.task_done()
        assert queue.get_queue_size("A") == "2/3"
        assert queue.get_queue_size("B") == "1/3"
        task.status = "done"
        assert queue.get_queue_size("A") == "1/2"
        assert queue.get_queue_size("B") == "1/2"

    asyncio.run(run())
