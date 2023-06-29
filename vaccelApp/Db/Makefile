TOP=../..
include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS BELOW HERE

# Combining all files into one ...
# split into templates
DB += digital_twin_templates.db
# and records
DB += digital_twin_records.db

# the actual database required by the files included above
DB += offset.rec
DB += transfer_function.rec
DB += sextupole_transfer_function.rec
DB += power_converter.rec
DB += power_converter_fanout.rec
DB += power_converter_relay.rec

DB += muxer_elements.rec
DB += quadrupole_names.json


DB += beam.rec
# If <anyname>.db template is not named <anyname>*.template add
# <anyname>_TEMPLATE = <templatename>

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD EXTRA GNUMAKE RULES BELOW HERE

# PYTHON=python3
# PYTHON_EXPORT_SCRIPT=../magnet_info_from_db.py
# PYTHON_EXPORT_STAMP=python_export_stamp
# TOUCH=touch

# power_converter_fanout.inc : $(PYTHON_EXPORT_STAMP)
#
# transfer_function.inc : $(PYTHON_EXPORT_STAMP)
#
# $(PYTHON_EXPORT_STAMP) :
#	$(PYTHON) $(PYTHON_EXPORT_SCRIPT)
#	$(TOUCH) $@
