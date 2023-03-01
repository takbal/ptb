import os

from pathlib import Path
from uuid import uuid4

def disp(fig, title="plotly", saveto=None, xsize=None, ysize=None, dir="/tmp/figures"):
    """
    diplay a plotly plot through the figure server

    Parameters
    ----------
        fig: plotly fig
            the figure to show
        title: str, default = "plotly"
            the window title
        xsize: int, optional
            window x size in pixels, default is max
        ysize: int, optional
            window y size in pixels, default is max
        dir: str, default = /tmp/figures
            the directory of the figserv.py)
        saveto : str, optional
            if present, save a copy with the tile into this directory
    """

    if not xsize:
        xsize = "max"
    else:
        xsize = str(xsize)

    if not ysize:
        ysize = "max"
    else:
        ysize = str(ysize)

    fname = str(uuid4())[0:7] + "!" + xsize + "!" + ysize + "!" + title + ".html"

    os.makedirs(dir, exist_ok=True)

    fig.write_html(Path(dir) / fname, auto_open=False, include_plotlyjs = "directory")

    if saveto:
        os.makedirs(saveto, exist_ok=True)
        fig.write_html(Path(saveto) / (title + ".html"), auto_open=False)
