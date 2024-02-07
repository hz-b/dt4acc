#!../../bin/linux-x86_64/vaccel

#- You may have to change vaccel to something else
#- everywhere it appears in this file

< envPaths

cd "${TOP}"

# Won't be left in the environment Path
epicsEnvSet("PYTHONPATH","$(TOP)/src")
epicsEnvSet("CALCULATION_ENGINE", "DEFAULT")


# Must be specified outside of this directory? switch to static ?
# epicsEnvSet("LD_LIBRARY_PATH","$(TOP)/lib:")
epicsEnvSet("PREFIX","Pierre:DT")

## Register all support components
dbLoadDatabase "dbd/vaccel.dbd"
vaccel_registerRecordDeviceDriver pdbbase


#- Set this to see messages from mySub
#var mySubDebug 1

#- Run this to trace the stages of iocInit
#traceIocInit

dbLoadTemplate "db/digital_twin_templates.db", "PREFIX=$(PREFIX)"
dbLoadRecords "db/digital_twin_records.db", "PREFIX=$(PREFIX)"
pydev("from dt4acc import command; update=command.update; publish=command.publish")
pydev("from dt4acc.device_interface import muxer; mux = muxer.build_muxer(prefix='$(PREFIX)')")

cd "${TOP}/iocBoot/${IOC}"
iocInit

## Start any sequence programs
#seq sncExample, "user=mfp"
