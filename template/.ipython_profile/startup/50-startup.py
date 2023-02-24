import sys
import os
from pathlib import Path
from argparse import Namespace as args

from IPython import get_ipython
ipython = get_ipython() 
if "__IPYTHON__" in globals(): 
    ipython.magic("load_ext autoreload") 
    ipython.magic("autoreload 2")

print('Python %s on %s' % (sys.version, sys.platform))
