#!/bin/bash
# usage: run_chk.sh <workdir> <build...>   builds: base fix2 roe (site-<build> = pip --target install)
set -u
K=$(dirname "$(readlink -f "$0")"); W=$1; shift
export CUDA_VISIBLE_DEVICES=
for n in "$@"; do
  mkdir -p "$W/chkruns/$n"
  while read name args; do
    [ -z "$name" ] && continue
    out="$W/chkruns/$n/$name"
    [ -f "$out.json" ] && { echo "$n/$name done"; continue; }
    ps -eo args | grep -v grep | grep -q -- "--out $out " && { echo "$n/$name running"; continue; }
    PYTHONPATH=$W/site-$n setsid nohup python "$K/chk_arm.py" --out "$out" $args > "$out.out" 2>&1 < /dev/null &
    echo "$n/$name $!"
  done <<'ARMS'
colU_s1   --scheme 1 --column --nx2 4
colU_s9   --scheme 9 --column --nx2 4
colS_s1   --scheme 1 --column --nx2 4 --shear
colS_s9   --scheme 9 --column --nx2 4 --shear
colUn2_s1 --scheme 1 --column --nx2 4 --noise 1e-2
colUn2_s9 --scheme 9 --column --nx2 4 --noise 1e-2
colSn2_s1 --scheme 1 --column --nx2 4 --shear --noise 1e-2
colSn2_s9 --scheme 9 --column --nx2 4 --shear --noise 1e-2
boxU_s1   --scheme 1
boxU_s9   --scheme 9
boxS_s1   --scheme 1 --shear
boxS_s9   --scheme 9 --shear
moist_s1  --scheme 1 --column --nx2 4 --moist
moist_s9  --scheme 9 --column --nx2 4 --moist
moistrest_s9 --scheme 9 --column --nx2 4 --moist --u0 0 --noise 0
box200_s1 --scheme 1 --dx 200e3
ARMS
done
