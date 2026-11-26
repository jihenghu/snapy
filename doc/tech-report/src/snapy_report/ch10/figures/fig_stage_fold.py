"""The monitor's stage fold for an amount (RegisterMonitor::fold_ at the code pin): each stage's booked rate
a^(s) waits for w2^(s) dt, each stage's post p^(s) counts at once, and both are scaled by the later stages'
w1. Three stages of the SSP rk3 weights, as an illustration of the coefficients; it reads no data.
"""
from snapy_report import figstyle as fs

# SSP rk3 (Shu-Osher): U <- w0 U^n + w1 U + w2 dt L(U); (w1, w2) per stage
W = [(0.0, 1.0), (0.25, 0.25), (2.0 / 3.0, 2.0 / 3.0)]


def make_fig():
    fig, ax = fs.new_figure(fs.DOUBLE, 2.3)
    ax.set_axis_off()
    n = len(W)
    c = [1.0] * n
    for s in range(n - 2, -1, -1):
        c[s] = c[s + 1] * W[s + 1][0]
    ax.text(0.0, 3.6, "stage $s$", fontsize=fs.SMALL_PT, weight="bold")
    ax.text(1.2, 3.6, r"$c^{(s)}=\prod_{s'>s} w_1^{(s')}$", fontsize=fs.SMALL_PT, weight="bold")
    ax.text(3.0, 3.6, r"rate weight $c^{(s)} w_2^{(s)}\Delta t$", fontsize=fs.SMALL_PT, weight="bold")
    ax.text(5.0, 3.6, r"post weight $c^{(s)}$", fontsize=fs.SMALL_PT, weight="bold")
    for s, (w1, w2) in enumerate(W):
        y = 2.8 - s
        ax.text(0.0, y, f"{s}", fontsize=fs.SMALL_PT, va="center")
        ax.text(1.2, y, f"{c[s]:.4g}", fontsize=fs.SMALL_PT, va="center", color=fs.BLUE)
        ax.text(3.0, y, f"{c[s] * w2:.4g}" + r" $\Delta t$", fontsize=fs.SMALL_PT, va="center", color=fs.ORANGE)
        ax.text(5.0, y, f"{c[s]:.4g}", fontsize=fs.SMALL_PT, va="center", color=fs.GREEN)
    ax.text(0.0, 0.25, r"rate weights sum to $\Delta t$ (here $1/6+1/6+2/3=1$): a constant rate books its step amount",
            fontsize=fs.SMALL_PT, color=fs.GREY)
    ax.set_xlim(-0.05, 6.3)
    ax.set_ylim(0.0, 3.9)
    return fig
