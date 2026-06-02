import asyncio
import logging
import math
from dataclasses import dataclass
from typing import Dict, Literal, Sequence, Union

import numpy as np
from softioc import softioc
from softioc.pythonSoftIoc import RecordWrapper

from dt4acc.core.interfaces.controller_interface import ControllerInterface
from dt4acc.custom_epics.ioc.controller import Controller as EpicsController, dispatcher
from dt4acc.custom_epics.ioc.pv_setup import (
    initialize_master_clock_pvs,
    initialize_orbit_pvs,
    initialize_twiss_pvs,
    initialize_tune_pvs,
    initialize_machine_info_pvs,
)
from dt4acc.custom_facility.als.model import Monitor, Setpoint
from dt4acc_lib.model.utils.command import ReadCommand, Command, BehaviourOnError
from dt4acc_lib.model.output.result import ReadTogetherAndTranslated

logger = logging.getLogger("dt4acc")


def unpack_translated_reading_expecting_single_float(
    pkg: ReadTogetherAndTranslated,
) -> float:
    (translated,) = pkg.data
    (expected_single,) = translated.readings
    val = float(expected_single.payload)
    return val


def unpack_translated_reading_calculate_average(
    pkg: ReadTogetherAndTranslated,
) -> float:
    if len(pkg.data) == 1:
        # Todo: consider if this options should be here
        return unpack_translated_reading_expecting_single_float(pkg)

    values = []
    for translated in pkg.data:
        # How
        (expected_single,) = translated.readings
        val = float(expected_single.payload)
        values.append(val)

    val = np.mean(values)
    return val


def handle_returned_data(
    pkg: ReadTogetherAndTranslated, returned_data_type: str
) -> float:
    if returned_data_type == "single":
        return unpack_translated_reading_expecting_single_float(pkg)
    elif returned_data_type == "average":
        return unpack_translated_reading_calculate_average(pkg)
    else:
        raise AssertionError(
            f"Not prepared to handle returned_data {returned_data_type}"
        )


async def build_ao_record(
    builder, model: Setpoint, controller: ControllerInterface
) -> RecordWrapper:
    initial_val = handle_returned_data(
        await controller.trigger_read([model.rcmd]), model.returned_data
    )
    # don't forget the ones that should be updated
    # when this changes: e.g. read backs from power converters
    # but be aware: don't call the rcmd that is used as basis
    # to build the Command passed to update
    #
    # This command will then be received by view: the value will
    # be updated and everything starts all over again
    #
    # So only use the extra ones
    reads = model.reads or []
    assert model.rcmd not in reads

    async def update(val: float):
        return await controller.update(
            cmd=Command(
                id=model.rcmd.id,
                property=model.rcmd.property,
                value=val,
                behaviour_on_error=BehaviourOnError.ignore,
            ),
            reads=reads,
            delayed_reads=[],
        )

    rec = builder.aOut(
        model.pv_name, initial_value=initial_val, on_update=update, PREC=model.prec
    )
    return rec


async def build_ai_record(builder, model: Monitor, controller: ControllerInterface):
    if model.update == "delayed":
        initial_val = math.nan
    else:
        initial_val = handle_returned_data(
            await controller.trigger_read([model.rcmd]), model.returned_data
        )
    rec = builder.aIn(
        model.pv_name,
        initial_value=initial_val,
        PREC=model.prec,
    )
    return rec


factory = dict(
    ai=build_ai_record,
    ao=build_ao_record,
)


async def initialize_pvs_from_model(
    builder,
    models: Sequence[Union[Setpoint, Monitor]],
    controller: ControllerInterface,
) -> Dict[ReadCommand, RecordWrapper]:
    """initialise pvs based on their Setpoint or Monitor model

    Ignore pvs that can not be instantiated

    Todo:
        is that a good idea ?
    """

    async def instantiate(model):
        f = factory[model.record_type]
        try:
            rec = await f(builder, model, controller)
        except KeyError as ke:
            logger.warning("Could not instantiate %s due to key error %s", model, ke)
            rec = None
        return rec

    r = {model.rcmd: await instantiate(model) for model in models}
    r = {rcmd: rec for rcmd, rec in r.items() if rec is not None}
    return r


class ALSEpicsController(EpicsController):
    """
    Todo:
        refactor EPICSController to include the developments needed
        here
    """

    def __init__(
        self,
        *,
        name,
        builder: RecordWrapper,
        controller_delegate: ControllerInterface,
        process_variable_views: Sequence[Union[Setpoint, Monitor]],
    ):
        super().__init__(
            name=name, builder=builder, controller_delegate=controller_delegate
        )
        self.process_variable_views = process_variable_views

    async def startup(self) -> None:
        self.builder.SetDeviceName(self.prefix)

        recs = await initialize_pvs_from_model(
            self.builder, self.process_variable_views, controller=self.delegate
        )

        d = {
            **recs,
            **await initialize_master_clock_pvs(self.builder, self.delegate),
            **initialize_machine_info_pvs(self.builder, n_ref_buckets=328),
            **initialize_orbit_pvs(self.builder),
            **initialize_twiss_pvs(self.builder),
            **initialize_tune_pvs(self.builder),
        }

        self.delegate.view.update_process_variables(d)
        logger.warning("All PVs set up")

        self.builder.LoadDatabase()
        softioc.iocInit(dispatcher)

    async def trigger_default_reads(self):
        """
        Todo:
            make method of default controller
        """
        for i in range(50):
            # Wait for variables to get on line
            # this check should not be here but on startup
            rcmd = self.delegate.view.process_variables.get(
                ReadCommand(id="beam", property="x")
            )
            if rcmd:
                break
            await asyncio.sleep(0.2)
        else:
            logger.error("Test of startup of variables failed!")

        default_reads = self.delegate.default_delayed_reads
        r = await self.trigger_read(default_reads)

        for rcmd, pkg in zip(default_reads, r.data):
            await self.delegate.view.dispatch(rcmd, pkg)

    async def trigger_read_all_values(self):
        """
        Todo:
            make method of default controller
        """
        # collect once all readings form all views
        # trigger update and then be finished
        # Read all in once at start up
        reads = list(self.delegate.view.process_variables)

        async def read_one_by_one(rcmd):
            # so that we can log the ones that fail
            try:
                r = await self.trigger_read([rcmd])
            except Exception as ex:
                logger.error(
                    f"{self.__class__.__name__} {self.name} failed to retrieve data for {rcmd}"
                )
                # can be still useful to report in one batch
                return rcmd, None
            return rcmd, r

        read_result = [await read_one_by_one(rcmd) for rcmd in reads]
        read_result = [
            (rcmd, translated)
            for rcmd, translated in read_result
            if translated is not None
        ]
        # Need to combine translated...
        for rcmd, translated in read_result:
            for data in translated.data:
                await self.delegate.view.dispatch(rcmd, data)


__all__ = ["ALSEpicsController"]
