import sys
import os
from pathlib import Path
from argparse import Namespace as args

from IPython import get_ipython
ipython = get_ipython()
ipython.magic("load_ext autoreload") 
ipython.magic("autoreload 2")
