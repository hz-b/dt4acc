import logging
from dataclasses import dataclass
from typing import Dict, Literal, Sequence, Union

from softioc import softioc
from softioc.pythonSoftIoc import RecordWrapper

from dt4acc.core.interfaces.controller_interface import ControllerInterface
from dt4acc.custom_epics.ioc.controller import Controller as EpicsController, dispatcher
from dt4acc.custom_epics.ioc.pv_setup import initialize_orbit_pvs, initialize_twiss_pvs, initialize_tune_pvs
from dt4acc.custom_facility.als.model import Monitor, Setpoint
from dt4acc_lib.model.utils.command import ReadCommand, Command, BehaviourOnError

logger = logging.getLogger("dt4acc")


async def build_ao_record(
    builder,
    model: Setpoint,
    controller: ControllerInterface
) -> RecordWrapper:
    initial_val, = controller.trigger_read([model.rcmd])
    reads = []
    if model.monitor is not None:
        reads = [model.monitor.rcmd]

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
        model.pv_name,
        initial_value=initial_val,
        on_update=update,
        PREC=model.prec
    )
    return rec


async def build_ain_record(
    builder,
    model: Monitor,
    controller: ControllerInterface
):
    initial_val, = await controller.trigger_read([model.rcmd])
    rec = builder.aIn(
        model.pv_name,
        initial_value=initial_val,
        PREC=model.prec,
    )
    return rec

factory = dict(
    ain=build_ao_record,
    ao=build_ao_record,
)

async def initialize_pvs_from_model(
        builder,
        models: Sequence[Union[Setpoint, Monitor]],
        controller: ControllerInterface,
) -> Dict[ReadCommand, RecordWrapper]:

    def instantiate(model):
        f = factory[model.record_type]
        rec = f(builder, model, controller)
        return rec

    r = {
        model.rcmd: instantiate(model)
        for model in models
    }
    return r


class ALSEpicsController(EpicsController):
    async def startup(self, models: Sequence[Union[Monitor, Setpoint]]) -> None:
        self.builder.SetDeviceName(self.prefix)

        recs = await initialize_pvs_from_model(self.builder, models, controller=self.delegate),

        d = {
            **recs,
            **initialize_orbit_pvs(self.builder),
            **initialize_twiss_pvs(self.builder),
            **initialize_tune_pvs(self.builder),
        }

        self.delegate.view.update_process_variables(d)
        logger.warning("All PVs set up")

        self.builder.LoadDatabase()
        softioc.iocInit(dispatcher)

