#!/bin/bash
# usage: run_all.sh <site-main> <site-pbar> <outdir>
# site-*: pip --target installs of the main build and of main + lmars-energy-flux-pbar.patch
set -u
K=$(dirname "$(readlink -f "$0")")
M=$1; P=$2; O=$3
mkdir -p "$O"
export CUDA_VISIBLE_DEVICES=
run() { name=$1; site=$2; shift 2; PYTHONPATH=$site python "$K/run_arm.py" --out "$O/$name" "$@" > "$O/$name.out" 2>&1 & }
[ -z "${ONLY:-}" ] || [ "${ONLY}" = "abd" ] && {
run a0_lmars_u0_nonoise "$M" --solver lmars --u 0   --noise 0
run a_lmars_u0          "$M" --solver lmars --u 0
run b_lmars_u400        "$M" --solver lmars --u 400
run d_hllc_u400         "$M" --solver hllc  --u 400
}
[ -z "${ONLY:-}" ] || [ "${ONLY}" = "c" ] && run c_lmars_pbar_u400 "$P" --solver lmars --u 400
# diagnostic arms (beyond the brief): same as b with explicit vertical / covariance off
[ -z "${ONLY:-}" ] || [ "${ONLY}" = "ef" ] && {
run e_lmars_u400_explicit "$M" --solver lmars --u 400 --implicit 0
SNAP_FLUX_COVARIANCE=0 run f_lmars_u400_nocov "$M" --solver lmars --u 400
}
[ "${ONLY:-}" = "gh" ] || [ -z "${ONLY:-}" ] && {
run g_hllc_u400_explicit  "$M" --solver hllc  --u 400 --implicit 0
run h_lmars_u400_impl1    "$M" --solver lmars --u 400 --implicit 1
}
[ "${ONLY:-}" = "i" ] || [ -z "${ONLY:-}" ] && run i_lmars_u400_cfl015 "$M" --solver lmars --u 400 --cfl 0.15
wait
