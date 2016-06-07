#!/usr/bin/env python2

################################################################################
## This script is for recieving data from a pocket correlator.
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

import time
import argparse
import numpy as np
import pocketcorr as pc

if __name__ == '__main__':
    # Parse command-line options
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--ip', dest='ip', required=True,
                        help='IP address of Pocket Correlator')
    parser.add_argument('-r', '--rpoco',
                        required=True,
                        help=' '.join(['Pocket correlator model.']))
    parser.add_argument('-n', '--num-reads', type=int, default=10,
                        help='Number of readouts.')
    parser.add_argument('-s', '--single-pair', action='store_true',
                        help='Get the readout time for a single baseline.')

    args = parser.parse_args()

    ip     = args.ip
    rpoco  = args.rpoco
    nreads = args.num_reads
    blread = args.single_pair
    # Most of these don't really matter since this test is about timing, not
    # about what the data is.
    calfile       = 'psa898_v003'
    nyquist       = 1
    acc_len       = 1 << 31
    eq_coeff      = 16
    fft_shift     = 0x3ff
    samp_rate     = 200e6
    insel         = 0 # Maybe do digital zeros? doesn't realy matter.
    force_restart = True

    # Start up the ROACH board
    if pc.is_demux2(rpoco):
        roach = pc.POCOdemux2(ip)
    else:
        roach = pc.POCO(ip)
    roach.check_connected()
    roach.get_model(rpoco)
    roach.set_attributes(calfile, samp_rate, nyquist)
    roach.start_bof(acc_len, eq_coeff, fft_shift, insel, force_restart)
    print


    read_time = []
    single_bram = []
    for i in range(nreads):
        # Read all antennas
        tstart = time.time()
        if pc.is_demux2(rpoco):
            for pair in roach.pairs:
                if blread and pair not in [(0,0), (0,1), (1,1)]:
                    continue
                tstart_bram = time.time()
                roach.read_corr(pair)
                tend_bram = time.time()

                # Double BRAM readout time for cross-corrs.
                if pair[0] - pair[1]:
                    single_bram.append((tend_bram - tstart_bram)/2)
                else:
                    single_bram.append(tend_bram - tstart_bram)
        else:
            for fst, snd in zip(roach.fst, roach.snd):
                if blread and fst not in [(0,0), (0,1), (1,1)]:
                    continue
                tstart_bram = time.time()
                roach.read_corr(fst)
                tend_bram = time.time()

                # Double BRAM readout time for cross-corrs.
                if fst[0] - fst[1]:
                    single_bram.append((tend_bram - tstart_bram)/2)
                else:
                    single_bram.append(tend_bram - tstart_bram)

        tend = time.time()
        read_time.append(tend - tstart)

        # Print results.
        print 'Readout', str(i+1)+'/'+str(nreads) + ':', read_time[-1], 's'

    print
    print 'Total readout time:', np.mean(read_time)
    print 'BRAM readout time:', np.mean(single_bram)
    roach.progdev('')
