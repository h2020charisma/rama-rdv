#!/usr/bin/env python3


"""
# Ramanchada2

## Purpose
`ramanchada2` software package is meant to fill the gap between the theoretical
Raman analysis and the experimental Raman spectroscopy by providing means to
compare data of different origin. The software is in early development stage
but still able to solve practical problems.

## Features


### Read simulated data
Process simulated data by [VASP] and [CRYSTAL] and provide same interface.
CRYSTAL data contain intensities for multiple orientations -- laser beam
incidents perpendicularly or parallelly to the observation and information
for mono-crystals. VASP data provide data only for poly-crystals but in
different format. So the perpendicular and parallel intensities are calculated
by an implemented [algorithm](https://doi.org/10.1103/PhysRevB.54.7830).

### Models
[LMFIT] theoretical models can be build by spectral information obtained by
simulations or by provided by the user. These models can be fit to experimental
data, providing calibration information. At poor initial calibration the minimisation
procedure naturally fails. An iterative procedure aiming to solve this problem
was adopted in the code. On the first iteration the experimental spectrum lines
are artificially broadened. This makes it possible for the minimisation procedure
to find a parameters that are close enough to be used as an initial guess for
the second iteration. In few iterations the algorithm is able to fit to the original
experimental data. This idea is implemented and is at proof-of-concept level.

### Generate spectra
Spectra can be generated by the theoretical models. Random Poissonian noise and
artificial random-generated baseline can be added to the generated spectra, making
them convenient tools to test new methods for analysis.

### Spectrum manipulation
A number of filters can be applied to spectra (experimental and generated).
Scaling on both x and y axes is possible. Scaling could be linear or arbitrary
user defined function. A convolution is possible with set of predefined functions
as well as user defined model.

## Concept
The code is object oriented, written in python. Main elements are Spectrum and
theoretical models. Theoretical models are based on [LMFIT] library, while
Spectrum is a custom made class. Spectrum object contains data for x and y axes
and metadata coming from experimental files or other sources. It is planned
to add information about the uncertainties in x and y. All filters and manipulation
procedures are available as class methods. Measures are taken to preserve spectrum
instances immutable, so filters are generating new spectra, preserving the original
unchanged. Additionally, Spectrum has information about its history -- the sequence
of applied filters.

## File formats
### `.cha` vs [USID]/[NSID]
`ramanchada`(1) software package introduced `.cha` file format, which is a [HDF5]
with a specific architecture. Two spectroscopy specific file formats -- [USID] and
[NSID] -- were considered as successors of `.cha`. [USID] and [NSID] are provided
by [pycroscopy] package as an extension of [HDF5]. Several jupyter notebooks were
created in order to assess the advantages and disadvantages of such a change. These
file formats are designed to handle multidimensional spectral data, keeping track
of the modifications. These file formats does not provide big advantage in our case,
so currently `ramanchada2` supports `.cha` file format and does not support [USID]
or [NSID].

### Cache
The concept to keep previous variants of data is employed in `ramanchada2`. If
configured so, the software saves the data for all Spectrum instances to a
tree-organized `.cha` file. When a particular chain of operations is requested
by the user, the software checks if the final result is present in the cache file,
if so it is provided, otherwise the software checks for its parent. When a parent
or some of the grand parents are present, they are taken as a starting point and
the needed steps are applied to provide the final result. The current implementation
uses [h5py] library to access local hdf files. It is foreseen to have implementation
with [h5pyd] that support network operations.


[VASP]: https://www.vasp.at/
[CRYSTAL]: https://www.crystal.unito.it/index.php
[LMFIT]: https://lmfit.github.io/lmfit-py/index.html
[HDF5]: https://hdfgroup.org/
[h5py]: https://h5py.org/
[h5pyd]: https://github.com/HDFGroup/h5pyd
[pycroscopy]: https://pycroscopy.github.io/pycroscopy/
[USID]: https://pycroscopy.github.io/USID
[NSID]: https://pycroscopy.github.io/pyNSID
"""

from __future__ import annotations

from . import spectrum
from . import theoretical_lines
__all__ = ['spectrum', 'theoretical_lines']
__version__ = '0.0.4'


import logging


class CustomFormatter(logging.Formatter):
    green = "\x1b[32m"
    blue = "\x1b[34m"
    yellow = "\x1b[33m"
    red = "\x1b[31m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    fmt = "%(asctime)s %(name)s %(levelname)s - %(message)s"
    fmt = "%(levelname)s - %(filename)s:%(lineno)d %(funcName)s() - %(message)s"

    FORMATS = {
        logging.DEBUG: green + fmt + reset,
        logging.INFO: blue + fmt + reset,
        logging.WARNING: yellow + fmt + reset,
        logging.ERROR: red + fmt + reset,
        logging.CRITICAL: bold_red + fmt + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def basicConfig(level=logging.INFO):
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(CustomFormatter())
    logging.basicConfig(handlers=[ch], force=True)


stream = logging.StreamHandler()
stream.setFormatter(CustomFormatter())
logging.basicConfig(handlers=[stream], force=True)
logger = logging.getLogger(__name__)
