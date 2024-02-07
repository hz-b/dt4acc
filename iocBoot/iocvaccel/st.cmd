#!../../bin/linux-x86_64/vaccel

< envPaths

cd "${TOP}"

# Won't be left in the environment Path
epicsEnvSet("PYTHONPATH","$(TOP)/src")
epicsEnvSet("CALCULATION_ENGINE", "DEFAULT")


epicsEnvSet("PREFIX","Pierre:DT")

## Register all support components
dbLoadDatabase "dbd/vaccel.dbd"
vaccel_registerRecordDeviceDriver pdbbase

#- Run this to trace the stages of iocInit
#traceIocInit

dbLoadTemplate "db/digital_twin_templates.db", "PREFIX=$(PREFIX)"
dbLoadRecords "db/digital_twin_records.db", "PREFIX=$(PREFIX)"
pydev("from dt4acc import command; update=command.update; publish=command.publish")
pydev("from dt4acc.device_interface import muxer; mux = muxer.build_muxer(prefix='$(PREFIX)')")

cd "${TOP}/iocBoot/${IOC}"
iocInit

