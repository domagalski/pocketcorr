#!/usr/bin/env python2

################################################################################
## This script is for simple ADC caputer to test the a pocket correlator.
## Copyright (C) 2014  Rachel Simone Domagalski: domagalski@berkeley.edu
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
import pocketcorr as pc
from numpy import fft

#BRAM_SIZE = 4 << 11
BRAM_SIZE = 4 << 10
BRAM_WIDTH = 32
NBITS = 8

class ADC(pc.POCO):
    def adc_read(self, start_pol, demux=1, capture='adc'):
        """
        Read the time domain signals out of a BRAM.
        """
        #XXX need to do demux2 eq blocks
        # Read the register containing the ADC captures.
        if demux == 2 and capture == 'pfb':
            names = ['pfb_real', 'pfb_imag']
            # XXX data type should be <i4 after recompile
            real = np.fromstring(self.read(names[0], BRAM_SIZE), '>i4')
            imag = np.fromstring(self.read(names[1], BRAM_SIZE), '>i4')
            pfb_read = np.zeros(BRAM_SIZE / 4, dtype=np.complex64)
            pfb_read.real = real# map(twos_comp, real)
            pfb_read.imag = imag#map(twos_comp, imag)
            return pfb_read
        else:
            read_size = BRAM_SIZE
            nbits = demux*NBITS
            npols = BRAM_WIDTH/nbits
            first = str(start_pol)
            last = str(start_pol + npols - 1)
            adc = capture + '_'*int(demux>1)

            # I feel one day I'm going to look back on this and shake my head.
            if self.poco == 'spoco12':
                if adc == 'pfb':
                    print 'ERROR: This is messed up on the FPGA.'
                    sys.exit(1)
                elif adc == 'fft':
                    last = str(start_pol + 6)
                    read_size *= 2
                    npols /= 2
                elif adc == 'eq':
                    last = str(start_pol + 1)
                    read_size *= 2
                adc += '_cap_'

                # There is a sync pulse somewhere in the data
                if adc[:2] == 'eq' or adc[:3] == 'fft':
                    sync = self.read(adc + 'sync', read_size).find(chr(1)) / 4
            concat = self.read(adc + '_'.join([first, last]), read_size)

            # Get the formatting for the data.
            if adc[:3] != 'fft':
                shape = (read_size/(npols*demux), npols*demux)
                fmt = '>i1'
            else:
                shape = (read_size/(npols*demux*2), npols*demux)
                fmt = '>i2'

            # Parse the data into usable values.
            adc_read = np.fromstring(concat, fmt).reshape(*shape)
            if adc[:2] == 'eq' or adc[:3] == 'fft':
                adc_read = adc_read[sync:sync+adc_read.shape[0]/2]
            adc_read = list(adc_read.transpose()[::-1])
            if adc[:3] == 'fft':
                adc_read = adc_read[0] + 1j*adc_read[1]
                split = len(adc_read)/2
                adc_read = [adc_read[:split], adc_read[split:]]

            if demux == 2:
                adc_read = [np.r_[adc_read[2*i],adc_read[2*i+1]]
                        for i in range(len(adc_read)/2)]
                for i in range(len(adc_read)):
                    reordered = np.copy(adc_read[i]).reshape(2, shape[0])
                    reordered = reordered.transpose().flatten()
                    adc_read[i] = np.copy(reordered)

            # Return the data as a dictionary.
            if capture == 'adc_cap':
                capture = 'adc'
            names = [capture + str(i) for i in range(start_pol, start_pol+npols)]
            if adc[:3] == 'fft':
                names = [capture + str(i) for i in [start_pol, start_pol+6]]
            return zip(names, adc_read)

def twos_comp(num32, nbits=18):
    """
    Perform the two-s compiment of some n-bit number.
    """
    bit_sel = 2**nbits - 1
    neg_bit = 1 << nbits - 1
    num32 = num32 & bit_sel
    if num32 & neg_bit:
        return -(((1 << 32) - num32) & bit_sel)
    else:
        return num32

if __name__ == '__main__':
    # Grab options from the command line
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--ip-roach', dest='roach', required=True,
                        help='Hostname/ip address of the ROACH.')
    parser.add_argument('-N', '--npol',
                        default=8,
                        type=int,
                        help='Number of antennas in the rpoco design.')
    parser.add_argument('-c', '--capture',
                        help='Block to capture from (SNAP only)')
    parser.add_argument('-d', '--demux', default=1, type=int,
                        help='Demux mode of the ADC.')
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

    spoco12 = False
    modelist = pc.mode_int2list(poco.read_int('ping'))
    if modelist[0] == 'snap' and modelist[3] == 12:
        spoco12 = True
        poco.poco = 'spoco12'

    if args.demux == 1 and args.capture is None:
        if spoco12:
            cap = 'adc'
        else:
            cap = 'new_raw'
    else:
        cap = args.capture

    if spoco12: # See the else for description of the sequence
        poco.write_int(cap + '_cap_raw_trig', 1)
        poco.write_int(cap + '_cap_raw', 1)
        poco.write_int(cap + '_cap_raw', 0)
        poco.write_int(cap + '_cap_raw_trig', 1)
    else:
        # Enable the ADC capture
        poco.write_int(cap + '_capture_trig', 1)

        # capture the ADC.
        poco.write_int(cap + '_capture', 1)
        poco.write_int(cap + '_capture', 0)

        # Turn off ADC capture.
        poco.write_int(cap + '_capture_trig', 0)

    # Collect data and store it as a dictionary
    adc_capture = []
    nbits = args.demux * NBITS
    if cap == 'pfb' and not spoco12:
        pfb_capture = poco.adc_read(0, args.demux, cap)
    else:
        npol = args.npol
        step_size = BRAM_SIZE/nbits
        if cap == 'eq' or cap == 'fft':
            npol /= 2
            step_size = 1
        for i in range(0, npol, step_size):
            adc_capture += poco.adc_read(i, args.demux, cap)
        adc_capture = dict(adc_capture)

    # Now we either save or plot the data.
    if args.outfile is not None:
        np.savez(args.outfile, **adc_capture)

    # Set this for plotting
    #if args.demux == 1 and args.capture is None:
    #    cap = 'adc'

    if args.antennas is not None:
        import matplotlib.pyplot as plt
        if cap == 'pfb' and not spoco12:
            plt.plot(np.abs(pfb_capture)**2)
        else:
            time_axis = np.arange(BRAM_SIZE*nbits/BRAM_WIDTH) * 1e6 / args.samp_rate
            freq_axis = fft.fftfreq(len(time_axis), 1e6 / args.samp_rate)
            freq_axis = freq_axis[:len(freq_axis)/2] # ADC data is real
            for ant in args.antennas:
                plt.figure()
                name = cap + ant
                sample = adc_capture[name]
                if args.fft or cap == 'fft':
                    if args.fft:
                        pspec = np.abs(fft.fft(sample)[:len(sample)/2])**2
                        pspec = 10*np.log10(pspec / np.max(pspec))
                        plt.plot(freq_axis, pspec)
                        plt.xlabel('Frequency (MHz)')
                        plt.ylabel('Power (dB)')
                    else:
                        pspec = np.abs(sample)**2
                        plt.plot(pspec)
                        plt.xlabel('Frequency (chan)')
                        plt.ylabel('Power')
                    plt.title(name)
                    #plt.axis([0, freq_axis[-1], np.min(pspec), 0])
                else:
                    plt.plot(time_axis, sample)
                    plt.xlabel('Time ($\mu s$)')
                    plt.ylabel('Amplitude (ADU)')
                    plt.title(name)
                    plt.axis([0, time_axis[-1], np.min(sample)-2, np.max(sample)+2])

        plt.show()
