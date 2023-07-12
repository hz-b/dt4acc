import os
from pathlib import Path
import time
import gtpsa
from thor_scsi.lib import ConfigType
from thor_scsi.factory import accelerator_from_config

t2_file = (
    Path(os.environ["HOME"])
    # / "cpp"
    / "Devel"
    / "gitlab"
    / "dt4acc"
    / "lattices"
    / "b2_stduser_beamports_blm_tracy_corr.lat"
)


acc = accelerator_from_config(t2_file)
conf = ConfigType()
desc = gtpsa.desc(6,3)
x0 = gtpsa.ss_vect_tpsa(desc, 1, 6, gtpsa.default_mapping())
tic = time.time()
acc.propagate(conf, x0)
tac = time.time()
dt = tac - tic
xd = gtpsa.ss_vect_double(0e0, 6, gtpsa.default_mapping())
tic = time.time()
acc.propagate(conf, xd)
tac = time.time()
ddt = tac - tic
print(f"{dt=} {ddt=} {dt/ddt=}")