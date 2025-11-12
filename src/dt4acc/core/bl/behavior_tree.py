# python
# File: src/dt4acc/core/bl/behavior_tree.py
import asyncio
from enum import Enum
from typing import Callable, Awaitable, List, Optional

Status = Enum("Status", "SUCCESS FAILURE RUNNING")


class Node:
    async def tick(self) -> Status:
        raise NotImplementedError


class Sequence(Node):
    def __init__(self, children: List[Node]):
        self.children = children

    async def tick(self) -> Status:
        for child in self.children:
            res = await child.tick()
            if res is not Status.SUCCESS:
                return res
        return Status.SUCCESS


class Action(Node):
    def __init__(self, coro_factory: Callable[[], Awaitable]):
        """
        coro_factory: a callable that returns an awaitable when called.
        This allows lazy creation of the coroutine so that each tick executes fresh.
        """
        self.coro_factory = coro_factory

    async def tick(self) -> Status:
        try:
            await self.coro_factory()
            return Status.SUCCESS
        except asyncio.CancelledError:
            raise
        except Exception:
            return Status.FAILURE


class WaitUntilCalculationsComplete(Node):
    """
    Polls accelerator's twiss/orbit DelayExecution pending_task until they're
    either None or finished. Useful to ensure calculations started by updates
    complete before continuing.
    """
    def __init__(self, acc_mgr, poll_interval: float = 0.05, timeout: Optional[float] = 10.0):
        self.acc_mgr = acc_mgr
        self.poll_interval = poll_interval
        self.timeout = timeout

    async def _pending_done(self, task):
        if task is None:
            return True
        if task.done():
            return True
        return False

    async def tick(self) -> Status:
        start = asyncio.get_event_loop().time()
        while True:
            acc = self.acc_mgr.accelerator
            twiss_task = getattr(acc, "twiss_calculation_delay", None)
            orbit_task = getattr(acc, "orbit_calculation_delay", None)

            t_pending = getattr(twiss_task, "pending_task", None) if twiss_task else None
            o_pending = getattr(orbit_task, "pending_task", None) if orbit_task else None

            t_done = await self._pending_done(t_pending)
            o_done = await self._pending_done(o_pending)

            if t_done and o_done:
                return Status.SUCCESS

            if self.timeout is not None and (asyncio.get_event_loop().time() - start) > self.timeout:
                return Status.FAILURE

            await asyncio.sleep(self.poll_interval)


# Helper orchestration function used by handlers
async def handle_power_converter_set_with_bt(
    update_manager,
    acc_mgr,
    pc_name: str,
    value,
    property_name,
    *,
    poll_interval: float = 0.05,
    timeout: Optional[float] = 10.0,
):
    """
    Build and run a small BT sequence:
      1) Update power converter set via UpdateManager (existing path)
      2) Wait until accelerator calculations (twiss/orbit) finish

    Usage: call this from your PV write handler instead of calling UpdateManager.update directly.
    """
    # Action to call the existing update path for the device
    action_update_pc = Action(lambda: update_manager.update(device_id=pc_name, property_name=property_name, value=value))

    # Wait node to ensure calculations finish before returning
    wait_node = WaitUntilCalculationsComplete(acc_mgr, poll_interval=poll_interval, timeout=timeout)

    root = Sequence([action_update_pc, wait_node])
    res = await root.tick()
    return res
