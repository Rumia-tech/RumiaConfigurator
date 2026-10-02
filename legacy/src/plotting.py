import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure

def setup_plot_figure(figsize=(6, 4), dpi=100):
    fig = Figure(figsize=figsize, dpi=dpi)
    ax = fig.add_subplot(111)
    ax.grid(True)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Value')
    return fig, ax

def finalize_layout(fig):
    fig.tight_layout()
    return fig
