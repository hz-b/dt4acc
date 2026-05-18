from dt4acc_lib.bl.command_rewritter import CommandRewriter

# Virtual result element IDs — these are computed by the backend (twiss, tune,
# track, orbit) and never exist in the AT lattice. In device view the liaison
# has no conversion for them so inverse_read_command must pass them through
# unchanged, exactly as design view does.
_VIRTUAL_RESULT_IDS = frozenset({"twiss", "tune", "track", "orbit", "chromaticity"})


class VirtualPassthroughCommandRewriter(CommandRewriter):
    """
    CommandRewriter that short-circuits virtual result IDs (twiss, tune,
    track, orbit). These are not AT lattice elements — they are computed
    results published by SimulatorBackend.

    All four methods are overridden so that both the routing (read commands)
    and the value conversion (set commands / data conversion) bypass the
    liaison and translator entirely for these virtual IDs.
    """

    def inverse_read_command(self, command):
        if command.id in _VIRTUAL_RESULT_IDS:
            return [command]
        return super().inverse_read_command(command)

    def forward_read_command(self, command):
        if command.id in _VIRTUAL_RESULT_IDS:
            return [command]
        return super().forward_read_command(command)

    def inverse(self, cmd):
        if cmd.id in _VIRTUAL_RESULT_IDS:
            return [cmd]
        return super().inverse(cmd)

    def forward(self, cmd):
        if cmd.id in _VIRTUAL_RESULT_IDS:
            return [cmd]
        return super().forward(cmd)

__all__ = ["VirtualPassthroughCommandRewriter"]