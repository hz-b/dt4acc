from abc import ABCMeta, abstractmethod
from typing import Sequence

from accml_lib.core.model.output.result import ReadTogether
from accml_lib.core.model.utils.command import Command, ReadCommand


class ControllerInterface(metaclass=ABCMeta):
    @abstractmethod
    async def update(
            self,
            cmd: Command,
            reads: Sequence[ReadCommand],
            delayed_reads: Sequence[ReadCommand]
    ):
        """update a value (in the back engine) and update views accordingly

        Args:
            cmd: command that changes value in the back engine
            reads: read commands to peek into the back engine and update
                   immediately
            delayed_reads: read commands that typically require calculations
                           these are only updated with a delay
                           e.g. calculation of twiss or orbit
        """

    @abstractmethod
    async def trigger_read(self, reads: Sequence[ReadCommand]) -> ReadTogether:
        """just a simple wrapper of mexec.trigger_read
        """