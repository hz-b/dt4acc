import asyncio

import numpy as np
from at import shift_elem

from dt4acc.bl.event import Event
from ..interfaces.element_interface import ElementInterface
from ..model.element_upate import ElementUpdate


def estimate_shift(element, eps=1e-8):
    """
    Todo: get it upstreamed into pyat
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


class ElementProxy(ElementInterface):
    def __init__(self, obj, *, element_id):
        self._obj = obj
        self.element_id = element_id
        self.on_update_finished = Event()
        self.on_changed_value = Event()

    def __repr__(self):
        return f"{self.__class__.__name__}({self._obj}, element_id={self.element_id})"

    def update_roll(self, *, roll):
        """
        Todo: implement setting roll

        """
        # return
        self._obj.set_tilt(roll)

    async def update_shift(self, *, dx=None, dy=None):
        """
        todo: find out if there is a shift

        Push updated value back to sender?
        """

        assert dx is not None or dy is not None

        element, = self._obj

        shift = estimate_shift(element)
        if dx is None:
            dx = shift[0]
        if dy is None:
            dy = shift[1]
        shift_elem(element, dx, dy)

        # look what really happened
        element, = self._obj
        dxr, _, dyr, _, _, _ = estimate_shift(element)
        return
        asyncio.create_task(self.on_changed_value.trigger(
            ElementUpdate(element_id=self.element_id, property_name="dx", value=value)
        ))
        asyncio.create_task(self.on_changed_value.trigger(
            ElementUpdate(element_id=self.element_id, property_name="dy", value=value)
        ))

    async def update(self, property_id: str, value, element_data):
        """
        Todo:
            activate update calculations again
        """
        if value is not None:
            assert np.isfinite(value)

        element, = self._obj
        method_name = "set_" + property_id
        if method_name == "set_x":
            # Todo: check that lattice placement works on the original lattice
            #       and that this is not a copy
            await self.update_shift(dx=value)
        elif method_name == "set_y":
            await self.update_shift(dy=value)
        elif method_name == "set_roll":
            await self.update_roll(roll=value)
        elif method_name == "set_im":
            element.update(K=value * element_data.hw2phys)

        elif method_name in ["set_rdbk", "set_K"]:
            pass
        else:
            method = getattr(self._obj, method_name)
            await method(value)

        await self.on_update_finished.trigger(None)


class AddOnElementProxy(ElementProxy):
    """Proxy for an element whose update is to be relayed to
    another element
    """

    def __init__(self, obj, *, element_id, host_element_id):
        super().__init__(obj, element_id=element_id)
        self.host_element_id = host_element_id

    def __str__(self):
        return f"{self.__class__.__name__}({self._obj}, element_id={self.element_id}, host_element_id={self.host_element_id})"

    def update(self, property_id: str, value):
        raise NotImplementedError("Needs to be implemented for specific case")


class KickAngleCorrectorProxy(AddOnElementProxy):
    """
    Todo:
        already third layer
    """

    def __init__(self, obj, *, correction_plane, **kwargs):
        assert correction_plane in ["horizontal", "vertical"]
        self.correction_planes = correction_plane
        super().__init__(*obj, **kwargs)

    async def update_kick(self, *, kick_x=None, kick_y=None):
        """updates requested kick
        """
        kick_angles = self._obj.KickAngle.copy()
        for idx, kick in enumerate([kick_x, kick_y]):
            if kick is not None:
                kick_angles[idx] = kick
        self._obj.KickAngle = kick_angles

        kick_angles = self._obj.KickAngle
        for i, kick in enumerate([kick_x, kick_y]):
            if kick is not None:
                await self.on_changed_value.trigger(
                    ElementUpdate(element_id=self.element_id, property_name="K", value=kick_angles[i])
                )

    async def update(self, property_id: str, value):
        assert property_id == "K"
        method_name = "set_" + property_id
        if method_name == "set_K":
            """needs to know if it is x or y
            """
            if self.correction_planes == "horizontal":
                self.update_kick(kick_x=value)
            elif self.correction_planes == "vertical":
                self.update_kick(kick_y=value)
            else:
                raise ValueError(
                    f"{self.element_id}, updating: did not expect to use (coordinate) {self.correction_planes}"
                )
        else:
            raise ValueError(f"{self.element_id}: property {property_id} unknown")

        await self.on_update_finished.trigger(None)
