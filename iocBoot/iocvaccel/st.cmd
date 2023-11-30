#!../../bin/linux-x86_64/vaccel

< envPaths

cd "${TOP}"

# Won't be left in the environment Path
epicsEnvSet("PYTHONPATH","$(TOP)/src/:$(PYTHONPATH)")

epicsEnvSet("PREFIX","Pierre:DT")
epicsEnvSet("THOR_SCSI_LATTICE", "$(TOP)/lattices/b2_stduser_beamports_blm_tracy_corr.lat")

## Register all support components
dbLoadDatabase "dbd/vaccel.dbd"
vaccel_registerRecordDeviceDriver pdbbase

#- Run this to trace the stages of iocInit
#traceIocInit

dbLoadTemplate "db/digital_twin_templates.db", "PREFIX=$(PREFIX)"
dbLoadRecords "db/digital_twin_records.db", "PREFIX=$(PREFIX)"
pydev("from dt4acc import accelerator, muxer;")
pydev("vacc = accelerator.build_virtual_accelerator(prefix='$(PREFIX)')")
# start with some offset
# pydev("vacc = accelerator.build_virtual_accelerator(prefix='$(PREFIX)', cmd=accelerator.move_quad_compensate)")

pydev("mux = muxer.build_muxer(prefix='$(PREFIX)')")

cd "${TOP}/iocBoot/${IOC}"
iocInit

