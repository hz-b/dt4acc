from p4p.client.thread import Context
from p4p.server import StaticProvider


class PVManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PVManager, cls).__new__(cls)
            cls._instance.pvs = {}
            cls._instance.provider = StaticProvider('digital_twin')  # 'abc' is an arbitrary name
        return cls._instance

    def add_pv(self, name, pv):
        self.pvs[name] = pv
        self.provider.add(name, pv)

    def update_pv(self, name, new_value, ctx=None):
        if ctx is None:
            ctx = Context('pva')
        pv = self.pvs.get(name)
        if pv:
            ctx.put(name, new_value)
        else:
            print(f"PV {name} not found")

    def remove_pv(self, name):
        pv = self.pvs.pop(name, None)
        if pv:
            self.provider.remove(name)

    def clear_pvs(self):
        self.pvs.clear()
        self.provider.clear()

    def get_pv(self, name):
        return self.pvs.get(name)

    def get_pv_list(self):
        return list(self.pvs.keys())

    def get_provider(self):
        return self.provider
