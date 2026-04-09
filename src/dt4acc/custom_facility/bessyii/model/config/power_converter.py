from typing import Hashable

from pydantic import BaseModel


class ResponseModel(BaseModel):
    """General response model for a device reacting to a control input change

    Timeout: whithin this time the device has to answer
    Settle time: after this time the device is expected to be in a stable state
    """

    #: seconds
    timeout: float
    # seconds
    settle_time: float


class PowerConverterInterface(BaseModel):
    #:  e.g., 'CHANNEL:QF1C01A:SP'
    setpoint: str
    #: e.g., 'CHANNEL:QF1C01A:RB'
    readback: str


class PowerConverter(BaseModel):
    id: Hashable
    interface: PowerConverterInterface
    response: ResponseModel

    def get_current(self):
        return 0.0
