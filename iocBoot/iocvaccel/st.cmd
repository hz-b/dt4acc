#!../../bin/linux-x86_64/vaccel

< envPaths

cd "${TOP}"

# Won't be left in the environment Path
epicsEnvSet("PYTHONPATH","$(TOP)/src")
epicsEnvSet("CALCULATION_ENGINE", "DEFAULT")
epicsEnvSet("EPICS_PVAS_INTF_LIST", "0.0.0.0")     # Listen on all interfaces for PVAccess
epicsEnvSet("EPICS_PVA_ADDR_LIST", "0.0.0.0")      # PVA Address list (broadcast network)
epicsEnvSet("EPICS_PVAS_SERVER_PORT", "5075")      # PVA Server port
epicsEnvSet("EPICS_CAS_INTF_ADDR_LIST", "0.0.0.0") # Listen on all interfaces for Channel Access
epicsEnvSet("EPICS_CA_ADDR_LIST", "0.0.0.0")       # CA Address list (broadcast network)
epicsEnvSet("EPICS_CA_SERVER_PORT", "5064")        # CA Server port

## Register all support components
dbLoadDatabase "dbd/vaccel.dbd"
vaccel_registerRecordDeviceDriver pdbbase

#- Run this to trace the stages of iocInit
#traceIocInit

dbLoadTemplate "db/digital_twin_templates.db", "PREFIX=$(DT4ACC_PREFIX)"
dbLoadRecords "db/digital_twin_records.db", "PREFIX=$(DT4ACC_PREFIX)"
pydev("from dt4acc import command; update=command.update; publish=command.publish")
pydev("from dt4acc.device_interface import muxer; mux = muxer.build_muxer(prefix='$(DT4ACC_PREFIX)')")

cd "${TOP}/iocBoot/${IOC}"
../../bin/linux-x86_64/softIocPVA
iocInit

