#!/usr/bin/env python2

################################################################################
## This script is for simple ADC caputer to test the a pocket correlator.
## Copyright (C) 2014  Rachel Domagalski: rsdomagalski@gmail.com
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

import sys
import argparse
import numpy as np
import corr.katcp_wrapper as katcp
from numpy import fft

BRAM_SIZE = 4 << 11
BRAM_WIDTH = 32
NBITS = 8

class ADC(katcp.FpgaClient):
    def adc_read(self, start_pol):
        """
        Read the time domain signals out of a BRAM.
        """
        # Read the register containing the ADC captures.
        npols = BRAM_WIDTH/NBITS
        first = str(start_pol)
        last = str(start_pol + npols - 1)
        concat = self.read('adc' + '_'.join([first, last]), BRAM_SIZE)

        # Parse the data into usable values.
        adc_read = np.fromstring(concat, '>i1').reshape(BRAM_SIZE/npols, npols)
        adc_read = list(adc_read.transpose()[::-1])

        # Return the data as a dictionary.
        names = ['adc' + str(i) for i in range(start_pol, start_pol+npols)]
        return zip(names, adc_read)

if __name__ == '__main__':
    # Grab options from the command line
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--ip-roach', dest='roach', required=True,
                        help='Hostname/ip address of the ROACH.')
    parser.add_argument('-N', '--npol',
                        default=8,
                        type=int,
                        help='Number of antennas in the rpoco design.')
    parser.add_argument('-o', '--output-file',
                        dest='outfile',
                        help='NPZ file to save data to.')
    parser.add_argument('-a', '--antennas', nargs='+',
                        help='Antennas to plot.')
    parser.add_argument('-f', '--fft', action='store_true',
                        help='Run an FFT on the data.')
    parser.add_argument('-S', '--samp-rate', default=200e6, type=float,
                        help='Samping rate of the ADC (for plots).')
    args = parser.parse_args()

    # Make sure that the user specified something to do.
    if args.outfile is None and args.antennas is None:
        print 'ERROR: Nothing to do.'
        sys.exit(1)
    if args.outfile is not None and args.antennas is None and args.fft:
        print 'ERROR: This script only stores raw data.'
        sys.exit(1)


    # Connect to the ROACH.
    poco = ADC(args.roach)
    poco.wait_connected()

    # Enable the ADC capture
    poco.write_int('new_raw_capture_trig', 1)

    # capture the ADC.
    poco.write_int('new_raw_capture', 1)
    poco.write_int('new_raw_capture', 0)

    # Turn off ADC capture.
    poco.write_int('new_raw_capture_trig', 0)

    # Collect data and store it as a dictionary
    adc_capture = []
    for i in range(0, args.npol, BRAM_WIDTH/NBITS):
        adc_capture += poco.adc_read(i)
    adc_capture = dict(adc_capture)

    # Now we either save or plot the data.
    if args.outfile is not None:
        np.savez(args.outfile, **adc_capture)

    if args.antennas is not None:
        import matplotlib.pyplot as plt
        time_axis = np.arange(BRAM_SIZE*NBITS/BRAM_WIDTH) * 1e6 / args.samp_rate
        freq_axis = fft.fftfreq(len(time_axis), 1e6 / args.samp_rate)
        freq_axis = freq_axis[:len(freq_axis)/2] # ADC data is real
        for ant in args.antennas:
            plt.figure()
            name = 'adc' + ant
            sample = adc_capture[name]
            if args.fft:
                pspec = np.abs(fft.fft(sample)[:len(sample)/2])**2
                pspec = 10*np.log10(pspec / np.max(pspec))
                plt.plot(freq_axis, pspec)
                plt.xlabel('Frequency (MHz)')
                plt.ylabel('Power (dB)')
                plt.title(name)
                plt.axis([0, freq_axis[-1], np.min(pspec), 0])
            else:
                plt.plot(time_axis, sample)
                plt.xlabel('Time ($\mu s$)')
                plt.ylabel('Amplitude (ADU)')
                plt.title(name)
                plt.axis([0, time_axis[-1], np.min(sample)-2, np.max(sample)+2])

        plt.show()
