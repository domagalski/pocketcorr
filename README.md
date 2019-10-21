PocketCorr 
===========================================================

This is a KATCP-based pocket correlator for single ROACH boards.

Documentation
-------------

Documentation for ``pocketcorr`` can be found here:
http://galadriel.astro.utoronto.ca/~domagalski/pocketcorr/

Installation
------------

All you need to do is run `python setup.py install` and the software will be
installed. The name of the script that recieves data from the ROACH is called
`pocketcorr_rx.py`. So far, this will only work on a ROACH, as the Simulink
model for the ROACH2 hasn't been written yet. The .bof file to be run on the
ROACH is provided in the fpga directory of the rpoco8 git repo. It must be
placed in the `/boffiles` directory on the ROACH so that KATCP knows that it
exists.

Dependencies
---------------------------

This software requires the modules [aipy](https://github.com/aaronparsons/aipy),
[corr](https://github.com/ska-sa/corr),
[SNAPsynth](https://github.com/domagalski/snap-synth),
and whatever those modules depend on.
The default calibration files can be found in the
[capo](https://github.com/dannyjacobs/capo) repo, and the path to where the
calibration files are located must be in your PYTHONPATH.

Credits
-------------------------------------------

This software is heavily based upon the
[rpoco8](https://github.com/zakiali/rpoco8) software, and uses the same Simulink
design from the rpoco8 repo.
