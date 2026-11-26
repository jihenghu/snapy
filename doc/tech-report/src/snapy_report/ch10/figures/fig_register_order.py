"""The order of the flux register's writes in one stage (FluxRegister and MeshBlockImpl::stage_advance /
stage_combine at the code pin): the producers' posts, the prescribed-face apply before the divergence, the
post-implicit apply, the wall batch's flush and end_stage. A cartoon; it reads no data.
"""
import matplotlib.pyplot as plt

from snapy_report import figstyle as fs

STEPS = [
    ("begin_stage", "the stage's weights $w_1^{(s)}, w_2^{(s)}$; the wall batch starts at its first slot", fs.GREY),
    ("slot / add / scale", r"the sweep and the sources post into $T_d$ (plain row adds, in call order)", fs.ORANGE),
    ("apply_prescribed(d)", "every active direction, after the posts and before the divergence", fs.GREEN),
    ("divergence", r"$\Delta U$ from $T_d$: a wall face carries its prescribed value", fs.SKY),
    ("apply_prescribed(1)", "again after the implicit correction, or when the written mark is set", fs.GREEN),
    ("WallBatch::flush", "each slot's after - before, weighted by $A_f$, booked as one rate per row", fs.ORANGE),
    ("end_stage", r"$S_d \leftarrow w_1^{(s)}S_d + w_2^{(s)}\Delta t\,T_d$; counts flushed", fs.BLUE),
]


def make_fig():
    fig, ax = fs.new_figure(fs.DOUBLE, 2.9)
    ax.set_axis_off()
    n = len(STEPS)
    for k, (name, what, col) in enumerate(STEPS):
        y = n - k
        ax.add_patch(plt.Rectangle((0.0, y - 0.32), 0.12, 0.64, fc=col, ec="none"))
        ax.text(0.25, y, name, fontsize=fs.SMALL_PT, family=fs.MONO, va="center")
        ax.text(2.35, y, what, fontsize=fs.SMALL_PT, va="center")
        if k + 1 < n:
            ax.annotate("", xy=(0.06, y - 0.62), xytext=(0.06, y - 0.36),
                        arrowprops=dict(arrowstyle="->", color=fs.BLACK, lw=0.6))
    ax.set_xlim(-0.05, 6.3)
    ax.set_ylim(0.4, n + 0.6)
    return fig
