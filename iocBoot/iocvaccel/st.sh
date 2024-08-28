#!/bin/sh

if [ -z ${DT4ACC_PREFIX} ]
then
  DT4ACC_PREFIX=Anonym:DT
fi

export DT4ACC_PREFIX

# just to make sure
T_DIR=`pwd`
echo "Using prefix DT4ACC_PREFIX=${DT4ACC_PREFIX}"
echo "Current directory: ${T_DIR}"

cd ../../

export LD_LIBRARY_PATH=`pwd`/lib:$LD_LIBRARY_PATH

cd ${T_DIR}

./st.cmd
