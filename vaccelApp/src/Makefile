TOP=../..

include $(TOP)/configure/CONFIG
include $(PYDEVICE)/configure/CONFIG.PyDevice
#----------------------------------------
#  ADD MACRO DEFINITIONS BELOW HERE

# Use typed rset structure (see 3.16.1 release notes)
USR_CPPFLAGS += -DUSE_TYPED_RSET

# Build an IOC support library
LIBRARY_IOC += vaccelSupport

vaccelSupport_LIBS += $(EPICS_BASE_IOC_LIBS)

# Auto-generate a header file containing a version string.
# Version comes from the VCS if available, else date+time.
GENVERSION = vaccelVersion.h
# Macro name
GENVERSIONMACRO = vaccelVERSION

# Build the IOC application
PROD_IOC = vaccel

# vaccel.dbd will be created and installed
DBD += vaccel.dbd

# vaccel.dbd will include these files:
vaccel_DBD += base.dbd

# vaccel_registerRecordDeviceDriver.cpp derives from vaccel.dbd
vaccel_SRCS += vaccel_registerRecordDeviceDriver.cpp

# Build the main IOC entry point where needed
vaccel_SRCS_DEFAULT += vaccelMain.cpp
vaccel_SRCS_vxWorks += -nil-

vaccel_DBD += pydev.dbd
vaccel_LIBS += pydev

# Link QSRV (pvAccess Server) if available
ifdef EPICS_QSRV_MAJOR_VERSION
    vaccel_LIBS += qsrv
    vaccel_LIBS += $(EPICS_BASE_PVA_CORE_LIBS)
    vaccel_DBD += PVAServerRegister.dbd
    vaccel_DBD += qsrv.dbd
endif

# Finally link IOC to the EPICS Base libraries
vaccel_LIBS += $(EPICS_BASE_IOC_LIBS)

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD EXTRA GNUMAKE RULES BELOW HERE

# Explicit dependency needed for generated header file
devvaccelVersion$(DEP): $(COMMON_DIR)/$(GENVERSION)
