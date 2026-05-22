import logging
import math
from dataclasses import dataclass
from typing import Dict, Literal, Sequence, Union

from softioc import softioc
from softioc.pythonSoftIoc import RecordWrapper

from dt4acc.core.interfaces.controller_interface import ControllerInterface
from dt4acc.custom_epics.ioc.controller import Controller as EpicsController, dispatcher
from dt4acc.custom_epics.ioc.pv_setup import (
    initialize_master_clock_pvs,
    initialize_orbit_pvs,
    initialize_twiss_pvs,
    initialize_tune_pvs,
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


async def build_ao_record(
    builder, model: Setpoint, controller: ControllerInterface
) -> RecordWrapper:
    initial_val = unpack_translated_reading_expecting_single_float(
        await controller.trigger_read([model.rcmd])
    )

    reads = []

    if model.rcmd is not None:
        reads = [model.rcmd]

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
        initial_val = unpack_translated_reading_expecting_single_float(
            await controller.trigger_read([model.rcmd])
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
    async def instantiate(model):
        f = factory[model.record_type]
        rec = await f(builder, model, controller)
        return rec

    r = {model.rcmd: await instantiate(model) for model in models}
    return r


class ALSEpicsController(EpicsController):
    def __init__(
        self,
        *,
        name,
        builder: RecordWrapper,
        controller_delegate: ControllerInterface,
        process_variable_views: Sequence[Union[Setpoint, Monitor]]
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
            **initialize_orbit_pvs(self.builder),
            **initialize_twiss_pvs(self.builder),
            **initialize_tune_pvs(self.builder),
        }

        self.delegate.view.update_process_variables(d)
        logger.warning("All PVs set up")

        self.builder.LoadDatabase()
        softioc.iocInit(dispatcher)
