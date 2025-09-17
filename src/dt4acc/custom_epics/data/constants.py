from dataclasses import dataclass

cavity_names = ["CAV"]
#bessy ii defaults

@dataclass
class Ringparameters:
    freq: float
    brho: float
    energy: float

ring_parameters = Ringparameters(freq=0.0, brho=5.67229387129245, energy=629e6)

special_pvs = {
    "bpm_pv": "MDIZ2T5G",
    "master_clock": "MCLKHX251C",
    "current": "MDIZ3T5G",
}

@dataclass
class Config:
    n_elements : int

config = Config(n_elements=1500)
