#!/bin/sh

CAMONITOR=camonitor

PREFIX=Pierre:DT
ELEMENT=q3m2t8r


ELEMENT_PVS='im:dItest im:ImuxProxy im:mux:active im:Imux par:hw2phys im:I y:set Cm:set Cm:rdbk'
BEAM_PVS='orbit:found orbit:fixed_point orbit:eps orbit:im:eps working_point:x working_point:y'
CALCULATION_PVS='dt:delayed-calcs dt:calcs beam:orbit:calc_time beam:twiss:calc_time'
PVS="QSPAZR:set TUNEZR:rdH TUNEZR:rdV"


do_expand () {
    local prefix=$1
    local pvs=$2
    local res=""

    for i in $pvs
    do
	res="$res $prefix:$i"
    done
    echo $res
    return 0
}

CALCULATION_EXPANED_PVS=`do_expand "$PREFIX" "$CALCULATION_PVS"`
ELEMENT_EXPANED_PVS=`do_expand "$PREFIX:$ELEMENT" "$ELEMENT_PVS"`
BEAM_EXPANED_PVS=`do_expand "$PREFIX:beam" "$BEAM_PVS"`
EXPANDED_PVS=`do_expand "$PREFIX" "$PVS"`

ALL_PVS="$EXPANDED_PVS $CALCULATION_EXPANED_PVS $BEAM_EXPANED_PVS $ELEMENT_EXPANED_PVS"

echo "monitoring the following pvs"
echo "  " $ALL_PVS
echo

"$CAMONITOR" $ALL_PVS
