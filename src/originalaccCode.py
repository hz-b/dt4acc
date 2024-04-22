import thor_scsi.lib as tslib
from thor_scsi.factory import accelerator_from_config
from thor_scsi.utils.closed_orbit import compute_closed_orbit
from thor_scsi.utils.linear_optics import compute_twiss_along_lattice

from thor_scsi.utils.accelerator import (
    instrument_with_standard_observers,
    extract_orbit_from_standard_observers,
    extract_orbit_from_accelerator_with_standard_observers,
)
from thor_scsi.utils.extract_info import accelerator_info
import numpy as np
import os
import logging
from typing import Sequence
import pydev
import itertools
import functools
import threading
import time
import datetime
import traceback

logger = logging.getLogger("thor-scsi-lib")

t_dir = os.path.join(os.environ["HOME"], "Nextcloud", "thor_scsi")
t_file = os.path.join(t_dir, "b3_tst.lat")


@functools.lru_cache(maxsize=1)
def getBPMs(acc):
    bpms = [element for element in acc if element.name[:3] == "bpm"]
    bpm_names = [bpm.name for bpm in bpms]
    logger.debug(f"Using bpms {bpm_names}")
    return bpms


class Calculator:
    def __init__(self, *, parent):
        parent.acc
        parent.conf
        self.parent = parent

        self.result = None


class TwissCalculator(Calculator):
    def calculate(self):
        self.result = compute_twiss_along_lattice(self.parent.acc, self.parent.conf)
        return self.result


class OrbitCalculator(Calculator):
    def __init__(self, delta=0e0, x0=None, eps=1e-8, max_iter=10, **kwargs):
        super().__init__(**kwargs)
        self.delta = delta
        self.x0 = x0
        self.eps = eps
        self.max_iter = max_iter

    def setEpsilon(self, eps):
        eps = float(eps)
        if not eps > 0e0:
            raise AssertionError("Epsilon must be > 0.0")

        self.eps = eps

    def getEpsilon(self):
        return self.eps

    def calculate(self):
        delta = None
        x0 = None
        if self.result is None or not np.isfinite(self.result.x0).all():
            delta = 0e0
        else:
            x0 = self.result.x0
            delta = None

        try:
            self.result = compute_closed_orbit(
                self.parent.acc,
                self.parent.conf,
                x0=x0,
                delta=delta,
                max_iter=self.max_iter,
                eps=self.eps,
            )
        except:
            logger.warning(f"eps {self.eps}")
            raise

        if not self.result.found_closed_orbit:
            raise ValueError("No closed orbit was found")

        self.orbit = extract_orbit_from_accelerator_with_standard_observers(self.parent.acc)
        logger.warning("Calculated Orbit")
        return self.result


class AcceleratorFacade:
    """
    Todo:
        better name?
    """

    def __init__(self, acc):
        self.acc = acc
        self.observers = instrument_with_standard_observers(self.acc)
        self.conf = tslib.ConfigType()

        self.twiss = TwissCalculator(parent=self)
        self.orbit = OrbitCalculator(parent=self)

        self.eps = None

    def getBPMData(self):
        """
        """
        bpms = getBPMs(self.acc)

        def extract_orbit_offset(elem):
            ob = elem.getObserver()
            if not ob:
                return np.array([np.nan, np.nan])

            if ob.hasPhaseSpace():
                a = ob.getPhaseSpace()
            elif ob.hasTruncatedPowerSeries():
                a = np.array(ob.getTruncatedPowerSeries().cst())
            else:
                raise ValueError("No observed bpm data")
            return a[[0, 2]]

        orbit_offsets = np.array([extract_orbit_offset(bpm) for bpm in bpms])
        names = [bpm.name for bpm in bpms]
        return orbit_offsets, names

    def findElement(self, *, element_name: str, element_index: int) -> tslib.ElemType:
        if not element_name:
            return self.acc[element_index]
        else:
            # here element name is used as family index
            logger.debug(f"Trying to find element {element_name} {element_index}")
            try:
                r = self.acc.find(element_name, element_index)
            except Exception as exc:
                logger.error(
                    f"Failed to find element {element_name} {element_index}: {exc}"
                )
                raise exc
            return r

    def getMethod(self, *, element, method_name: str):
        logger.debug(f"Trying to find method {method_name} on element {element}")
        try:
            method = getattr(element, method_name)
        except Exception as exc:
            logger.error(f"Failed to find method {method_name} on element {element}")
            logger.warning(f"Methods known are {dir(element)}")
            raise exc
        return method

    def walkToMethod(self, *, element, method_names: Sequence[str]):
        method = self.getMethod(element=element, method_name=method_names[0])

        if len(method_names) == 1:
            return method

        try:
            child = method()
        except Exception as exc:
            logger.error(f"Failed to execute method {method}")
            raise exc

        return self.walkToMethod(element=child, method_names=method_names[1:])

    def getProperty(
        self, *, element_name: str, element_index: int, method_names: Sequence[str]
    ):
        elem = self.findElement(element_name=element_name, element_index=element_index)
        method = self.walkToMethod(element=elem, method_names=method_names)
        return method()

    def setProperty(
        self,
        *,
        element_name: str,
        element_index: int,
        method_names: Sequence[str],
        value: object,
    ):
        elem = self.findElement(element_name=element_name, element_index=element_index)
        method = self.walkToMethod(element=elem, method_names=method_names)
        logger.debug(f"Setting element {elem} using method {method} to value {value}")
        try:
            method(value)
        except Exception as exc:
            logger.error(
                f"Set element {elem} using method {method} to value {value} failed: {exc}"
            )
        else:
            logger.debug(f"Set element {elem} using method {method} to value {value}")
        return elem

    def calculateTwiss(self):
        """expected to be called when required

        Todo:
           safe computed result?
        """
        result = self.twiss.calculate()
        logger.warning("Calculated Twiss")
        return result

    def calculateOrbit(self):
        """expected to be called when required

        Todo:
           safe computed result?
        """
        return self.orbit.calculate()


publish_counter = itertools.count()


class CalculationRunningManager:
    def __init__(self, *, prefix):
        self.label = f"{prefix}-dt-calcs"

    def signal(self):
        cls_name = self.__class__.__name__
        logger.warning(f"{cls_name}: #pydev.iointr({self.label}, {self.running})")
        #pydev.iointr(self.label, self.running)

    def __enter__(self):
        self.running = True
        self.signal()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.running = False
        self.signal()


class PendingCalculationManager:
    def __init__(self, *, info: str):
        self.pending = False
        self.info = info

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.pending = False
        else:
            logger.error(f"Failed to calculate {self.info}: {exc_type} {exc_val}")
            traceback.print_tb(exc_tb)
            logger.error(exc_tb)
        return True


class DelayExecution:
    """Only calculate if not a change has just been applied

    Allows to gather many changes before one calculation occurs
    """

    def __init__(self, *, prefix, callback, delay):
        self.request_timestamp = None
        self.execution_timestamp = None
        self.lock = threading.Lock()
        self.callback = callback
        self.delay = float(delay)
        self.execution = PendingCalculationManager(info="delayed execution")

        self.running = False
        self.label = f"{prefix}-dt-delayed-calcs"
        #pydev.iointr(self.label, self.execution.pending)

    def tic(self):
        def run():
            logger.warning("")
            time.sleep(self.delay)
            self.tac()

        cls_name = self.__class__.__name__
        with self.lock:
            if self.execution.pending:
                # Execution already pending
                logger.debug(f"{cls_name}: execution already pending")
                return

            self.execution.pending = True
            #pydev.iointr(self.label, self.execution.pending)
            logger.info(f"{cls_name}: delayed execution requested")
            self.actual_timestamp = datetime.datetime.now()
            thread = threading.Thread(target=run)
            thread.start()
            logger.info(f"{cls_name}: leaving tic:")

    def tac(self):
        cls_name = self.__class__.__name__
        logger.debug(f"{cls_name}: delayed execution: start.. waiting for lock")
        with self.lock:
            logger.warning(f"{cls_name}: delayed execution: start")
            assert self.execution.pending
            with self.execution:
                self.callback()
            self.execution.pending = False
            logger.debug(
                f"Executing #pydev.iointr({self.label}, {self.execution.pending})"
            )
            #pydev.iointr(self.label, self.execution.pending)
        logger.warning(f"{cls_name}: delayed execution: end")


class BPMMimikry:
    def __init__(self, *, parent, prefix):
        self.prefix = prefix
        self.parent = parent

    def publishBPMData(self, orbit_result):
        if orbit_result is None:
            raise AssertionError("Why no orbit data?")

        if not orbit_result.found_closed_orbit:
            logger.warning("No valid orbit!")
            return

        bpm_data, names = self.parent.accelerator_facade.getBPMData()
        logger.warning("Bpm data shape %s", bpm_data.shape)

        prefix = self.prefix
        label = f"{prefix}-bpm-names"
        names_as_bytes = [name.encode() for name in names]
        #pydev.iointr(label, names_as_bytes)

        for data, plane in zip(bpm_data.T, ["x", "y"]):
            label = f"{prefix}-bpm.d{plane}"
            logger.debug("BPM Data for plane %s: %s", plane, list(data))
            #pydev.iointr(label, list(data))

        # Build bpm data together
        n_channels = 128
        n_used, _ = bpm_data.shape
        bdata_prepare = np.zeros((8, n_channels), dtype=np.float)
        # x plane
        bdata_prepare[0, :n_used] = bpm_data[:, 0]
        bdata_prepare[1, :n_used] = bpm_data[:, 1]

        bdata = bdata_prepare.reshape(-1)

        bdata_all = np.zeros((2048,), dtype=np.float)
        bdata_all[: len(bdata)] = bdata

        label = f"{prefix}-bpm-bdata"
        #pydev.iointr(label, list(bdata_all))


class VirtualAccelerator:
    def __init__(self, accelerator_facade, prefix=""):
        self.accelerator_facade = accelerator_facade
        self.prefix = prefix
        self.execute_calculations = False
        self.orbit_pending = PendingCalculationManager(info="closed orbit")
        self.twiss_pending = PendingCalculationManager(info="twiss parameters")
        self.calc_context = CalculationRunningManager(prefix=prefix)
        self.bpm = BPMMimikry(prefix=prefix, parent=self)
        self.delay_execution = DelayExecution(
            prefix=prefix, callback=self._executePendingCalculations, delay=0.1
        )
        self.startup = False

    def executeCalculationsAtStartup(self, *, delay_before_first=3):
        if self.startup:
            raise ValueError("Startup already running!")

        def run():
            logger.warning("Startup delaying calculations")
            val = self.execute_calculations
            self.executeCalculations(active=False)
            time.sleep(3)
            logger.warning("Startup: executing pending calculations")
            self._executePendingCalculations()
            logger.warning("Startup: setting execute back to start value")
            self.executeCalculations(active=val)

        # thread = threading.Thread(target=run, name="start vacc")
        # thread.start()

    def executeCalculations(self, *, active):
        self.execute_calculations = bool(active)
        logger.warning(f"Request for executing calculations: {active}")
        if active:
            self.executePendingCalculations()

    def getProperty(self, **kwargs):
        return self.accelerator_facade.getProperty(**kwargs)

    def setProperty(self, **kwargs):
        """

        Todo:
            Who should now trigger the calculation of twiss etc if
            changes are applied?
        """
        return self.accelerator_facade.setProperty(**kwargs)

    def setPropertyAndReadback(
        self, *, readback_method, readback_label, twiss=True, orbit=True, **kwargs
    ):
        """
        """
        elem = self.setProperty(**kwargs)
        method = self.accelerator_facade.getMethod(
            element=elem, method_name=readback_method
        )
        rdbk = method()
        logger.info(
            f"Publishing readback {rdbk} type {type(rdbk)} with label {readback_label}"
        )
        #pydev.iointr(readback_label, rdbk)

        # Typically these calculations below will fail if the twin sets
        # unsensible data during start up.
        if twiss:
            self.twiss_pending.pending = True

        if orbit:
            self.orbit_pending.pending = True

        self.executePendingCalculations()

    def executePendingCalculations(self):
        # if not self.execute_calculations:
        #    return

        # self._executePendingCalculations()
        self.delay_execution.tic()

    def _executePendingCalculations(self):
        with self.calc_context:
            self.calculateTwiss()
            self.calculateOrbit()

    def calculateTwiss(self):
        if not self.twiss_pending.pending:
            logger.warning(f"No twiss calculation pending")
            return

        logger.warning(f"Executing twiss calculation")
        with self.twiss_pending:
            self._calculateTwiss()

        logger.warning(
            f"Twiss: after calculation still need? %d", self.twiss_pending.pending
        )

    def calculateOrbit(self):
        if not self.orbit_pending.pending:
            logger.warning(f"No orbit calculation pending")
            return

        logger.warning(f"Executing orbit calculation")
        with self.orbit_pending:
            r = self._calculateOrbit()

        logger.warning(
            f"Orbit: after calculation still need? %d", self.orbit_pending.pending
        )

    def _calculateTwiss(self):
        """

        Todo:
           publish update of data
        """
        r = self.accelerator_facade.calculateTwiss()
        # logger.warning(r)
        # logger.warning(r.tps)
        prefix = self.prefix + ":beam"
        for par in "alpha", "beta", "dnu":
            for plane in "x", "y":
                val = r.twiss.sel(plane=plane, par=par).values
                lpar = par
                if par == "dnu":
                    val = np.add.accumulate(val)
                    lpar = "nu"
                val = val.tolist()
                label = f"{prefix}:{lpar}:{plane}"
                logger.info(f"Executing pydev.iontr({label}, {val[:3]} {type(val)}")
                #pydev.iointr(label, val)
        return r

    def _calculateOrbit(self):
        """

        Todo:
           publish update of data
        """
        r = self.accelerator_facade.calculateOrbit()
        if not r.found_closed_orbit:
            raise ValueError("No closed orbit was found")

        ds = self.accelerator_facade.orbit.orbit
        prefix = self.prefix + ":beam"
        for plane in "x", "y":
            val = ds.ps.sel(phase_coordinate=plane).values.tolist()
            label = f"{prefix}:orbit:{plane}"
            logger.info(f"Executing pydev.iontr({label}, {val[:3]} {type(val)}")
            #pydev.iointr(label, val)

        self.bpm.publishBPMData(r)

    def publishLattice(self):
        """
        """
        info = accelerator_info(self.accelerator_facade.acc)
        # logger.warning(info)

        s = info.s
        val = s.values.tolist()
        prefix = self.prefix + ":beam"
        label = f"{prefix}:s"
        logger.info(f"Executing pydev.iontr({label}, {val[:3]} {type(val)}")
        #pydev.iointr(label, val)
        val = next(publish_counter)

        names = info.names
        val = [name.encode() for name in names.values]
        label = f"{prefix}:names"
        logger.warning(f"Executing pydev.iontr({label}, {val[:3]} {type(val)}")
        #pydev.iointr(label, val)
        val = next(publish_counter)

        return val


lattice_filename_default = os.environ["THOR_SCSI_LATTICE"]


def build_virtual_accelerator(*, prefix, lattice_file_name=lattice_filename_default):
    acc = accelerator_from_config(lattice_file_name)

    af = AcceleratorFacade(acc)
    vacc = VirtualAccelerator(af, prefix=prefix)
    vacc.executeCalculationsAtStartup()
    return vacc
