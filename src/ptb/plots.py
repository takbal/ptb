import os

from pathlib import Path
from uuid import uuid4


def disp(
    fig,
    title="figure",
    show=True,
    saveto=None,
    xsize=None,
    ysize=None,
    server_dir="/tmp/figures",
    include_plotlyjs="cdn",
):
    """
    save or diplay a plotly plot through the figure server

    Parameters
    ----------
        fig: plotly fig
            the figure
        title: str, default = "figure"
            figure title, included in file name
        show: bool, def=True
            if true, show the plot
        saveto : str, optional
            if present, directory to save the plot into
        xsize: int, optional
            if shown, window x size in pixels, default is max
        ysize: int, optional
            if shown, window y size in pixels, default is max
        dir: str, default = /tmp/figures
            the directory of the figserv.py)
        include_plotlyjs: str, optional, def = "cdn"
            specifies this field for saveto (see plotly)
    """

    if show:
        if not xsize:
            xsize = "max"
        else:
            xsize = str(xsize)

        if not ysize:
            ysize = "max"
        else:
            ysize = str(ysize)

        fname = str(uuid4())[0:7] + "!" + xsize + "!" + ysize + "!" + title + ".html"

        os.makedirs(server_dir, exist_ok=True)

        fig.write_html(
            Path(server_dir) / fname, auto_open=False, include_plotlyjs="directory"
        )

    if saveto:
        os.makedirs(saveto, exist_ok=True)
        fig.write_html(
            Path(saveto) / (title + ".html"),
            auto_open=False,
            include_plotlyjs=include_plotlyjs,
        )
