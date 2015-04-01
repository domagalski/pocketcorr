#!/usr/bin/env python2.7

################################################################################
## This script is for getting the mean cross correlation out of poco data.
## Copyright (C) 2014  Rachel Domagalski: idomagalski@berkeley.edu
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import os
import sys
import aipy
import argparse
import numpy as np
import matplotlib.pyplot as plt


def get_index(model, index):
    antennas = int(model[5:]) # Turn this into a number

    try:
        ant_num = int(index)
    except ValueError:
        if len(index) == 1:
            ant_num = ord(index) - ord('a')
        elif len(index) == 2: # ROACH2 antenna names
            if antennas != 16:
                raise RuntimeError('This is not implimented yet.')

            # Check if the input is valid
            letter, number = index[0], int(index[1]) - 1
            if number > 1 or ord(letter) < ord('a') or ord(letter) > 'h':
                raise ValueError('Invalid antenna number')

            letnum = ord(letter) - ord('a')
            ant_num = letnum * 2 + number
        else:
            raise ValueError('Invalid antenna number.')

    # Check that the index is valid
    if ant_num < antennas:
        return ant_num
    else:
        raise ValueError('Antenna number out of range.')

def get_model(infiles):
    """
    This function gets the ROACH model.
    """
    models = list(set([aipy.miriad.UV(f)['operator'][:-1] for f in infiles]))
    if len(models) > 1:
        raise ValueError('Input UV files are from different ROACH models.')

    model = models[0]
    if model in ['rpoco8', 'rpoco16', 'rpoco32']:
        return model
    else:
        return 'rpoco8'

def print_progress(step,
                   total,
                   prog_str='Percent complete:',
                   quiet=False,
                   prog_id=''):
    """
    Print the progress of some iteration through data. The step is the
    current i for i in range(total). This function also displays
    progress quietly by writing it to a file.
    """
    progress = round(100 * float(step+1) / total, 2)
    progress = '\r' + prog_str + ' ' + str(progress) + '%\t\t'
    if quiet:
        if step + 1 == total:
            os.system('rm -f progress' + prog_id)
        else:
            with open('progress' + prog_id, 'w') as f:
                f.write(progress[1:-2] + '\n')
    else:
        print progress,
        if step == total - 1:
            print
        else:
            sys.stdout.flush()

if __name__ == '__main__':
    # Get options fromt the command line
    parser = argparse.ArgumentParser()
    parser.add_argument('infiles', nargs='+', help='Input uv files.')
    parser.add_argument('-i',
                        dest='ant_i',
                        required=True,
                        metavar='num',
                        help='Antenna i to use.')
    parser.add_argument('-j',
                        dest='ant_j',
                        required=True,
                        metavar='num',
                        help='Antenna j to use.')
    parser.add_argument('-l', '--log',
                        action='store_true',
                        dest='log',
                        help='Plot on a log scale.')
    parser.add_argument('-p', '--plot-all',
                        action='store_true',
                        help='Plot real/imag + abs of correlation.')
    args = parser.parse_args()

    # Get the antenna numbers
    model = get_model(args.infiles)
    ant_i, ant_j = get_index(model, args.ant_i), get_index(model, args.ant_j)
    ant_i, ant_j = min(ant_i, ant_j), max(ant_i, ant_j)

    # Initialize arrays to store the spectra
    spectra_r = []
    spectra_i = []
    last_nchan = -1
    nfiles = len(args.infiles)

    # Read spectra from the UV files into numpy arrays
    for num, infile in enumerate(map(os.path.abspath, args.infiles)):
        uv = aipy.miriad.UV(infile)
        uv.select('antennae', ant_i, ant_j)
        nchan = uv['nchan']
        if last_nchan > 0  and nchan != last_nchan:
            raise ValueError('Number of channels do not match across inputs.')
        last_nchan = nchan

        # Get all of the spectra
        for i, (preamble, data) in enumerate(uv.all()):
            if i > 1:
                spectra_r.append(np.real(data.take(range(nchan))))
                spectra_i.append(np.imag(data.take(range(nchan))))

        if num < nfiles - 1:
            del uv

        # Display a cute progress meter.
        if nfiles > 1:
            print_progress(num, nfiles)

    # Get the frequency bins of the data
    frequency = 1e3 * aipy.cal.get_freqs(uv['sdf'], uv['sfreq'], nchan)

    # Compute the means
    mean_spec_r = np.mean(spectra_r, axis=0)
    mean_spec_i = np.mean(spectra_i, axis=0)
    mean_spec_a = np.sqrt(mean_spec_r**2 + mean_spec_i**2)

    # Plot the spectrum
    figure_size = (15,8)
    title = 'Mean correlation of antennas %d  and %d' % (ant_i, ant_j)
    if args.plot_all:
        f, axes = plt.subplots(3, 1, sharex=True, figsize=figure_size)
        for mean_spec, title, ax, in zip([mean_spec_r, mean_spec_i, mean_spec_a],
                                         ['real', 'imag', 'abs'], axes):
            ax.plot(frequency, mean_spec, 'b')
            if args.log:
                ax.set_yscale('log')
            ax.set_ylabel(title)
        f.subplots_adjust(hspace=0)
        axes[-1].set_xlabel('Frequency (MHz)')
        axes[0].set_title(title)
    else:
        plt.figure(figsize=figure_size)
        plt.plot(frequency, mean_spec_a)
        plt.xlabel('Frequency (MHz)')
        plt.title(title)
    plt.tight_layout()
    plt.show()
