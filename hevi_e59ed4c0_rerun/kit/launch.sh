#!/bin/bash
# usage: launch.sh <build: base|hevi> <name> <hevi_arm.py args...>
# base = ba2b28ce CPU Release pip --target install; hevi = e59ed4c0 CPU Release build here
set -u
W=/data2/ai_workspace/worker2/hevi
B=$1; N=$2; shift 2
case $B in base) SITE=/data2/ai_workspace/worker1/s1rev/site-fix2;; hevi) SITE=$W/site-hevi;; esac
mkdir -p $W/runs/$B
out=$W/runs/$B/$N
[ -f $out.json ] && { echo "$B/$N done"; exit 0; }
PYTHONPATH=$SITE CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 setsid nohup \
  /data2/ai_workspace/worker1/lmft/venv/bin/python3.11 $W/kit/hevi_arm.py --out $out "$@" > $out.out 2>&1 < /dev/null &
echo "$B/$N $!"
