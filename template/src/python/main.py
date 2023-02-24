#!/usr/bin/env python3

"""
Short description comes here

Long description comes here
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from importlib.metadata import version as ilib_version, PackageNotFoundError
from textwrap import dedent


def main(args=None):
    # put your code here:
    pass


if __name__ == "__main__":
    # command-line usage explanation comes here:
    epilog = """
    """

    try:
        version = ilib_version("PACKAGE")
    except PackageNotFoundError:
        version = "UNKNOWN"

    parser = ArgumentParser(
        description=__import__("__main__").__doc__.split("\n")[1],
        formatter_class=RawDescriptionHelpFormatter,
        epilog=dedent(epilog),
    )

    parser.add_argument("-V", "--version", action="version", version=version)
    # add further arguments here:

    main(parser.parse_args())
