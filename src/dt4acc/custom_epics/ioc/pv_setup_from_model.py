from typing import Dict, Sequence, Union

import numpy as np
from softioc.pythonSoftIoc import RecordWrapper

from dt4acc.core.interfaces.controller_interface import ControllerInterface
from dt4acc.core.model.view import Monitor, Setpoint
from dt4acc.core.utils.logger import get_logger
from dt4acc_lib.model.output.result import ReadTogetherAndTranslated
from dt4acc_lib.model.utils.command import ReadCommand, Command, BehaviourOnError

logger = get_logger()


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


class NotSingleReading(Exception):
    pass


def unpack_translated_reading_expecting_single_float(
    pkg: ReadTogetherAndTranslated,
) -> float:
    (translated,) = pkg.data
    L = len(translated.readings)
    if L != 1:
        raise NotSingleReading(
            f"received pkg of {L} items; request: {translated.cmd}"
            f", returned: {[r.cmd for r in translated.readings]}"
        )
    (expected_single,) = translated.readings
    val = float(expected_single.payload)
    return val


def unpack_translated_reading_calculate_average(
    pkg: ReadTogetherAndTranslated,
) -> float:
    if len(pkg.data) == 1:
        # Todo: consider if this options should be here
        try:
            return unpack_translated_reading_expecting_single_float(pkg)
        except NotSingleReading as nsr:
            logger.info("pkg %s: was not a single reading %s", pkg.data[0].cmd, nsr)

    values = []
    for translated in pkg.data:
        # Todo: review if there should be more than one returned
        #       happens now for dx, but has to be analysed if that
        #       is what should happen ...
        # (expected_single,) = translated.readings
        for single in translated.readings:
            val = float(single.payload)
            values.append(val)

    val = np.mean(values)
    return float(val)


class PotentialLoopError(Exception):
    """Avoid calling us back again

    The read command is used as an index in the view to the record

    A setpoint specifies a read command that shall be used to create
    the appropriate Command to update the simulation. If the same
    command is in the list of reads, the setpoint will be updated
    when the result are dispachted to view.dispatch

    This will create an infinite loop
    """
    pass


async def build_ao_record(
    builder, model: Setpoint, controller: ControllerInterface
) -> RecordWrapper:
    initial_val = handle_returned_data(
        await controller.trigger_read([model.rcmd]), model.treat_returned_data
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
    if model.rcmd in reads:
        raise PotentialLoopError(
            f"For setpoint {model.pv_name} potential infinite loop detected:"
            f"{model.rcmd} is in (model) reads {reads}"
        )

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
        initial_val = np.nan
    else:
        initial_val = handle_returned_data(
            await controller.trigger_read([model.rcmd]), model.treat_returned_data
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
        rec = None
        try:
            rec = await f(builder, model, controller)
        except KeyError as ke:
            logger.warning("Could not instantiate %s due to key error %s", model, ke)
        except PotentialLoopError as loop_error:
            logger.warning("Could not instantiate %s due to potential loop %s", model, loop_error)
        return rec

    r = {model.rcmd: await instantiate(model) for model in models}
    r = {rcmd: rec for rcmd, rec in r.items() if rec is not None}
    return r


__all__ = ["initialize_pvs_from_model"]