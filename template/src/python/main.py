#!/usr/bin/env python3

"""
Short description comes here

Long description comes here
"""

epilog = """
    command-line usage explanation comes here
    """

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from importlib.metadata import version as importlib_version, PackageNotFoundError
from textwrap import dedent
from pathlib import Path
from inspect import getsourcefile

def main(args=None):
    
    # put your code here:
    pass
        
if __name__ == '__main__':

    try:
        version = importlib_version('PACKAGE')
    except PackageNotFoundError:
        version = 'UNKNOWN'

    parser = ArgumentParser( description = __import__('__main__').__doc__.split("\n")[1],
        formatter_class = RawDescriptionHelpFormatter,
        epilog = dedent(epilog) )    

    parser.add_argument('-V', '--version', action='version', version=version)
    # add further arguments here:
    
    main(parser.parse_args())
