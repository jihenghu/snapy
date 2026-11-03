"""G6 reference: linear growth rate of 2-D compressible inviscid convection.

Linearised Euler about a hydrostatic column, perturbations ~ exp(i k x + s t),
with v = i u so the operator is real:
    s rho' = -k rho0 v - d(rho0 w)/dz
    s v    =  (k / rho0) p'
    s w    = -(dp'/dz + g rho') / rho0
    s p'   = -w dp0/dz - gamma p0 (k v + dw/dz),   dp0/dz = -rho0 g
Walls z = 0, L impermeable (w = 0): the reflecting wall of ghost rule (c).
Dry deck gas of examples/jupiter_gcm.yaml (:6-8, cv_R 2.5 -> gamma 1.4,
mu from kintera), g = 22 (:126-128), L = 300 km (:59-60).

Discretisations:
  cheb : Chebyshev-Gauss-Lobatto collocation (reference)
  fd2  : second-order staggered finite differences on an arbitrary face list
         (w on faces, rho', v, p' at midpoints), base state exact pointwise

Usage: python -I evp_g6.py <outdir> <gcm280 dir>
"""
import csv
import hashlib
import math
import pickle
import sys

import numpy as np
from scipy import integrate, linalg

OUT, GCM = sys.argv[1], sys.argv[2]
EPS = np.finfo(float).eps
L = 300.0e3
G = 22.0
GAMMA = 1.0 + 1.0 / 2.5  # cv_R = 2.5
try:
    import kintera as k
    op = k.ThermoOptions.from_yaml(f"{GCM}/../snapy/examples/jupiter_gcm.yaml")
    MU = float(k.ThermoX(op).mu[0])
    MU_SRC = f"kintera {k.__version__} ThermoX.mu[0]"
except Exception as e:  # pragma: no cover
    MU, MU_SRC = 2.11239e-3, f"composition H1.5 He0.15 (kintera unavailable: {e})"
RGAS = 8.31446 / MU if "kintera" not in MU_SRC else float(k.constants.Rgas) / MU
CP = GAMMA / (GAMMA - 1.0) * RGAS
GAMMA_D = G / CP
TB, PB = 600.0, 1.0e7          # examples/jupiter_gcm.yaml:184-185
TTOP = 110.0                   # Tmin, :186; the job-569eeedf column ends at 110.00 K


class Column:
    """T(z) with lapse Gam(z); p0 from exact hydrostatic integration."""

    def __init__(self, name, lapse, T_of):
        self.name, self.lapse, self.T = name, lapse, T_of
        self._zc = None
        self._memo = {}

    def lnp(self, z):
        z = np.atleast_1d(z).astype(float)
        out = np.empty_like(z)
        for i, zi in enumerate(z):
            key = float(zi)
            if key in self._memo:
                out[i] = self._memo[key]; continue
            v, _ = integrate.quad(lambda s: G / (RGAS * self.T(s)), 0.0, zi,
                                  epsabs=0.0, epsrel=1e-13, limit=400)
            out[i] = math.log(PB) - v
            self._memo[key] = out[i]
        return out

    def base(self, z):
        T = self.T(z)
        p = np.exp(self.lnp(z))
        rho = p / (RGAS * T)
        return T, p, rho

    def N2(self, z):
        return G / self.T(z) * (GAMMA_D - self.lapse(z))

    def H(self, z):
        return RGAS * self.T(z) / G


# (i) jupiter_gcm dry fit: straight line through the job-569eeedf endpoints
GAM_I = (TB - TTOP) / L
col_i = Column("i: jupiter_gcm linear fit (600 K -> 110 K over 300 km)",
               lambda z: GAM_I + 0.0 * np.asarray(z, float),
               lambda z: TB - GAM_I * np.asarray(z, float))

# (ii) varying lapse: the same troposphere under an isothermal stratosphere,
# joined smoothly by tanh at z_t = 200 km over w = 25 km
ZT, WT = 200.0e3, 25.0e3


def _T_ii(z):
    z = np.asarray(z, float)
    a = np.logaddexp((z - ZT) / WT, -(z - ZT) / WT) - np.logaddexp(ZT / WT, -ZT / WT)
    return TB - GAM_I * (z / 2.0 - WT / 2.0 * a)


col_ii = Column("ii: troposphere (lapse as i) under isothermal stratosphere, tanh join z_t=200 km, w=25 km",
                lambda z: GAM_I * 0.5 * (1.0 - np.tanh((np.asarray(z, float) - ZT) / WT)),
                _T_ii)


def cheb(N):
    x = np.cos(np.pi * np.arange(N + 1) / N)
    c = np.hstack([2.0, np.ones(N - 1), 2.0]) * (-1.0) ** np.arange(N + 1)
    X = np.tile(x, (N + 1, 1)).T
    dX = X - X.T
    D = np.outer(c, 1.0 / c) / (dX + np.eye(N + 1))
    D -= np.diag(D.sum(1))
    return x, D


def assemble_cheb(col, kx, N):
    x, D = cheb(N)
    z = (1.0 - x) * L / 2.0            # z from 0 to L
    D = D * (-2.0 / L)
    T, p, rho = col.base(z)
    dp = -rho * G
    n = N + 1
    iw = np.arange(1, N)               # interior w unknowns
    nw = len(iw)
    # unknown order: rho'(n), v(n), w(nw), p'(n)
    R0, V0, W0, P0 = 0, n, 2 * n, 2 * n + nw
    M = np.zeros((3 * n + nw, 3 * n + nw))
    Dw = D[:, iw]
    # continuity: -k rho0 v - d(rho0 w)/dz
    M[R0:R0 + n, V0:V0 + n] = np.diag(-kx * rho)
    M[R0:R0 + n, W0:W0 + nw] = -(D * rho[None, :])[:, iw]
    # x-momentum
    M[V0:V0 + n, P0:P0 + n] = np.diag(kx / rho)
    # z-momentum at interior points
    M[W0:W0 + nw, P0:P0 + n] = -(D[iw, :]) / rho[iw, None]
    M[W0:W0 + nw, R0:R0 + n] = -np.eye(n)[iw, :] * (G / rho[iw, None])
    # pressure
    M[P0:P0 + n, W0:W0 + nw] = -np.eye(n)[:, iw] * dp[:, None] - GAMMA * p[:, None] * Dw
    M[P0:P0 + n, V0:V0 + n] = np.diag(-GAMMA * p * kx)
    scale = np.concatenate([np.full(n, rho[0]), np.full(n, math.sqrt(GAMMA * p[0] / rho[0])),
                            np.full(nw, math.sqrt(GAMMA * p[0] / rho[0])), np.full(n, p[0])])
    zw = z[iw]
    return M, scale, dict(z=z, zw=zw, slices=(R0, V0, W0, P0, n, nw))


def assemble_fd2(col, kx, faces):
    f = np.asarray(faces, float)
    Nc = len(f) - 1
    c = 0.5 * (f[1:] + f[:-1])
    dz = np.diff(f)
    Tc, pc, rc = col.base(c)
    fi = f[1:-1]                        # interior faces carry w
    _, _, rf = col.base(fi)
    dzv = c[1:] - c[:-1]
    nw = Nc - 1
    R0, V0, W0, P0 = 0, Nc, 2 * Nc, 2 * Nc + nw
    M = np.zeros((3 * Nc + nw, 3 * Nc + nw))
    I = np.arange(Nc)
    M[R0 + I, V0 + I] = -kx * rc
    M[V0 + I, P0 + I] = kx / rc
    M[P0 + I, V0 + I] = -GAMMA * pc * kx
    for i in range(Nc):
        # faces i (below) and i+1 (above); interior face j -> w index j-1
        for jf, sgn in ((i, -1.0), (i + 1, 1.0)):
            if 1 <= jf <= Nc - 1:
                wj = W0 + jf - 1
                M[R0 + i, wj] += -sgn * rf[jf - 1] / dz[i]
                M[P0 + i, wj] += -GAMMA * pc[i] * sgn / dz[i]
                # w interpolated to the midpoint: average of its two faces
                M[P0 + i, wj] += -0.5 * (-rc[i] * G)
    for j in range(1, Nc):
        wj = W0 + j - 1
        a = (fi[j - 1] - c[j - 1]) / dzv[j - 1]       # linear weight to cell j
        M[wj, P0 + j] += -1.0 / (rf[j - 1] * dzv[j - 1])
        M[wj, P0 + j - 1] += 1.0 / (rf[j - 1] * dzv[j - 1])
        M[wj, R0 + j] += -G * a / rf[j - 1]
        M[wj, R0 + j - 1] += -G * (1.0 - a) / rf[j - 1]
    cs = math.sqrt(GAMMA * pc[0] / rc[0])
    scale = np.concatenate([np.full(Nc, rc[0]), np.full(Nc, cs), np.full(nw, cs), np.full(Nc, pc[0])])
    return M, scale, dict(z=c, zw=fi, slices=(R0, V0, W0, P0, Nc, nw))


def _nodes(wv):
    wv = wv / wv[np.argmax(np.abs(wv))]
    sig = np.sign(wv[np.abs(wv) > 1e-3])  # nodes of the bulk mode, not of a ~1e-6 evanescent tail
    return int(np.sum(sig[1:] != sig[:-1]))


def leading(M, scale, info, want_vec=False):
    """largest real eigenvalue whose w has no interior zero (vertical mode 1)."""
    Ms = (M * scale[None, :]) / scale[:, None]   # S^-1 M S
    w, vl, vr = linalg.eig(Ms, left=True, right=True)
    R0, V0, W0, P0, n, nw = info["slices"]
    real = np.where((np.abs(w.imag) <= 1e-9 * np.abs(w)) & (w.real > 0))[0]
    order = real[np.argsort(-w.real[real])]
    j, top_any = None, (w[order[0]].real if len(order) else float("nan"))
    for jj in order:
        if _nodes(vr[W0:W0 + nw, jj].real) == 0:
            j = jj; break
    if j is None:
        return dict(s=float("nan"), kappa=float("nan"), floor=float("nan"), nodes=-1, top_any=top_any)
    s = w[j].real
    x, y = vr[:, j], vl[:, j]
    kappa = np.linalg.norm(x) * np.linalg.norm(y) / abs(np.vdot(y, x))
    floor = kappa * EPS * np.linalg.norm(Ms, 2) / abs(s)
    out = dict(s=s, kappa=kappa, floor=floor, nodes=0, top_any=top_any)
    if want_vec:
        wv = x[W0:W0 + nw].real
        out["zw"] = info["zw"]; out["w"] = wv / wv[np.argmax(np.abs(wv))]
        pv = x[P0:P0 + n].real * scale[P0:P0 + n]
        out["zp"] = info["z"]; out["p"] = pv / pv[np.argmax(np.abs(pv))]
    return out


def shoot_rhs(col, kx, sig):
    def f(z, y):
        w, q = y
        T = col.T(z); Tp = -col.lapse(z); RT = RGAS * T
        Sig = sig + GAMMA * RT * kx * kx / sig
        wp = (G * w / RT - q * Sig) / GAMMA
        rho_p = (-kx * kx * q / sig - (1.0 / RT) * (-G / RT - Tp / T) * w - wp / RT) / sig
        dpp = -sig * w / RT - G * rho_p          # (dp'/dz) / p0
        qp = dpp + q * G / RT
        return [wp, qp]
    return f


def shoot_end(col, kx, sig, rtol, dense=False):
    sol = integrate.solve_ivp(shoot_rhs(col, kx, sig), (0.0, L), [0.0, 1.0], method="DOP853",
                              rtol=rtol, atol=1e-30, dense_output=dense)
    return sol


def shoot_mode1(col, kx, rtol=1e-12):
    """largest sigma with w(L) = 0; checked to have no interior zero of w (mode 1)."""
    zz = np.linspace(0, L, 3001)
    smax = math.sqrt(max(-col.N2(zz).min(), 0.0))
    grid = smax * np.exp(np.linspace(math.log(0.999999), math.log(1e-3), 2000))
    prev_s, prev_w = None, None
    for sg in grid:
        wl = shoot_end(col, kx, sg, 1e-8).y[0, -1]
        if prev_w is not None and np.sign(wl) != np.sign(prev_w):
            from scipy.optimize import brentq
            root = brentq(lambda x: shoot_end(col, kx, x, rtol).y[0, -1], sg, prev_s,
                          xtol=1e-22, rtol=4 * EPS, maxiter=500)
            sol = shoot_end(col, kx, root, rtol, dense=True)
            wz = sol.sol(zz[1:-1])[0]
            return root, _nodes(wz), sol
        prev_s, prev_w = sg, wl
    return float("nan"), -1, None


def contract_faces(Hfun_z, Hfun_v, N):
    """N cells at equal increments of s = int dz/H from the top (the job-569eeedf map)."""
    s = np.concatenate([[0.0], np.cumsum(0.5 * (1.0 / Hfun_v[::-1][1:] + 1.0 / Hfun_v[::-1][:-1])
                                         * -np.diff(Hfun_z[::-1]))])
    targets = np.linspace(0.0, s[-1], N + 1)
    faces = np.interp(targets, s, Hfun_z[::-1])
    faces[0], faces[-1] = L, 0.0
    return faces[::-1]


def read_faces(path):
    with open(path) as fh:
        rows = list(csv.DictReader(fh))
    return np.array([float(r["z_face_m"]) for r in rows])


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


ERR = {}


def main():
    print(f"gas: mu={MU*1e3:.6f} g/mol ({MU_SRC}), R={RGAS:.4f}, gamma={GAMMA}, cp={CP:.3f}, "
          f"g={G}, Gamma_d={GAMMA_D*1e3:.6f} K/km")
    print(f"col i lapse {GAM_I*1e3:.6f} K/km = {GAM_I/GAMMA_D:.6f} Gamma_d")
    for col in (col_i, col_ii):
        zz = np.linspace(0, L, 3001)
        n2 = col.N2(zz)
        print(f"{col.name}: N2 min={n2.min():.4e} at z={zz[n2.argmin()]/1e3:.1f} km, "
              f"max={n2.max():.4e} at z={zz[n2.argmax()]/1e3:.1f} km; "
              f"sqrt(-N2min)={math.sqrt(-n2.min()):.5e} s^-1; T top={col.T(L):.3f} K")

    print("\nmode-1 growth rate vs Lx (shooting, rtol 1e-10)")
    for col in (col_i, col_ii):
        for Lx in (1200e3, 600e3, 300e3, 150e3, 75e3, 37.5e3):
            sg, nz, _ = shoot_mode1(col, 2 * math.pi / Lx, rtol=1e-10)
            print(f"  {col.name[:3]} Lx={Lx/1e3:7.1f} km  sigma1={sg:.10e}  interior zeros of w={nz}")

    LX = 300.0e3
    KX = 2 * math.pi / LX
    print(f"\nseed: Lx = {LX/1e3:.0f} km, kx = {KX:.6e} 1/m, vertical mode 1")

    ref = {}
    for col in (col_i, col_ii):
        key = col.name.split(':')[0] + ':'
        print(f"\nreference, {key}")
        for rt in (1e-9, 1e-11, 1e-13):
            sg, nz, sol = shoot_mode1(col, KX, rtol=rt)
            print(f"  shooting rtol={rt:.0e}: sigma1={sg:.15e} interior zeros={nz}")
        ref[key] = dict(s=sg, sol=sol)
        for N in (24, 32, 48, 64, 96, 128):
            r = leading(*assemble_cheb(col, KX, N))
            print(f"  cheb N={N:4d} mode-1 sigma={r['s']:.15e} rel.err vs shooting={(r['s']-sg)/sg:+.3e} "
                  f"kappa={r['kappa']:.3e} eps-floor={r['floor']:.2e} (largest real any-mode {r['top_any']:.4e})")

    fine = pickle.load(open(f"{GCM}/fine_profile.pkl", "rb"))
    zf = np.array([q["z"] for q in fine]); Hf = np.array([q["H"] for q in fine])
    f5, f10 = read_faces(f"{GCM}/jupiter_gcm_faces_n5.csv"), read_faces(f"{GCM}/jupiter_gcm_faces_n10.csv")
    print(f"\n(j) lists: n5 sha256 {sha(f'{GCM}/jupiter_gcm_faces_n5.csv')}, "
          f"n10 sha256 {sha(f'{GCM}/jupiter_gcm_faces_n10.csv')}")
    for N, fl in ((30, f5), (59, f10)):
        g = contract_faces(zf, Hf, N)
        print(f"  contract map regenerated at N={N}: max|face - csv| = {np.max(np.abs(g - fl)):.3e} m")
    for nm, fl in (("n5", f5), ("n10", f10)):
        dzl = np.diff(fl); cc = 0.5 * (fl[1:] + fl[:-1])
        print(f"  (j) {nm} on column i: dz/H_dry max {np.max(dzl/col_i.H(cc)):.4f} min {np.min(dzl/col_i.H(cc)):.4f}")
    grids_i = {"j n5 (30)": f5, "j n10 (59)": f10,
               "map 118": contract_faces(zf, Hf, 118), "map 236": contract_faces(zf, Hf, 236),
               "map 472": contract_faces(zf, Hf, 472),
               "uni 30": np.linspace(0, L, 31), "uni 59": np.linspace(0, L, 60),
               "uni 118": np.linspace(0, L, 119), "uni 236": np.linspace(0, L, 237),
               "uni 472": np.linspace(0, L, 473),
               "uni 77 (n5 at top)": np.linspace(0, L, 78), "uni 153 (n10 at top)": np.linspace(0, L, 154),
               "uni 100 (deck)": np.linspace(0, L, 101)}
    zz = np.linspace(0, L, 30001); Hii = col_ii.H(zz)
    s_ii = np.trapezoid(1.0 / Hii, zz)
    print(f"\ncol ii contract: int dz/H = {s_ii:.5f}; H bottom/top = {col_ii.H(0)/1e3:.3f}/{col_ii.H(L)/1e3:.3f} km")
    grids_ii = {}
    for n in (5, 10, 20, 40):
        Nn = math.ceil(n * s_ii)
        fl = contract_faces(zz, Hii, Nn)
        dzl = np.diff(fl); cc = 0.5 * (fl[1:] + fl[:-1])
        r = dzl[1:] / dzl[:-1]
        print(f"  n={n}: N={Nn} max dz/H={np.max(dzl/col_ii.H(cc)):.4f}  r min/median/max = "
              f"{r.min():.5f}/{np.median(r):.5f}/{r.max():.5f}")
        grids_ii[f"map n{n} ({Nn})"] = fl
        grids_ii[f"uni {Nn}"] = np.linspace(0, L, Nn + 1)
        if n in (5, 10):
            with open(f"{OUT}/col_ii_faces_n{n}.csv", "w", newline="") as fh:
                wr = csv.writer(fh); wr.writerow(["i", "z_face_m"])
                for i, v in enumerate(fl): wr.writerow([i, f"{v:.6f}"])

    for col, grids in ((col_i, grids_i), (col_ii, grids_ii)):
        s_ref = ref[col.name.split(':')[0] + ':']["s"]
        print(f"\nfd2 mode-1 relative growth-rate error, {col.name[:3]} (ref {s_ref:.12e})")
        for nm, fl in grids.items():
            r = leading(*assemble_fd2(col, KX, fl))
            print(f"  {nm:22s} N={len(fl)-1:4d} sigma={r['s']:.10e} rel.err={(r['s']-s_ref)/s_ref:+.4e} "
                  f"kappa={r['kappa']:.2e} eps-floor={r['floor']:.1e}")
            ERR[(col.name.split(':')[0] + ':', nm)] = ((r['s'] - s_ref) / s_ref, len(fl) - 1, r['floor'])


    # thresholds: asymptotic fd2 model |E| = C N^-p from the two finest levels of each family,
    # floored at 10x the largest eps-scaled bound seen (kappa eps ||M|| / sigma)
    K = lambda c: c.split(":")[0] + ":"
    def find(ck, pre):
        return next(nm for (c, nm) in ERR if c == ck and nm.startswith(pre))
    fam = {("i:", "map"): ["map 236", "map 472"], ("i:", "uni"): ["uni 236", "uni 472"],
           ("ii:", "map"): [find("ii:", "map n20"), find("ii:", "map n40")],
           ("ii:", "uni"): ["uni " + find("ii:", "map n20").split("(")[1][:-1],
                            "uni " + find("ii:", "map n40").split("(")[1][:-1]]}
    F = 10 * max(v[2] for v in ERR.values())
    print(f"\nthreshold floor 10*max(eps-bound) = {F:.2e}")
    model = {}
    for (ck, fk), (a, b) in fam.items():
        Ea, Na, _ = ERR[(ck, a)]; Eb, Nb, _ = ERR[(ck, b)]
        p = math.log(abs(Ea) / abs(Eb)) / math.log(Nb / Na); C = abs(Eb) * Nb ** p
        model[(ck, fk)] = (C, p)
        print(f"  model {ck} {fk}: |E| = {C:.4e} * N^-{p:.3f}")
    gates = {"i:": [("map", 30, "j n5 (30)"), ("map", 59, "j n10 (59)"), ("map", 118, "map 118"),
                    ("uni", 30, "uni 30"), ("uni", 59, "uni 59"), ("uni", 118, "uni 118"),
                    ("uni", 77, "uni 77 (n5 at top)"), ("uni", 153, "uni 153 (n10 at top)"), ("uni", 100, "uni 100 (deck)")],
             "ii:": [("map", ERR[("ii:", find("ii:", f"map n{n}"))][1], find("ii:", f"map n{n}")) for n in (5, 10, 20)]
                    + [("uni", ERR[("ii:", find("ii:", f"map n{n}"))][1], "uni " + str(ERR[("ii:", find("ii:", f"map n{n}"))][1])) for n in (5, 10, 20)]}
    print("\nG6 thresholds: grid  N  |fd2 err|  model C N^-p  threshold=max(|fd2|, model, floor)")
    for ck, lst in gates.items():
        for fk, N, nm in lst:
            C, p = model[(ck, fk)]
            e = abs(ERR[(ck, nm)][0]) if (ck, nm) in ERR else float("nan")
            m = C * N ** -p
            print(f"  {ck:3s} {nm:22s} N={N:4d}  |fd2|={e:.3e}  model={m:.3e}  threshold={max(e, m, F):.2e}")
    for ck, names in (("i:", ["j n5 (30)", "j n10 (59)", "map 118", "map 236", "map 472"]),
                      ("ii:", [find("ii:", f"map n{n}") for n in (5, 10, 20, 40)])):
        es = [ERR[(ck, n)] for n in names]
        ords = [math.log(abs(es[i][0]) / abs(es[i + 1][0])) / math.log(es[i + 1][1] / es[i][1]) for i in range(len(es) - 1)]
        print(f"  fd2 observed orders on the {ck} contract ladder: " + ", ".join(f"{o:.3f}" for o in ords))

    for col in (col_i, col_ii):
        key = col.name.split(':')[0] + ':'
        r = leading(*assemble_cheb(col, KX, 128), want_vec=True)
        zw, wv, zp, pv = r["zw"], r["w"], r["zp"], r["p"]
        if wv[np.argmax(np.abs(wv))] < 0: wv = -wv; pv = -pv
        _, p0, _ = col.base(zp)
        q = pv / p0; q = q / q[np.argmax(np.abs(q))]
        zwf = np.linspace(zw.min(), zw.max(), 20001)
        print(f"\neigenfunction {key} (cheb N=128, sigma={r['s']:.12e}): max|w| at z={zw[np.argmax(np.abs(wv))]/1e3:.2f} km; "
              f"z_km  w/max|w|  p'/max|p'|  (p'/p0)/max")
        for zl in np.linspace(0, L, 11):
            wl = 0.0 if zl in (0.0, L) else np.interp(zl, zw[::-1], wv[::-1]) if zw[0] > zw[-1] else np.interp(zl, zw, wv)
            print(f"  {zl/1e3:6.1f}  {wl:+.6f}  {np.interp(zl, zp, pv):+.6f}  {np.interp(zl, zp, q):+.6f}")


if __name__ == "__main__":
    main()
