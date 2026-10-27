#!/bin/bash
# CPU build of e59ed4c0 per README, same config as the ba2b28ce base build
set -e
source /opt/rh/gcc-toolset-13/enable
export TMPDIR=/data2/ai_workspace/worker2/tmp PIP_CACHE_DIR=/data2/ai_workspace/worker2/.pipcache
V=/data2/ai_workspace/worker1/lmft/venv
export PATH=$V/bin:$PATH
cd /data2/ai_workspace/worker2/hevi/src
cmake -B build -DCMAKE_BUILD_TYPE=Release -DNETCDF=ON -DCUDA=OFF -DPython3_EXECUTABLE=$V/bin/python3.11 -DCMAKE_PREFIX_PATH=$V/lib64/python3.11/site-packages/torch/share/cmake > ../cfg.log 2>&1
cmake --build build --parallel 16 > ../build.log 2>&1
$V/bin/python3.11 -m pip install --no-deps --no-build-isolation --target /data2/ai_workspace/worker2/hevi/site-hevi . > ../pip.log 2>&1
echo BUILD_OK
