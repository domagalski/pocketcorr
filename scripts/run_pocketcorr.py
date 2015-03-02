#!/usr/bin/env python2

################################################################################
## This script is for recieving data from a pocket correlator.
## Copyright (C) 2014  Rachel Domagalski: idomagalski@berkeley.edu
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
## ## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import os
import sys

if __name__ == '__main__':
    assert len(sys.argv) > 1, 'ERROR: Missing POCO configuration file.'

    # Open the configuration file.
    configfile = sys.argv[1].replace('.py', '')
    configpath = os.path.dirname(os.path.abspath(configfile))
    configfile = os.path.basename(configfile)
    sys.path.insert(0, configpath)
    exec('from ' + configfile + ' import config')
    sys.path = sys.path[1:]

    # Set up the call to pocketcorr_rx.py
    cmd = ['pocketcorr_rx.py']
    for key in config.keys():
        cmd.append('--' + key.replace('_', '-'))
        if config[key] is not None:
            cmd.append(str(config[key]))

    # Run the pocketcorr_rx.py command
    sys.exit(os.system(' '.join(cmd + sys.argv[2:])))
