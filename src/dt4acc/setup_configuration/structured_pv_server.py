import asyncio

from p4p.nt import NTScalar
from p4p.server import Server
from p4p.server.asyncio import SharedPV
from p4p.wrapper import Value, Type
from softioc import builder

from dt4acc.setup_configuration.pv_manager import PVManager

# Set device name for SoftIOC PVs
builder.SetDeviceName("Anonym")

manager = PVManager()
help_type = NTScalar('s')
types = {
    'int': NTScalar('i').wrap(0),
    'float': NTScalar('d').wrap(0.0),
    'str': NTScalar('s').wrap(''),
    'array': NTScalar('ad').wrap([0.0, 0.0]),
    'bool': NTScalar('b').wrap(False),
    'bool_array': NTScalar('ab').wrap([])
}


class ElementHandler:
    def __init__(self, element):
        self.element = element

    def rpc(self, pv, op):
        V = op.value()

    async def put(self, pv, op):
        val = op.value()


# Define structured PV types
twiss_type = Type([
    ('x', ('S', None, [
        ('alpha', 'ad'),
        ('beta', 'ad'),
        ('nu', 'ad'),
    ])),
    ('y', ('S', None, [
        ('alpha', 'ad'),
        ('beta', 'ad'),
        ('nu', 'ad'),
    ])),
    ('names', 'as')
])

orbit_type = Type([
    ('x', 'ad'),
    ('y', 'ad'),
    ('names', 'as'),
    ('found', '?'),
    ('x0', 'ad')
])

bpm_type = Type([
    ('bpms', ('aS', None, [
        ('name', 's'),
        ('pos', ('S', None, [
            ('x', 'd'),
            ('y', 'd')
        ]))
    ]))
])


# Correct placement of structured PVs within the asyncio loop
async def initialize_p4p_pvs(manager):
    twiss_pv = SharedPV(initial=Value(twiss_type, {
        'x': {'alpha': [0.0], 'beta': [0.0], 'nu': [0.0]},
        'y': {'alpha': [0.0], 'beta': [0.0], 'nu': [0.0]},
        'names': ['']
    }))
    manager.add_pv("Anonym:beam:twiss", twiss_pv)
    orbit_pv = SharedPV(initial=Value(orbit_type, {
        'x': [0.0],
        'y': [0.0],
        'names': [''],
        'found': False,
        'x0': [0.0]
    }))
    manager.add_pv("Anonym:beam:orbit", orbit_pv)

    bpm_pv = SharedPV(initial=Value(bpm_type, {
        'bpms': [{
            'name': '',
            'pos': {'x': 0.0, 'y': 0.0}
        }]
    }))
    manager.add_pv("Anonym:beam:bpm", bpm_pv)


async def start_p4p_server(manager):
    provider = manager.get_provider()
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


# Start both SoftIOC and P4P server in a unified event loop
async def run_server():
    # p4p_providers = await initialize_p4p_pvs()
    # await asyncio.gather(
    #     start_p4p_server(p4p_providers),
    #     # dispatcher.loop(),
    #     softioc.interactive_ioc(globals())
    # )
    await initialize_p4p_pvs(manager)
    asyncio.create_task(start_p4p_server(manager)),  # Run P4P server


if __name__ == "__main__":
    asyncio.run(run_server())