#!/bin/bash
# dt ladder (dx 5 km, u 400) and g = 0 control; arms run detached in parallel.
# usage: run_ladder.sh <site-main> <outdir>
# Reused from run_all.sh (same setup): b_lmars_u400 (scheme 9, cfl 0.3),
# i_lmars_u400_cfl015 (scheme 9, cfl 0.15), h_lmars_u400_impl1 (scheme 1, cfl 0.3).
set -u
K=$(dirname "$(readlink -f "$0")")
M=$1; O=$2
mkdir -p "$O"
export CUDA_VISIBLE_DEVICES=
run() { name=$1; shift; PYTHONPATH=$M setsid nohup python "$K/run_arm.py" --out "$O/$name" "$@" > "$O/$name.out" 2>&1 < /dev/null & echo "$name $!"; }
run L9_cfl0075   --solver lmars --u 400 --implicit 9 --cfl 0.075
run L9_cfl00375  --solver lmars --u 400 --implicit 9 --cfl 0.0375
run L1_cfl015    --solver lmars --u 400 --implicit 1 --cfl 0.15
run L1_cfl0075   --solver lmars --u 400 --implicit 1 --cfl 0.075
run L1_cfl00375  --solver lmars --u 400 --implicit 1 --cfl 0.0375
run G0_u400_grav0 --solver lmars --u 400 --implicit 9 --cfl 0.3 --grav0
