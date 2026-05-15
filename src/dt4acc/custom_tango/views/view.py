from dt4acc.core.interfaces.view_interface import ViewInterface
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.views.calculation_result_view import CalculationResultView
from dt4acc_lib.model.output.result import TranslatedReading
from dt4acc_lib.model.utils.command import ReadCommand

logger = get_logger()

# ---------------------------------------------------------------------------
# TangoView — dispatches TranslatedReading results to CalculationResultView
# ---------------------------------------------------------------------------

class TangoView(ViewInterface):
    """
    Receives calculation results from the new backend (dt4acc_lib types) and
    adapts them into what CalculationResultView expects (old model types),
    then calls the appropriate push method.

    Backend types → CalculationResultView interface:

        ReadCommand("track", "pos")         → CalculatedTrack
          CalculatedTrack.track             = list[CalculatedPosition(.name, .x, .y)]
          CalculationResultView.push_orbit  expects .x, .y, .names (flat arrays)
          → _OrbitAdapter bridges this

        ReadCommand("twiss", "parameters")  → Twiss
          Twiss.twiss                       = list[TwissAtPosition(.name, .x, .y)]
          TwissAtPosition.x/y               = TwissParameters(.beta, .alpha, .nu)
          CalculationResultView.push_twiss  expects .x.alpha, .x.beta, .x.nu (flat arrays)
          → _TwissAdapter bridges this

        ReadCommand("tune", "x"/"y")        → Tune(.x, .y)
          TuneDevice attributes: .hor, .vert (plain floats written via DeviceProxy)
          CalculationResultView has no push_tune — we push directly
    """

    def __init__(self, *, prefix: str):
        self._calc_view = CalculationResultView(prefix=prefix)
        self._prefix = prefix

    async def dispatch(self, rcmd: ReadCommand, result: TranslatedReading) -> None:
        """Route a single translated reading to the appropriate push method."""
        try:
            if rcmd.id == "track" and rcmd.property == "pos":
                await self._push_orbit(result)
            elif rcmd.id == "twiss":
                await self._push_twiss(result)
            elif rcmd.id == "tune":
                await self._push_tune(result)
            elif rcmd.id == "chromaticity":
                await self._push_chromaticity(result)
            else:
                logger.debug("TangoView: no handler for %s — skipping", rcmd)
        except Exception as exc:
            logger.error("TangoView.dispatch failed for %s: %s", rcmd, exc)

    async def _push_orbit(self, result: TranslatedReading) -> None:
        (reading,) = result.readings
        track = reading.payload          # CalculatedTrack from new backend
        await self._calc_view.push_orbit(_OrbitAdapter(track))

    async def _push_twiss(self, result: TranslatedReading) -> None:
        (reading,) = result.readings
        twiss = reading.payload          # Twiss from new backend
        await self._calc_view.push_twiss(_TwissAdapter(twiss))

    async def _push_tune(self, result: TranslatedReading) -> None:
        (reading,) = result.readings
        tune = reading.payload
        await self._calc_view.push_tune(tune)

    async def _push_chromaticity(self, result: TranslatedReading) -> None:
        (reading,) = result.readings
        chroma = reading.payload           # Tune(.x, .y) reused for xi_x, xi_y
        await self._calc_view.push_chromaticity(chroma)

    async def push_invalid(self) -> None:
        """
        Push NaN arrays to all virtual devices — called when beam is lost
        so clients can detect invalid/stale data rather than seeing old values.
        """
        await self._calc_view.push_invalid()


# ---------------------------------------------------------------------------
# Adapter: Twiss (new) → TwissWithAggregatedKValues-compatible (old)
#
# CalculationResultView.push_twiss expects:
#   twiss_result.x.alpha  : array-like
#   twiss_result.x.beta   : array-like
#   twiss_result.x.nu     : array-like
#   twiss_result.y.alpha  : array-like
#   twiss_result.y.beta   : array-like
#   twiss_result.y.nu     : array-like
#   (tune is derived separately — not needed here)
#
# Twiss (new backend) has:
#   twiss: list[TwissAtPosition(name, x=TwissParameters(beta,alpha,nu),
#                                    y=TwissParameters(beta,alpha,nu))]
# ---------------------------------------------------------------------------

class _PlaneAdapter:
    """Presents per-plane arrays from a list of TwissAtPosition."""
    __slots__ = ("alpha", "beta", "nu")

    def __init__(self, positions, plane: str):
        self.alpha = [getattr(p, plane).alpha for p in positions]
        self.beta  = [getattr(p, plane).beta  for p in positions]
        self.nu    = [getattr(p, plane).nu    for p in positions]


class _TwissAdapter:
    __slots__ = ("x", "y")

    def __init__(self, twiss):
        positions = twiss.twiss          # list[TwissAtPosition]
        self.x = _PlaneAdapter(positions, "x")
        self.y = _PlaneAdapter(positions, "y")


class _OrbitAdapter:
    __slots__ = ("x", "y", "names", "x0", "found")

    def __init__(self, track):
        self.x     = [p.x    for p in track.track]
        self.y     = [p.y    for p in track.track]
        self.names = [p.name for p in track.track]
        self.x0    = []
        self.found = True

