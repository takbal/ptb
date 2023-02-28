#!/usr/bin/env python3

"""
Running this module starts a .html figure service, that watches a
directory and show all .html appearing there, then deletes the file.

Use it to view figures locally that are generated on a remote machine, like:

1. set up continuous syncing of the shared directory (default is /tmp/figures),
for example by unison, using the -repeat=watch flag,

2. run this service on the local machine,

3. from a client that runs on a remote machine, but wants to show
plotly figures on the local one, do:

    from ptb.plots import disp

    plot = ... # generate figure on the remote machine

    disp(plot) # figure appears on the local machine

This also works if the local and the remote are the same machine,
and no syncing is done (so code using 'disp' works in all case).

@author:  Balint Takacs
@contact: takbal@gmail.com
"""

import os
import sys

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from posixpath import join
from pathlib import Path
from time import sleep
from multiprocessing import Process

from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QApplication

def show_html(fname):

    # expected fname: "id!xsize!ysize!title.html"
    # here xsize and ysize can be "max"

    app = QApplication(sys.argv)
    web = QWebEngineView()
    web.load(QUrl.fromLocalFile(str(fname)))

    _, xsize, ysize, title = fname.stem.split("!")
    if xsize == "max":
        xsize = web.maximumWidth()
    else:
        xsize = int(xsize)
    if ysize == "max":
        ysize = web.maximumHeight()
    else:
        ysize = int(ysize)

    web.resize(xsize, ysize)
    web.setWindowTitle(title)
    web.show()
    retcode = app.exec_()
    os.remove(fname)
    sys.exit(retcode)



def run_service(args):

    os.makedirs(args.dir, exist_ok=True)

    shown = set()

    while(True):
        files = list( Path(args.dir).glob("*.html") )

        if not(files):
            shown.clear()

        for f in files:
            if f not in shown:
                shown.add(f)
                p = Process(target=show_html, args=(f,))
                p.start()

        sleep(1)


if __name__ == '__main__':

    parser = ArgumentParser( description=__import__('__main__').__doc__.split("\n")[1],
        formatter_class=RawDescriptionHelpFormatter)
    
    parser.add_argument(
        "-d",
        "--dir",
        type=str,
        default="/tmp/figures",
        required=False,
        help="the directory to watch",
    )

    run_service(parser.parse_args())
