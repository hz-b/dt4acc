import enum


class CalculationStates(enum.Enum):
    pending = "pending"
    executing = "executing"
    finished = "finished"
    error = "error"
