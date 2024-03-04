from collections import UserList


class Event(UserList):
    def append(self, item):
        assert (callable(item))
        super().append(item)

    def trigger(self, obj):
        for callback in self:
            callback(obj)


class StatusChange(Event):
    def trigger(self, flag: bool):
        return super().trigger(flag)