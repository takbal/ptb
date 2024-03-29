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
    """fill nans with interpolated values"""

    mask = np.isnan(x)
    x[mask] = np.interp(np.flatnonzero(mask), np.flatnonzero(~mask), x[~mask])


def set_replace_with_npnans(s: set):
    """fix float("nan") vs np.nan hell"""
    for x in s:
        if isinstance(x, float) and np.isnan(x):
            s.remove(x)
            s.add(np.nan)


def points_distance_to_line(X: np.array, v1: np.array, v2: np.array) -> np.array:
    """
    get the shortest distance of all vectors in X rows to the line defined by v1, v2 points.
    Vectors can be of arbitrary dimensions. If:

     xp := x - v1
     d := v2 - v1

    then the projection vector length is:

     diff_vector_len = | xp - xp dot d/(|d|^2) * d |
    """

    assert (v1 != v2).all(), "v1 and v2 must be different"

    v2v1 = v2 - v1
    v2v1_normed = v2v1 / (v2v1**2).sum()
    Xp = X - v1
    projected = (Xp * v2v1_normed).sum(axis=1)
    return norm(Xp - projected[:, np.newaxis] * v2v1)


def norm(X: np.array, axis=1) -> np.array:
    """get the L2 norm of vectors in X. By default, assume vectors are in rows"""
    return np.sqrt((X**2).sum(axis=axis))
