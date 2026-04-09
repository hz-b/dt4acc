import logging
from typing import Tuple

import numpy as np
from at import shift_elem

from dt4acc_lib.core.interfaces.simulator.element import ElementInterface

logger = logging.getLogger("accml")


def estimate_shift(element, eps=1e-8):
    """
    Todo: get it upstreamed into pyat
    todo: currently this is very pyat specific element update
    Estimate the shift values for an element.

    Args:
        element: The element to estimate shift for.
        eps: Tolerance value for consistency check.

    Returns:
        np.ndarray: Computed shift values.

    Raises:
        AssertionError: If standard deviation exceeds the tolerance.
    """
    try:
        down_stream_shift = element.T1
    except AttributeError:
        down_stream_shift = np.zeros([6], float)
    try:
        up_stream_shift = element.T2
    except AttributeError:
        up_stream_shift = np.zeros([6], float)

    prep = np.array([down_stream_shift, -up_stream_shift])
    shift = prep.mean(axis=0)

    # shifts can be applied to more than one element, these are now
    # expected to have all the same shift.
    assert (np.absolute(prep.std(axis=0)) < eps).all()
    return shift


def manipulate_kick(
    kick_angles: Tuple[float, float], kick_x=None, kick_y=None
) -> Tuple[float, float]:
    kick_angles = kick_angles.copy()
    if kick_x is not None:
        kick_angles[0] = kick_x
    if kick_y is not None:
        kick_angles[1] = kick_y
    return kick_angles


class ElementProxy(ElementInterface):
    """
    Proxy class for an accelerator element to handle interactions and updates.

    Attributes:
        _obj: The underlying accelerator element.
        element_id: Identifier for the element.
        on_update_finished: Event triggered upon update completion.
        on_changed_value: Event triggered upon value change.
    """

    def __init__(self, obj, *, element_id: str, name: str = None):
        self._obj = obj
        self.element_id = element_id
        self.name = name

    def get_name(self) -> str:
        if self.name:
            return self.name
        return self.element_id

    def __repr__(self):
        return f"{self.__class__.__name__}({self._obj}, element_id={self.element_id})"

    def update_roll(self, *, roll):
        """
        Todo: implement setting roll
        Set the roll of the element
        """
        self._obj.set_tilt(roll)

    async def update_shift(self, *, dx=None, dy=None):
        """
        Update the element shift.

        Args:
            dx: Shift in x-direction.
            dy: Shift in y-direction.

        Raises:
            AssertionError: If both dx and dy are None.
        """
        assert dx is not None or dy is not None, "Either dx or dy must be provided"

        (element,) = self._obj
        shift = estimate_shift(element)

        dx = dx if dx is not None else shift[0]
        dy = dy if dy is not None else shift[1]

        # call AT shift element
        shift_elem(element, dx, dy)

        # look what really happened
        (element,) = self._obj
        dxr, _, dyr, _, _, _ = estimate_shift(element)
        pass

    async def _delta_update(self, property_id: str, value: object):
        """
        Todo:
            This implementation is incorrect! Remove me!

            The delta is relative to some state of object ...
            Needs to be reviewed if it should be handled within this
            proxy

            Should that be rather handled at the backend layer?
        """
        raise AssertionError("delta update should not be handled by simulation backend or mexec!")
        ref = self.peek(property_id)
        t_val = value + ref
        logger.info("delta update %s.%s: ref %s, val %s -> %s",
                    self.element_id, property_id, ref, value, t_val)
        return await self._update(property_id, t_val)

    async def update(self, property_id: str, value: object):
        """
        Update element properties dynamically based on property_id.

        Args:
            property_id: The property to update.
            value: The value to set.
            element_data: Element-specific data required for update.

        Raises:
            ValueError: If an unknown property is specified.

        Todo: is that Liaison management?
              the inverse way
        """
        assert property_id[:6] != "delta_", (
            f"properties like {property_id}"
            " starting with delta should not end up here"
        )

        if value is not None:
            assert np.isfinite(value), "Value must be finite"

        return await self._update(property_id, value)

    async def _update(self, property_id: str, value: object):

        (element,) = self._obj
        method_name = f"set_{property_id}"

        if method_name == "set_x":
            await self.update_shift(dx=value)
        elif method_name == "set_y":
            await self.update_shift(dy=value)
        elif method_name == "set_roll":
            await self.update_roll(roll=value)
        elif method_name == "set_im":
            raise AssertionError("should not end up here")
            # val = value * element_data.hw2phys
            # element_type = str(element).split('\n')[0]
        elif method_name == "set_main_strength":
            element_type = element.__class__.__name__
            if "Sextupole" in element_type:
                element.update(H=value)
            elif "Quadrupole" in element_type:
                element.update(K=value)
            else:
                raise NotImplementedError(
                    f"Don't know how to set main strength for element {element_type}"
                )
        elif method_name == "set_freq":
            element.update(Frequency=value * 1000)
        elif method_name in ["set_rdbk", "set_K"]:
            pass
        elif method_name == "set_x_kick":
            element.update(KickAngle=manipulate_kick(element.KickAngle, kick_x=value))
        elif method_name == "set_y_kick":
            element.update(KickAngle=manipulate_kick(element.KickAngle, kick_y=value))
        elif method_name == "set_frequency":
            # should be ok for AT
            element.update(Frequency=value)
            # raise AssertionError("Cavity control not yet declared as functional, have a look to the line below")
        else:
            method = getattr(element, method_name)
            await method(value)

    def peek(self, property_id: str) -> float:
        assert property_id[:6] != "delta_", (
            f"properties like {property_id}"
            " starting with delta should not end up here"
        )

        if property_id in ["K", "H", "main_strength"]:
            return self.peek_main_strength(property_id)
        elif property_id in ["x_kick", "y_kick"]:
            return self.peek_kick(property_id)
        elif property_id in ["frequency"]:
            return self.peek_frequency()
        else:
            raise NotImplementedError(
                f"handling property {property_id} not (yet) implemented"
            )

    def peek_frequency(self):
        (element,) = self._obj
        return element.Frequency

    def peek_main_strength(self, property_id: str):
        (element,) = self._obj
        element_type = element.__class__.__name__
        if element_type == "Quadrupole":
            assert property_id in ["K", "main_strength"]
            return element.K
        elif element_type == "Sextupole":
            if property_id not in ["H", "main_strength"]:
                raise AssertionError(
                    f"Not handling {property_id} for element {element_type}"
                )
            return element.H
        else:
            raise NotImplementedError(
                f"main strength not implemented for element {element_type}"
            )

    def peek_kick(self, property_id: str):
        (element,) = self._obj
        lut = dict(x_kick=0, y_kick=1)
        try:
            idx = lut[property_id]
        except KeyError as ke:
            raise AssertionError(f"Did not expect kick {property_id}")
        return element.KickAngle[idx]



class AddOnElementProxy(ElementProxy):
    """
    Proxy for an element whose updates are relayed to another element.

    Attributes:
        host_element_id: ID of the host element.
    """

    def __init__(self, obj, *, element_id, host_element_id):
        super().__init__(obj, element_id=element_id)
        self.host_element_id = host_element_id

    def __str__(self):
        return f"{self.__class__.__name__}({self._obj}, element_id={self.element_id}, host_element_id={self.host_element_id})"

    def update(self, property_id: str, value, element_data):
        raise NotImplementedError("Needs to be implemented for specific case")


class KickAngleCorrectorProxy(AddOnElementProxy):
    """
    Proxy for handling kick angle corrections in a specific plane.

    Attributes:
        correction_plane: Specifies whether correction is horizontal or vertical.
    """

    def __init__(self, obj, **kwargs):
        super().__init__(*obj, **kwargs)

    async def update_kick(self, *, kick_x=None, kick_y=None):
        """
        Update kick angles for the corrector element.

        Args:
            kick_x: Horizontal kick angle.
            kick_y: Vertical kick angle.
            element_data: Element-specific conversion data.

        Todo: review if this code is still neede
        """
        element = self._obj
        if kick_x is not None:
            kick_x = kick_x
        if kick_y is not None:
            kick_y = kick_y
        element.update(
            KickAngle=manipulate_kick(self._obj.KickAngle, kick_x=kick_x, kick_y=kick_y)
        )

    async def update(self, property_id: str, value):
        """
        Handle updates for the corrector element.

        Args:
            property_id: The property to update (should be 'im').
            value: The value to set.
            element_data: Element-specific conversion data.

        Raises:
            ValueError: If an unknown property is specified.
        """
        assert property_id[:6] != "delta_", (
            f"properties like {property_id}"
            " starting with delta should not end up here"
        )

        if property_id == "x_kick":
            await self.update_kick(kick_x=value)
        elif property_id == "y_kick":
            await self.update_kick(kick_y=value)
        else:
            raise ValueError(f"Unexpected property {property_id} for kick corrector")

    def peek(self, property_id: str) -> float:
        assert property_id[:6] != "delta_", f"properties like {property_id} starting with delta should not end up here"

        element = self._obj

        if property_id == "x_kick":
            return element.KickAngle[0]
        elif property_id == "y_kick":
            return element.KickAngle[1]
        else:
            raise ValueError(f"Unexpected property {property_id} for kick corrector")
