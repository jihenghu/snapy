#!/bin/bash
# Small-cfl ladder arms with checkpoints every 0.05 d. Rerunning this script after
# the processes were killed resumes each arm from its last checkpoint (bitwise).
# usage: run_ladder_resume.sh <site-main> <outdir>
set -u
K=$(dirname "$(readlink -f "$0")")
M=$1; O=$2
mkdir -p "$O"
export CUDA_VISIBLE_DEVICES=
run() { name=$1; shift
  if [ -f "$O/$name/meta.json" ] && grep -q '"status"' "$O/$name/meta.json"; then echo "$name finished"; return; fi
  PYTHONPATH=$M setsid nohup python "$K/run_arm.py" --out "$O/$name" --resume --ckpt-dt 4320 "$@" >> "$O/$name.out" 2>&1 < /dev/null &
  echo "$name $!"; }
run L9_cfl0075   --solver lmars --u 400 --implicit 9 --cfl 0.075
run L9_cfl00375  --solver lmars --u 400 --implicit 9 --cfl 0.0375
run L1_cfl0075   --solver lmars --u 400 --implicit 1 --cfl 0.075
run L1_cfl00375  --solver lmars --u 400 --implicit 1 --cfl 0.0375
