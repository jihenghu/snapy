#!/bin/bash
# Scheme-1 fix review: same arms at base / fix1 (9825aba9) / fix2 (ba2b28ce).
# usage: run_review.sh <workdir>   (expects <workdir>/site-{base,fix1,fix2} = pip --target installs)
set -u
K=$(dirname "$(readlink -f "$0")"); W=$1
export CUDA_VISIBLE_DEVICES=
for n in base fix1 fix2; do
  mkdir -p "$W/runs/$n"
  while read name args; do
    [ -z "$name" ] && continue
    out="$W/runs/$n/$name"
    [ -f "$out.json" ] && { echo "$n/$name done"; continue; }
    ps -eo args | grep -v grep | grep -q -- "--out $out " && { echo "$n/$name running"; continue; }
    PYTHONPATH=$W/site-$n setsid nohup python "$K/run_arm_xw.py" --out "$out" $args > "$out.out" 2>&1 < /dev/null &
    echo "$n/$name $!"
  done <<'ARMS'
box_dx50_u400_s1  --scheme 1 --dx 50e3  --u0 400
box_dx100_u400_s1 --scheme 1 --dx 100e3 --u0 400
box_dx200_u400_s1 --scheme 1 --dx 200e3 --u0 400
box_dx100_u400_s9 --scheme 9 --dx 100e3 --u0 400
box_dx100_u0_s1_nonoise --scheme 1 --dx 100e3 --u0 0 --noise 0
col_dx100_u400_s1 --scheme 1 --dx 100e3 --u0 400 --nx2 4 --uniform-x2
ARMS
done
