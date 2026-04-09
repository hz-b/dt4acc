"""Execute commands using the backend in the appropriate context


Todo:
    * review dealing with command conversion

      When commands are converted a single command can be changed to many.
      This is ok, but further down the processing line it can be essential
      that these are packed together.

      Currently that is not respected.
"""
import asyncio
import datetime
import itertools
from typing import Any, Mapping, Sequence

from dt4acc_lib.interfaces.backend.backend import BackendRW
from dt4acc_lib.interfaces.utils.command_execution_engine import CommandExecutionEngine
from dt4acc_lib.interfaces.utils.command_rewritter import CommandRewriterBase
from dt4acc_lib.model.utils.command import ReadCommand, Command
from dt4acc_lib.model.output.result import SingleReading, ReadTogether,  \
    TranslatedReading, ReadTogetherAndTranslated



class TranslatingCommandExecutionEngine(CommandExecutionEngine):
    """Common functionality of the measurement execution engine"""

    def __init__(
        self,
        *,
        backend: BackendRW,
        cmd_rewriter: CommandRewriterBase,
        expected_view_for_output: str,
        num_readings: int
    ):
        assert num_readings >= 1, f"{num_readings=} must be at least one!"
        self.backend = backend
        self.cmd_rewriter = cmd_rewriter
        self.expected_view_for_output = expected_view_for_output
        self.num_readings = num_readings


    def get_expected_view_for_output(self) -> str:
        return self.expected_view_for_output

    async def trigger_read(self, rcmds: Sequence[ReadCommand]) -> ReadTogetherAndTranslated:
        """
        Todo:
            review handling context or view:
                * design / device

            Can commands be only converted once?

            command rewriter: separate function for
            read commands? i.e. a delegation to
            liaison manager
        """
        rcmds = convert_read_commands(
            cmd_rewriter=self.cmd_rewriter,
            commands=rcmds,
            output_view=self.get_expected_view_for_output(),
            backend_view=self.backend.get_natural_view_name(),
        )
        # convert read commands ... does not collapse them ...
        rcmds = list(itertools.chain(*rcmds))
        start = datetime.datetime.now()
        data = await read_and_encapsulate(self.backend, rcmds)
        end = datetime.datetime.now()
        # Todo: how to convert data back ... I think
        #       that gets difficult as soon as there is no 1-to-1 mapping any more
        #       how to handle delta_ ... I need to be able to access reference storage
        converted_data = convert_data_seq(
            cmd_rewriter=self.cmd_rewriter,
            detectors=rcmds,
            data=data.data,
            data_view=self.backend.get_natural_view_name(),
            target_view=self.get_expected_view_for_output(),
        )
        r = ReadTogetherAndTranslated(data=converted_data, start=start, end=end)
        return r

    async def set(self, cmds: Sequence[Command]):
        translated_commands =  convert_set_commands(
                cmd_rewriter=self.cmd_rewriter,
                commands=cmds,
                commands_view=self.get_expected_view_for_output(),
                target_view=self.backend.get_natural_view_name(),
            )
        translated_commands = tuple(itertools.chain(*translated_commands))
        return await set_(
            self.backend,
            translated_commands
        )


async def set_(backend: BackendRW, transaction_commands: Sequence[Command]) -> None:
    await asyncio.gather(
        *[
            backend.set(dev_id=cmd.id, prop_id=cmd.property, value=cmd.value)
            for cmd in transaction_commands
        ]
    )


async def trigger(backend: BackendRW, detectors: Sequence[ReadCommand]) -> None:
    # read in parallel
    await asyncio.gather(
        *[backend.trigger(dev_id=dev.id, prop_id=dev.property) for dev in detectors]
    )


async def read_and_encapsulate(backend: BackendRW, detectors: Sequence[ReadCommand]) -> ReadTogether:
    """put data into a ReadToGether envelope"""
    start = datetime.datetime.now()
    data = await read(backend, detectors)
    end = datetime.datetime.now()
    assert len(data) == len(detectors)
    reading = [
        SingleReading(
            name=f"{cmd.id}-{cmd.property}", payload=datum, cmd=cmd,
        )
        for datum, cmd in zip(data, detectors)
    ]
    return ReadTogether(data=reading, start=start, end=end)

async def read(backend: BackendRW, detectors: Sequence[ReadCommand]) -> Sequence[Any]:
    # read in parallel
    data = await asyncio.gather(
        *[backend.read(dev_id=dev.id, prop_id=dev.property) for dev in detectors]
    )
    return data


def convert_read_commands(
    *,
    cmd_rewriter: CommandRewriterBase,
    commands: Sequence[ReadCommand],
    output_view: str,
    backend_view: str,
):
    command = commands
    if output_view == backend_view:
        # No conversion needed — wrap each command in a list so that
        # itertools.chain(*result) in trigger_read() flattens correctly
        return [[cmd] for cmd in commands]
    elif output_view == "design":
        assert (
            backend_view == "device"
        ), "expected to need to convert from design to device"
        #: Warning: this code path is not yet tested
        # raise AssertionError("This path is not yet tested!")
        tmp = [cmd_rewriter.forward_read_command(r) for r in command]
        return tmp
    elif output_view == "device":
        assert (
            backend_view == "design"
        ), "expected to need to convert from device to design"
        tmp = [cmd_rewriter.inverse_read_command(r) for r in command]
        return tmp

    raise AssertionError("Did not expect to end up here!")


def convert_set_commands(
    *,
    cmd_rewriter: CommandRewriterBase,
    commands: Sequence[Command],
    commands_view: str,
    target_view: str,
):
    """

    Todo:
        consider to rename input view and target view to context
    """

    if commands_view == target_view:
        # No conversion needed — wrap each command in a list so that
        # itertools.chain(*result) in set() flattens correctly
        return [[cmd] for cmd in commands]
    elif commands_view == "design":
        assert (
                target_view == "device"
        ), "expected to need to convert from design to device"
        tmp = [cmd_rewriter.forward(c) for c in commands]
        # Todo:
        #       instead of itertools.chain this should return
        #       a Sequence[ReadTogether]
        #       review where else it has an impact
        #       User should chain commands if not required
        return tmp
        return list(itertools.chain(*tmp))
    elif commands_view == "device":
        assert (
                target_view == "design"
        ), "expected to need to convert from device to design"
        tmp = [cmd_rewriter.inverse(c) for c in commands]
        # Todo:
        #       instead of itertools.chain this should return
        #       a Sequence[ReadTogether]
        #       review where else it has an impact
        #       User should chain commands if not required
        return tmp
        return list(itertools.chain(*tmp))
    raise AssertionError("Did not expect to end up here!")


def convert_data_seq(
    *,
    cmd_rewriter: CommandRewriterBase,
    detectors: Sequence[ReadCommand],
    data: Sequence[SingleReading],
    data_view: str,
    target_view: str,
) -> Sequence[TranslatedReading]:
    """
    Todo:
        merge with convert_data
        Review what data type is returned

        Sequence[ReadTogether]?
    """

    def create_command(rcmd: ReadCommand, datum: SingleReading):
        assert rcmd is not None
        return Command(
            id=rcmd.id, property=rcmd.property, value=datum.payload, behaviour_on_error=None
        )

    l_det = len(detectors)
    l_data = len(data)
    if l_det != l_data:
        raise AssertionError(
            f"Converting data from {data_view} to {target_view}:"
            f" read commands {l_det} data {l_data}"
        )
    cmds = convert_set_commands(
        cmd_rewriter=cmd_rewriter,
        commands=[
            create_command(cmd, datum)
            # Todo: check that these have the same length
            for cmd, datum in itertools.zip_longest(detectors, data)
        ],
        commands_view=data_view,
        target_view=target_view,
    )

    assert len(cmds) == len(detectors), "Length of commands and detectors need to match" " as I need to combine them"
    # Todo: use key for checking ...
    r=[
        TranslatedReading(
            cmd=rc,
            readings=[
            SingleReading(
                name=f"{cmd.id}-{cmd.property}",
                cmd=ReadCommand(id=cmd.id, property=cmd.property),
                payload=cmd.value
            )
            for cmd in tc
        ]
        )
        for rc, tc in zip(detectors, cmds)
    ]
    return r


def convert_data(
    cmd_rewriter: CommandRewriterBase,
    detectors: Sequence[ReadCommand],
    data: Sequence[Mapping[str, object]],
) -> Sequence[ReadTogether]:
    """

    Here only command rewritter is used. As always the same command is used
    one could just look up the translation object once and then do batch
    processing.

    Early optimisation ...
    """

    def convert_single(cmd, datum):
        ncmd = cmd_rewriter.forward(
            Command(
                id=cmd.id, property=cmd.property, value=datum, behaviour_on_error=None
            )
        )
        return ncmd.value

    cmds = [ReadCommand(id=rcmd.id, property=rcmd.property) for rcmd in detectors]
    # Todo: use key for checking ...
    return [
        ReadTogether(
            data=[
                SingleReading(
                    name=datum[0],
                    cmd=ReadCommand(id=cmd.id, property=cmd.property),
                    payload=convert_single(cmd, datum[1]),
                )
                for cmd, datum in itertools.zip_longest(cmds, epoch.items())
            ]
        )
        for epoch in data
    ]