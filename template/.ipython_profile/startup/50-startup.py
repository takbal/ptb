import sys
import os
from pathlib import Path
from argparse import Namespace as args
from IPython import get_ipython

get_ipython().run_line_magic("load_ext", "autoreload")
get_ipython().run_line_magic("autoreload", "2")
