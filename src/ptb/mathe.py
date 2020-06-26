#!/usr/bin/env python3

"""
useful tools that are related to math 
"""

import numpy as np

def nansumabsnorm(v: np.ndarray) -> np.ndarray:
    """ 
    make sum|v| = 1, ignoring nans
        
    Args:
        v: input vector
        
    Returns:
        normalised array
        
    Raises:
        Nothing
    """    
    return v / np.nansum(abs(v))

def interpolate_nans(x: np.ndarray):
    '''fill nans with interpolated values'''
    
    mask = np.isnan(x)
    x[mask] = np.interp( np.flatnonzero(mask), np.flatnonzero(~mask), x[~mask])