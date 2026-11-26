"""One cycle line, token by token, as print_cycle_line prints it at the code pin (src/diagnostics/budget.cpp):
the volume integral each token sums over interior cells and local blocks, and the reduction to the root
process. The conserved totals are BudgetConsumer::totals; ke, pe and the meters are read from hydro. A
cartoon; it reads no data.
"""
import matplotlib.pyplot as plt

from snapy_report import figstyle as fs

ROWS = [
    ("mass0=", r"$\sum_i \rho_{d,i} V_i$ (BudgetConsumer::totals)", "SUM", fs.SKY),
    ("masst=", r"$\sum_i (\rho_{d,i}+\sum_n \rho_{n,i}) V_i$, with species", "SUM", fs.SKY),
    ("ke=", r"$\sum_i \frac{1}{2}m_j m^j/\rho_i\,V_i$", "SUM", fs.SKY),
    ("ie= / energy=", r"$\sum_i E_i V_i$ (BudgetConsumer::totals)", "SUM", fs.SKY),
    ("pe=", r"$\sum_i \rho_i\phi_i V_i$, with gravity", "SUM", fs.SKY),
    ("limcut=", r"cut over offered $x_1$ flux, run to date", "SUM, ratio", fs.ORANGE),
    ("thetamin=", r"smallest limiter $\theta$, run to date", "MIN", fs.ORANGE),
    ("thetasevere=", "count of severe cuts, run to date", "SUM", fs.ORANGE),
    ("vicclamp=", "largest clamp residual, run to date (implicit)", "MAX", fs.ORANGE),
]


def make_fig():
    fig, ax = fs.new_figure(fs.DOUBLE, 2.9)
    ax.set_axis_off()
    n = len(ROWS)
    for k, (tok, integral, op, col) in enumerate(ROWS):
        y = n - k
        ax.text(0.0, y, tok, fontsize=fs.SMALL_PT, family=fs.MONO, va="center", color=fs.BLACK)
        ax.add_patch(plt.Rectangle((1.55, y - 0.35), 0.12, 0.7, fc=col, ec="none"))
        ax.text(1.8, y, integral, fontsize=fs.SMALL_PT, va="center")
        ax.text(6.3, y, op, fontsize=fs.SMALL_PT, va="center", ha="right", color=fs.GREEN)
    ax.text(0.0, n + 1, "token", fontsize=fs.SMALL_PT, weight="bold")
    ax.text(1.8, n + 1, "what it sums over interior cells and local blocks", fontsize=fs.SMALL_PT, weight="bold")
    ax.text(6.3, n + 1, "reduce to root", fontsize=fs.SMALL_PT, weight="bold", ha="right")
    ax.plot([0, 6.3], [4.5, 4.5], color=fs.GREY, lw=0.6, ls="--")
    ax.text(4.2, 4.55, "run-to-date meters below", fontsize=fs.SMALL_PT, color=fs.GREY, ha="center", va="center",
            bbox=dict(fc="white", ec="none", pad=1))
    ax.set_xlim(-0.05, 6.35)
    ax.set_ylim(0.4, n + 1.4)
    return fig
