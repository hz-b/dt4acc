import asyncio

from p4p.client.asyncio import Context

class ContextProxy:
    def __init__(self, context):
        assert context == "pva"
        self.context = Context(context)

    async def put(self, *args, timeout=5, **kwargs):
        return await asyncio.wait_for(
            self.context.put(*args, **kwargs),
            timeout=timeout
        )

    async def get(self, id_: str, timeout: float = 5) -> [int, float]:
        """

        Todo:
            add typing for what all types that could be returned
        """
        return await asyncio.wait_for(self.context.get(id_), timeout=timeout)
