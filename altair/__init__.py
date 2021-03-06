# flake8: noqa
__version__ = '3.0.0dev2'

from .vegalite import *
from . import examples

def load_ipython_extension(ipython):
    from ._magics import vega, vegalite
    ipython.register_magic_function(vega, 'cell')
    ipython.register_magic_function(vegalite, 'cell')
