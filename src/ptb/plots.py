from pathlib import Path
from uuid import uuid4

def disp(fig, title="plotly", xsize=None, ysize=None, dir="/tmp/figures"):
    """
    diplay a plotly plot through the figure server

    Parameters
    ----------
        fig: plotly fig
            the figure to show
        title: str
            the window title
        xsize: int
            window x size in pixels, default is max
        ysize: int
            window y size in pixels, default is max
        dir: str
            the directory to save into (the one the plots server is running in)
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

    fig.write_html(Path(dir) / fname, auto_open=False)
