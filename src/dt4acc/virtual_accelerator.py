import itertools
import logging
import time
from typing import Dict, Any
import numpy as np
import pydev
from .pending_calculation_manager import PendingCalculationManager
from .calculation_running_manager import CalculationRunningManager
from .delay_execution import DelayExecution
from .bpm_mimikry import BPMMimikry
from typing import Sequence
from thor_scsi.utils.extract_info import accelerator_info

logger = logging.getLogger("thor-scsi-lib")

publish_counter = itertools.count()


class VirtualAccelerator:
    """
    Class representing a virtual accelerator.

    Attributes:
        accelerator_facade (object): The accelerator facade object.
        prefix (str): A prefix string.
        execute_calculations (bool): A flag indicating whether calculations are currently being executed.
        orbit_pending (object): A pending calculation manager object for closed orbit.
        twiss_pending (object): A pending calculation manager object for Twiss parameters.
        calc_context (object): A calculation running manager object.
        bpm (object): A BPMMimikry object.
        delay_execution (object): A delay execution object.
        startup (bool): A flag indicating whether startup is running.
    """

    def __init__(self, accelerator_facade, prefix=""):
        """
        Constructor for VirtualAccelerator class.

        Args:
            accelerator_facade (object): The accelerator facade object.
            prefix (str): A prefix string.
        """
        self.accelerator_facade = accelerator_facade
        self.prefix = prefix
        #: todo rename attribute as function with similar method exists
        self.executeCalculations = False
        self.orbit_pending = PendingCalculationManager(info="closed orbit")
        self.twiss_pending = PendingCalculationManager(info="Twiss parameters")
        self.calc_context = CalculationRunningManager(prefix=prefix)
        self.bpm = BPMMimikry(prefix=prefix, parent=self)
        self.delay_execution = DelayExecution(prefix=prefix, callback=self._execute_pending_calculations, delay=0.1)
        self.startup = False

    def execute_calculations_at_startup(self, *, delay_before_first=3):
        """
        Method to execute calculations at startup.

        Args:
            delay_before_first (int): The delay before the first calculation is executed.

        Raises:
            ValueError: If startup is already running.
        """
        if self.startup:
            raise ValueError("Startup already running!")

        def run():
            logger.warning("Startup delaying calculations")
            val = self.executeCalculations
            self.execute_calculations(active=False)
            time.sleep(3)
            logger.warning("Startup: executing pending calculations")
            self.twiss_pending.pending = True
            self.orbit_pending.pending = True
            self.execute_pending_calculations()
            self._execute_pending_calculations()
            logger.warning("Startup: setting execute back to start value")
            self.execute_calculations(active=val)

        # Todo: why is the run not executed ...
        # run()

    def execute_calculations(self, *, active):
        """
        Method to execute calculations.

        Args:
            active (bool): A flag indicating whether to execute calculations.
        """
        self.executeCalculations = bool(active)
        logger.warning(f"Request for executing calculations: {active}")
        if active:
            self.execute_pending_calculations()

    def _element_name_to_lower(self, kwargs):
        element_name = kwargs["element_name"]
        nkws = kwargs.copy()
        nkws["element_name"] = element_name.lower()
        return nkws

    def get_property(self, **kwargs) -> Dict[str, Any]:
        """
        Method to get the property.

        Args:
            **kwargs: Key value pairs of arguments.

        Returns:
            dict: A dictionary of the property.
        """
        # was set property
        kwargs = self._element_name_to_lower(kwargs)
        return self.accelerator_facade.get_property(**kwargs)

    def set_property(self, **kwargs):
        """
        """
        kwargs = self._element_name_to_lower(kwargs)
        return self.accelerator_facade.set_property(**kwargs)

    def set_property_and_readback(self, *, readback_method, readback_label, twiss=True, orbit=True, **kwargs):
        """
        Todo:
            Review as soon as readback also walks to a method
            if not better implement walk to element
        """
        kwargs = self._element_name_to_lower(kwargs)
        # Set property and get element
        elem = self.set_property(**kwargs)


        if True:
            # Get readback method and execute
            method = self.accelerator_facade.get_method(element=elem, method_name=readback_method)
            rdbk = method()
        else:
            # Requires that all readback methods are also list of methods to walk along
            # method = self.accelerator_facade.get_method(element=elem, method_name=readback_method)
            kwargs["method_names"]=readback_method
            del kwargs["value"]
            rdbk = self.get_property(element=elem, **kwargs)

        # Log readback value
        logger.info(f"Publishing readback {rdbk} type {type(rdbk)} with label {readback_label}")

        # Write readback value to output
        pydev.iointr(readback_label, rdbk)

        # Check if twiss and orbit are true and execute pending calculations
        if twiss:
            self.twiss_pending.pending = True

        if orbit:
            self.orbit_pending.pending = True

        self.execute_pending_calculations()

    def execute_pending_calculations(self):
        # if not self.execute_calculations:
        #    return

        # self._executePendingCalculations()
        self.delay_execution.request_execution()

    def _execute_pending_calculations(self):
        with self.calc_context:
            self.calculate_twiss()
            self.calculate_orbit()

    def calculate_twiss(self):
        if not self.twiss_pending.pending:
            logger.warning("No twiss calculation pending")
            return

        logger.warning("Executing twiss calculation")
        with self.twiss_pending:
            tic = time.time()
            self._calculate_twiss()
            tac = time.time()
            dt = tac - tic

            label = f"{self.prefix}:beam:twiss:calc_time"
            logger.info("Executing pydev.iontr(%s, %s)", label, dt)
            pydev.iointr(label, dt)

        logger.warning(f"Twiss: after calculation still need? {self.twiss_pending.pending}")

    def calculate_orbit(self):
        if not self.orbit_pending.pending:
            logger.warning("No orbit calculation pending")
            return

        logger.warning("Executing orbit calculation")
        with self.orbit_pending:
            tic = time.time()
            r = self._calculate_orbit()
            tac = time.time()
            dt = tac - tic

            label = f"{self.prefix}:beam:orbit:calc_time"
            logger.info("Executing pydev.iontr(%s, %s)", label, dt)
            pydev.iointr(label, dt)

        logger.warning("Orbit: after calculation still need? %d", self.orbit_pending.pending)

    import numpy as np

    def _calculate_twiss(self):
        """
        Calculates Twiss parameters and publishes the results.

        Todo:
            publish update of data
        """
        r = self.accelerator_facade.calculate_twiss()

        prefix = f"{self.prefix}:beam"
        for par in ["alpha", "beta", "dnu"]:
            for plane in ["x", "y"]:
                val = r.twiss.sel(plane=plane, par=par).values
                lpar = par
                if par == "dnu":
                    val = np.add.accumulate(val)
                    lpar = "nu"
                val = val.tolist()
                label = f"{prefix}:{lpar}:{plane}"
                logger.info(f"Executing pydev.iontr({label}, {val[:3]} {type(val)})")
                pydev.iointr(label, val)

                if lpar == "nu":
                    # publish the working point separately
                    label = f"{prefix}:working_point:{plane}"
                    qval = val[-1]
                    logger.info(f"Executing pydev.iontr({label}, {qval} {type(qval)})")
                    pydev.iointr(label, qval)

        return r

    def _calculate_orbit(self):
        """
        Calculates the orbit and publishes the data.

        Todo:
           publish update of data
        """
        # Calculate the orbit
        r = self.accelerator_facade.calculate_orbit()

        prefix = self.prefix + ":beam"

        # export closed orbit ...
        # found, fixed point, orbit
        # orbit only if found
        label = f"{prefix}:orbit:found"
        logger.info(f"Executing pydev.iontr({label}, {r.found_closed_orbit})")
        pydev.iointr(label, r.found_closed_orbit)

        label = f"{prefix}:orbit:fixed_point"
        # towards mm / mrad
        x0 = np.array(r.x0.iloc) * 1000.0
        x0 = list(x0)
        logger.info(f"Executing pydev.iontr({label}, {x0}")
        pydev.iointr(label, list(x0))

        # Raise a ValueError if no closed orbit is found
        if not r.found_closed_orbit:
            raise ValueError("No closed orbit was found")

        # Get the orbit data
        ds = self.accelerator_facade.orbit.orbit

        # Publish orbit data for x and y planes
        for plane in "x", "y":
            val = ds.ps.sel(phase_coordinate=plane).values.tolist()
            label = f"{prefix}:orbit:{plane}"
            logger.info(f"Executing pydev.iontr({label}, {val[:3]} {type(val)})")
            pydev.iointr(label, val)

        # Publish BPM data
        self.bpm.publish_bpm_data(r)

    def publishLattice(self):
        """
        Publishes lattice information to PyDev
        """
        info = accelerator_info(self.accelerator_facade.acc)
        prefix = self.prefix + ":beam"

        # Publish s values
        s_values = info.s.values.tolist()
        s_label = f"{prefix}:s"
        logger.info(f"Executing pydev.iontr({s_label}, {s_values[:3]} {type(s_values)}")
        pydev.iointr(s_label, s_values)
        next(publish_counter)

        # Publish element names
        element_names = [name.encode() for name in info.names.values]
        names_label = f"{prefix}:names"
        logger.warning(f"Executing pydev.iontr({names_label}, {element_names[:3]} {type(element_names)}")
        pydev.iointr(names_label, element_names)
        next(publish_counter)
