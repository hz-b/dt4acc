#!/bin/sh


# just to make sure
T_DIR=`pwd`

echo "Current directory: ${T_DIR}"

cd ../../

export LD_LIBRARY_PATH=`pwd`/lib:$LD_LIBRARY_PATH

cd ${T_DIR}

./st.cmd
