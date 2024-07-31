import logging
from p4p.client.thread import Context
from p4p.server import StaticProvider

# Configure logging
logging.basicConfig(level=logging.INFO)

class PVManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PVManager, cls).__new__(cls)
            cls._instance.pvs = {}
            cls._instance.provider = StaticProvider('digital_twin')
            cls._instance.context = Context('pva')  # Persistent context for efficiency
        return cls._instance

    def add_pv(self, name, pv):
        self.pvs[name] = pv
        self.provider.add(name, pv)
        logging.debug(f"Added PV {name}")

    async def update_pv(self, name, new_value):
        pv = self.pvs.get(name)
        if pv:
            try:
                logging.info(f"Updating PV {name} with value {new_value}")
                await self.context.put(name, new_value)  # Using persistent context
                logging.info(f"Successfully updated PV {name} with value {new_value}")
            except Exception as e:
                logging.error(f"Error updating PV {name}: {e}")
        else:
            logging.error(f"PV {name} not found")

    def remove_pv(self, name):
        pv = self.pvs.pop(name, None)
        if pv:
            self.provider.remove(name)
            logging.info(f"Removed PV {name}")

    def clear_pvs(self):
        self.pvs.clear()
        self.provider.clear()
        logging.info("Cleared all PVs")

    def get_pv(self, name):
        return self.pvs.get(name)

    def get_pv_list(self):
        return list(self.pvs.keys())

    def get_provider(self):
        return self.provider
