import asyncio
import logging
import time

from p4p.client.asyncio import Context
from p4p.nt import NTScalar
from p4p.server import Server
from p4p.server.asyncio import SharedPV

import dt4acc.command as cmd
from dt4acc.model.element_upate import ElementUpdate
from dt4acc.model.orbit import Orbit
from dt4acc.model.twiss import Twiss
from dt4acc.model.elementmodel import MagnetElementSetup, PowerConverterElementSetup
from dt4acc.setup_configuration.data_access import get_magnets, get_unique_power_converters, \
    get_magnets_per_power_converters
from dt4acc.setup_configuration.pv_manager import PVManager

# Configure logging
logging.basicConfig(level=logging.INFO)

help_type = NTScalar('s')
types = {
    'int': NTScalar('i').wrap(0),
    'float': NTScalar('d').wrap(0.0),
    'str': NTScalar('s').wrap(''),
    'array': NTScalar('ad').wrap([0.0, 0.0]),
    'bool': NTScalar('b').wrap(False),
    'bool_array': NTScalar('ab').wrap([])
}

manager = PVManager()


def get_property_id(pv_name):
    if ':Cm:set' in pv_name:
        return 'K'
    elif ':x:set' in pv_name:
        return 'x'
    elif ':y:set' in pv_name:
        return 'y'
    elif ':im:I' in pv_name:
        return 'im'
    elif ':rdbk' in pv_name:
        return 'rdbk'
    else:
        return None


class ElementHandler:
    def __init__(self, element):
        self.element = element

    def rpc(self, pv, op):
        V = op.value()
        if V.query.get('help') is not None:
            op.done(help_type.wrap('Try newtype=int (or float or str)'))
            return

        newtype = types[V.query.newtype]

        op.done(help_type.wrap('Success'))

        pv.close()
        pv.open(newtype)

    async def put(self, pv, op):
        val = op.value()
        logging.debug("Assigning %s = %s", op.name(), val)
        try:
            pv.post(val, timestamp=time.time())
        except Exception as e:
            logging.error("Error updating pv %s value %s exception $s", op.name(), val, e)
        pv_name = op.name()
        property_id = get_property_id(pv_name)
        if self.element.type == 'pc':
            rdbk_pv_name = pv_name
            rdbk_pv_name = rdbk_pv_name.replace('set', 'rdbk')
            rdbk_pv = manager.get_pv(rdbk_pv_name)
            if rdbk_pv:
                rdbk_pv.post(val, timestamp=time.time())
            context = Context('pva')
            # todo: find all relevant magnets and set their im:I at once.
            #  also update rdbk of this same pc
            magnets = get_magnets_per_power_converters(self.element.name)
            target_pvs_names = []
            target_pvs_vals = []
            for magnet in magnets:
                name = magnet['name']
                target_pv = 'Anonym:' + f"{name}:im:I"
                target_pvs_names.append(target_pv)
                target_pvs_vals.append(val)
            await context.put(target_pvs_names, target_pvs_vals)
            op.done()
        elif (property_id is None or isinstance(self.element, ElementUpdate) or isinstance(self.element, Orbit)
              or isinstance(self.element, Twiss) or property_id in ["rdbk", 'K']):
            op.done()
        else:
            # logging.info("Calling Command Update for %s value = %s", property_id, val)
            if isinstance(self.element, str):
                FamName = self.element
            else:
                # logging.warning("self.element is: $s : $s", self.element , self.element.name)
                FamName = self.element.name  # use .FamName if Accelerator from lat2db was used
            try:
                await cmd.update(element_id=FamName, property_name=property_id, value=float(op.value()),
                                 element=self.element)
                op.done()
            except Exception as e:
                logging.error("Error updating element %s property %s with value %s: %s", FamName, property_id, val, e)
            op.done()


def create_pv(initial_value_type, initial_type, element):
    initial = types[initial_value_type]
    pv = SharedPV(nt=NTScalar(initial_type), initial=initial, handler=ElementHandler(element))
    return pv


def add_magnet_pvs(magnet, prefix, manager):
    pv_name = prefix + magnet.name
    cm_pv_name = pv_name + ":Cm:set"
    dx_pv_name = pv_name + ":x:set"
    dy_pv_name = pv_name + ":y:set"
    im_pv_name = pv_name + ":im:I"

    # Create PVs
    pv = create_pv('float', 'd', magnet)
    cm_pv = create_pv('float', 'd', magnet)
    dx_pv = create_pv('float', 'd', magnet)
    dy_pv = create_pv('float', 'd', magnet)
    im_pv = create_pv('float', 'd', magnet)

    # Add to manager
    manager.add_pv(pv_name, pv)
    manager.add_pv(cm_pv_name, cm_pv)
    manager.add_pv(dx_pv_name, dx_pv)
    manager.add_pv(dy_pv_name, dy_pv)
    manager.add_pv(im_pv_name, im_pv)


def add_power_converter_pvs(pc_name, prefix, manager):
    # replicating real machine power converters.
    pc_pv_name = prefix + f"{pc_name}:set"
    pc_rdbk_name = prefix + f"{pc_name}:rdbk"
    pc_pv = create_pv('float', 'd', PowerConverterElementSetup(name=pc_name, type='pc'))
    pc_rdbk_pv = create_pv('float', 'd', PowerConverterElementSetup(name=pc_name, type='pc'))

    manager.add_pv(pc_pv_name, pc_pv)
    manager.add_pv(pc_rdbk_name, pc_rdbk_pv)


async def server_start_up():
    """
    to set the server based on latex if the data for magnets and hw2phy and setpoints are not ready for a specific machine
    -    from lat2db.model.accelerator import Accelerator
-    acc = Accelerator().ring
     prefix = "Anonym:"
-    for element in acc:
-        element_str = str(element)
-        element_split_by_space = element_str.split('\n')
-        element_type = element_split_by_space[0]
-        if element_type in ["Quadrupole:", "Sextupole:"]:
-            pv_name = prefix + element.FamName
-            cm_pv_name = pv_name + ":Cm:set"
-            dx_pv_name = pv_name + ":x:set"
-            dy_pv_name = pv_name + ":y:set"
-            im_pv_name = pv_name + ":im:I"
-            rdbk_pv_name = pv_name + ":rdbk"
-            pv = create_pv('float', 'd', element)
-            cm_pv = create_pv('float', 'd', element)
-            dx_pv = create_pv('float', 'd', element)
-            dy_pv = create_pv('float', 'd', element)
-            im_pv = create_pv('float', 'd', element)
-            rdbk_pv = create_pv('float', 'd', element)
-            manager.add_pv(pv_name, pv)
-            manager.add_pv(cm_pv_name, cm_pv)
-            manager.add_pv(dx_pv_name, dx_pv)
-            manager.add_pv(dy_pv_name, dy_pv)
-            manager.add_pv(im_pv_name, im_pv)
-            manager.add_pv(rdbk_pv_name, rdbk_pv)

    """
    # Fetch all Quadrupole, steerer and Sextupole magnets from the database
    energy = 1700000000
    electron_rest_mass = 0.51099895 * 1000000
    speed_of_light = 299792458
    brho = 5.67229387129245
    edf = 1 / brho
    prefix = "Anonym:"
    for magnet_data in get_magnets():
        magnet = MagnetElementSetup(
            type=magnet_data['type'],
            name=magnet_data['name'],
            hw2phys=magnet_data['magnetic_strength'] * edf,
            phys2hw=1 / (magnet_data['magnetic_strength'] * edf),
            energy=energy,
            magnetic_strength=magnet_data['magnetic_strength'],
            electron_rest_mass=electron_rest_mass,
            speed_of_light=speed_of_light,
            brho=brho,
            edf=edf,
            pc=magnet_data['pc']
        )
        add_magnet_pvs(magnet, prefix, manager)

    # Add PVs for unique power converters
    for pc_name in get_unique_power_converters():
        add_power_converter_pvs(pc_name, prefix, manager)

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


if __name__ == "__main__":
    asyncio.run(server_start_up())
