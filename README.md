# Digital twin for accelerators

This twin is based on `epics` and `thor scsi lib`. It is provided
as an Input Output Controller (IOC). The machine is modelled
using `thor scsi lib`. It's engineering to physics space is
implemented by epics records. PyDevice based records are used to
get data from the records into thor-scsi-lib.

## Requirements

* thor scsi lib: with its further requirements
    see https://github.com/jbengtsson/thor-scsi-lib for
    details

    The thor scsi python module has to be available / installed
    for the interpreter used for Pydevice (see next point)

* PyDevice: https://github.com/klemenv/PyDevice
* Epics:    https://github.com/epics-base/epics-base

* For extracting data from the database
    * pymongo
    * pandas
    * numpy
    * bact-math-utils https://github.com/hz-b/bact-math-utils

# Building the twin

1. clone the repository from HZB's gitlab e.g:

   ```
   git clone https://gitlab.helmholtz-berlin.de/acc-tools/dt4cc.git dt4acc
   ```

3. build the IOC

   a. from the root directory of this repository change into directory `vaccelApp/Db/`

   b. extract database data using

      ```shell
      python3 magnet_info_from_db.py
      ```
      Please note: you need to have access to pymongo.bessy.de

   c. change into the repositories root directory and start building the IOC using

      ```shell
      make
      ```

   d. change into the directory `iocBoot/iocvaccel/` and start the IOC with the
      script

      ```shell
      sh st.sh
      ```

