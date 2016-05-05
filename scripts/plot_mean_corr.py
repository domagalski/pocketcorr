#!/usr/bin/env python2.7

################################################################################
## This script is for getting the mean cross correlation out of poco data.
## Copyright (C) 2014  Rachel Simone Domagalski: domagalski@berkeley.edu
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
import pocketcorr as pc
import matplotlib.pyplot as plt

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
    parser.add_argument('-q', '--quiet',
                        action='store_true',
                        help='Suppress messages to stdout.')
    parser.add_argument('-s', '--scale',
                        action='store_true',
                        help=' '.join(['Scale the output by number of spectra',
                                       'per integration.']))
    args = parser.parse_args()

    # Get the antenna numbers
    model = pc.get_model_uv(args.infiles)
    ant_i = pc.get_ant_index(model, args.ant_i)
    ant_j = pc.get_ant_index(model, args.ant_j)
    ant_i, ant_j = min(ant_i, ant_j), max(ant_i, ant_j)

    # Initialize arrays to store the spectra
    spectra_r, spectra_i = pc.spec_list(args.infiles, ant_i, ant_j, not args.quiet)

    # Get the frequency bins of the data
    uv = aipy.miriad.UV(args.infiles[0])
    frequency = 1e3 * aipy.cal.get_freqs(uv['sdf'], uv['sfreq'], uv['nchan'])

    # Compute the means
    mean_spec_r = np.mean(spectra_r, axis=0)
    mean_spec_i = np.mean(spectra_i, axis=0)
    if args.scale:
        fft_size = 2*uv['nchan']
        if 'acclen' in uv.vars():
            scale_factor = uv['acclen'] / fft_size
        else:
            # Estimate the clocks per accumulation using the integration time.
            sfreq = uv['sfreq'] and uv['sfreq'] or 0.2 # XXX default value
            acclen = int(sfreq * 1e9 * uv['inttime'])
            upper = lower = acclen
            delta = 1
            while acclen % fft_size:
                upper = acclen + delta
                lower = acclen - delta
                if not upper % fft_size:
                    acclen = upper
                elif not lower % fft_size:
                    acclen = lower
                delta += 1
            scale_factor = acclen / fft_size
        mean_spec_r /= scale_factor
        mean_spec_i /= scale_factor
    mean_spec_a = np.sqrt(mean_spec_r**2 + mean_spec_i**2)

    # The reference UV file is no longer needed.
    del uv

    # Plot the spectrum
    figure_size = (15,8)
    title = 'Mean correlation of antennas %s and %s' % (args.ant_i, args.ant_j)
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
