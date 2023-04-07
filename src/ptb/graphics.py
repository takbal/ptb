"""
useful tools that are related to plotting / graphics 

@author:  Balint Takacs
@contact: takbal@gmail.com
"""

import matplotlib.pyplot as plt

# import mpld3

from xarray import DataArray


def sh():
    # show plot when in PyDev debug console
    plt.show(block=True)


def shmat(data, irange=None, jrange=None):
    # show matrix or DataArray with jet colormap
    if isinstance(data, DataArray):
        data = data.to_array()

    if irange is None:
        irange = slice(0, data.shape[0])

    if jrange is None:
        jrange = slice(0, data.shape[1])

    plt.imshow(data[irange, jrange], cmap="jet")
    plt.colorbar()
