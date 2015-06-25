"""
PocketCorr: KATCP-based pocket correlator for ROACH boards.
"""
from distutils.core import setup
import glob

__version__ = '0.6.5'

if __name__ == '__main__':
    setup(name = 'pocketcorr',
        version = __version__,
        description = __doc__,
        long_description = __doc__,
        license = 'GPL',
        author = 'Rachel Domagalski',
        author_email = 'idomagalski@berkeley.edu',
        url = 'https://github.com/domagalski/pocketcorr',
        package_dir = {'':'src'},
        py_modules = ['pocketcorr'],
        scripts = glob.glob('scripts/*'),
    )
