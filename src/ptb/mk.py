#!/usr/bin/env python3

"""
Short description comes here

Long description comes here

@author:  Balint Takacs
@contact: takbal@gmail.com
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from textwrap import dedent
from pathlib import Path
from inspect import getsourcefile

def main():

    # put usage here:
    usage = """
            command-line usage details comes here
            """

    project_location = Path(getsourcefile(lambda:0)).resolve().parent.parent.parent
    
    if (project_location / 'version').exists():
        with open(project_location / 'version', "r") as f:
            version = f.read()
    else:
        version = 'UNKNOWN'
    parser = ArgumentParser( description = __import__('__main__').__doc__.split("\n")[1],
        formatter_class = RawDescriptionHelpFormatter,
        epilog = dedent(usage) )    

    parser.add_argument('-V', '--version', action='version', version=version)
    # add further arguments here:
    
    args = parser.parse_args()
    
    ######################################

    # put your code here:
        
if __name__ == '__main__':
    main()
