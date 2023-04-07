"""
useful tools that are related to text processing 

@author:  Balint Takacs
@contact: takbal@gmail.com
"""

import logging
import sys


def extract_pvals(string, separator="_"):
    """
    Extract parameter values from a string. The keys in the string
    should be in the form like (assuming _ is the separator):

    '..._key1=x_key2=y..(/)..._key3=z_...'

    The strings '_key=' must be unique and present.

    It also returns the start and the length+1 of the string representing the
    numeric value.

    Args:

    Returns:

    Raises:
        AssertionError if wrong parameters are passed
    """
    parts = string.split(separator)
    parts = [p for p in parts if "=" in p]

    params = {}

    for p in parts:
        key, value = p.split("=")
        assert key not in params.keys()

        try:
            params[key] = float(value)
        except:
            params[key] = value

    return params


def getlogger(
    name: str,
    file: str = None,
    use_stdout=True,
    stream_level=logging.INFO,
    file_level=logging.INFO,
) -> logging.Logger:
    # Create a custom logger
    logger = logging.getLogger(name)

    if not logger.hasHandlers():
        logger.propagate = False
        logger.setLevel(min(stream_level, file_level))

        if use_stdout:
            c_handler = logging.StreamHandler(sys.stdout)
        else:
            c_handler = logging.StreamHandler()

        c_handler.setLevel(stream_level)
        c_format = logging.Formatter(
            "%(asctime)s: %(name)s [%(levelname)s]: %(message)s"
        )
        c_handler.setFormatter(c_format)
        logger.addHandler(c_handler)

        if file is not None:
            f_handler = logging.FileHandler(file)
            f_handler.setLevel(file_level)
            f_format = logging.Formatter(
                "%(asctime)s: %(name)s [%(levelname)s]: %(message)s"
            )
            f_handler.setFormatter(f_format)
            logger.addHandler(f_handler)

    return logger
