import asyncio
import logging
import time
import tracemalloc

from p4p.nt import NTScalar
from p4p.server import Server
from p4p.server.asyncio import SharedPV

import dt4acc.command as cmd
from dt4acc.resources.bessy2_sr_reflat import bessy2Lattice
from dt4acc.setup_configuration.pv_manager import PVManager

help_type = NTScalar('s')
types = {
    'int': NTScalar('i').wrap(0),
    'float': NTScalar('d').wrap(0.0),
    'str': NTScalar('s').wrap(''),
    'array': NTScalar('ad').wrap([0.0, 0.0]),
    'bool': NTScalar('b').wrap(False),
    'bool_array': NTScalar('ab').wrap([])
}


# Define a handler class for handling write requests to the PV
class ElementHandler(object):
    def __init__(self, element):
        self.element = element

    def rpc(self, pv, op):
        V = op.value()
        print("RPC", V, V.query.get('help'), V.query.get('newtype'))
        if V.query.get('help') is not None:
            op.done(help_type.wrap('Try newtype=int (or float or str)'))
            return

        newtype = types[V.query.newtype]

        op.done(help_type.wrap('Success'))

        pv.close()  # disconnect client
        pv.open(newtype)

    async def put(self, pv, op):
        val = op.value()
        logging.warning("Assign %s = %s", op.name(), val)
        # Notify any subscribers of the new value.
        # Also set timeStamp with current system time.
        pv.post(val, timestamp=time.time())
        # Notify the client making this PUT operation that it has now completed
        if isinstance(self.element, str):
            FamName = self.element
        else:
            FamName = self.element.FamName
        await cmd.update(element_id=FamName, property_name="dx", value=float(op.value()))
        op.done()


def create_pv(initial_value_type, initial_type, element):
    initial = types[initial_value_type]
    pv = SharedPV(nt=NTScalar(initial_type), initial=initial, handler=ElementHandler(element))
    return pv


async def server_start_up():
    # Get the PVManager instance
    manager = PVManager()

    # Iterate over each element in the accelerator list and add shared PVs

    # todo: change the lattice reading to use db (lat2db)
    acc = bessy2Lattice()
    prefix = "Pierre:DT:"
    for element in acc:
        # todo: once lattice is read from db then play with sequences instead of this AT format.
        element_str = str(element)
        element_split_by_space = element_str.split('\n')
        element_type = element_split_by_space[0]
        if element_type in ["Quadrupole:", "Sextupole:"]:
            pv_name = prefix + element.FamName
            cm_pv_name = pv_name + ":Cm:set"
            # todo: what values should the array start with?
            #   1 -> maybe read from a db where defaults for each pv are stored
            #   2 -> another alternative can be to read from machine if available
            #   Finally use a pattern to separate the different options (read from default db values, load from machine,...
            # Create a SharedPV and add it to the PVManager
            pv = create_pv('float', 'd', element)
            cm_pv = create_pv('float', 'd', element)
            manager.add_pv(pv_name, pv)
            manager.add_pv(cm_pv_name, cm_pv)

    # Create a StaticProvider and register it with the PVManager
    provider = manager.get_provider()

    # Create a P4P server with the created provider
    with Server(providers=[provider]):
        print('Server Starting')
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            print('Waiting for all tasks to complete...')
            tasks = asyncio.all_tasks()
            for task in tasks:
                if task != asyncio.current_task():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    tracemalloc.start()
    asyncio.run(server_start_up())
