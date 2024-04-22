from collections import UserList


class Event(UserList):
    def append(self, item):
        assert (callable(item))
        super().append(item)

    async def trigger(self, obj):
        for callback in self:
            if obj == None:
                return
            else:
                await callback(obj)


class StatusChange(Event):
    async def trigger(self, flag: bool):
        return await super().trigger(flag)
