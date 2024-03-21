import asyncio
import logging
import time

from p4p.nt import NTScalar
from p4p.server import Server, StaticProvider
from p4p.server.asyncio import SharedPV

import dt4acc.command as cmd
from dt4acc.resources.bessy2_sr_reflat import bessy2Lattice

help_type = NTScalar('s')
types = {
    'int': NTScalar('i').wrap(0),
    'float': NTScalar('d').wrap(0.0),
    'str': NTScalar('s').wrap(''),
    'array': NTScalar('ad').wrap([0.0, 0.0])
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

    def put(self, pv, op):
        val = op.value()
        logging.info("Assign %s = %s", op.name(), val)
        # Notify any subscribers of the new value.
        # Also set timeStamp with current system time.
        pv.post(val, timestamp=time.time())
        # Notify the client making this PUT operation that it has now completed
        cmd.update(element_id=self.element.FamName, property_name="dx", value=float(op.value()))
        op.done()

async def server_start_up():
    provider = StaticProvider('abc')  # 'mailbox' is an arbitrary name
    # Iterate over each element in the accelerator list and create shared PVs
    ring_pvs = []
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
            # todo: what values should the array start with?
            #   1 -> maybe read from a db where defaults for each pv are stored
            #   2 -> another alternative can be to read from machine if available
            #   Finally use a pattern to separate the different options (read from default db values, load from machine,...

            pv = SharedPV(nt=NTScalar('d'), initial=types['float'], handler=ElementHandler(element))
            provider.add(pv_name, pv)
            ring_pvs.append(pv)
    # Server.forever(providers=[provider])
    # Create a P4P server with the created shared PVs
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
    asyncio.run(server_start_up())
