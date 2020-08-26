"""
useful tools that are related to math 

@author:  Balint Takacs
@contact: takbal@gmail.com
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
    
def set_replace_with_npnans(s: set):
    """fix float("nan") vs np.nan hell"""
    for x in s:
        if isinstance(x, float) and np.isnan(x):
            s.remove(x)
            s.add(np.nan)
            