#!/bin/bash
# usage: build.sh <src_dir> [jobs]   CPU-only Release build, as in the snapy README
source /opt/rh/gcc-toolset-13/enable
source ${VENV:?set VENV to the venv path}/bin/activate
export CUDA_VISIBLE_DEVICES=
cd "$1"
PY=$(which python)
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCUDA=OFF -DNETCDF=ON -DBUILD_TESTS=OFF -DPython3_EXECUTABLE=$PY \
  -DCMAKE_PREFIX_PATH=$($PY -c 'import torch.utils;print(torch.utils.cmake_prefix_path)') > cfg.log 2>&1 || { echo CFGFAIL; exit 1; }
cmake --build build --parallel ${2:-12} > build.log 2>&1 || { echo BUILDFAIL; exit 1; }
echo BUILD_OK
