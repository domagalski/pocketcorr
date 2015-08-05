#!/usr/bin/env python2

################################################################################
## This script is for simulating data being read off from a ROACH.
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

import os
import time
import numpy as np
import numpy.random as npr
import pocketcorr as pc

# POCO constants.
NCHAN     = pc.NCHAN
SAMP_RATE = pc.SAMP_RATE

class FakeROACH(pc.POCO):
    """
    Simulated ROACH board for offline testing.
    """
    def cleanup(self):
        if os.path.exists('TMP_FILE'):
            os.system('rm -rf TMP_FILE')

    def poll(self):
        """
        Wait until the accumulation number has updated.
        """
        time.sleep(self.int_time)
        jd = pc.get_jul_date(time.time() - 0.5*self.int_time)
        self.count += 1
        return jd

    def read_corr(self, corr_pair):
        """
        Generate fake data to store in the UV file.
        """
        # Convert the strings to numeric data
        lendat  = NCHAN << 1
        window  = 10 * np.abs(2*np.sin(np.pi * np.arange(lendat) / lendat))
        cx_data = np.zeros(lendat, dtype=np.complex64)
        cx_data.real = npr.randn(lendat) + window
        cx_data.imag = npr.randn(lendat) + window
        cx_data[100:200] += 20.0

        # The data needs to be reshaped to account for the two FFT stages
        return cx_data.reshape((NCHAN, 2)).transpose()

    def start_bof(self):
        """
        Set object variables in the POCO start_bof function.
        """
        self.acc_len   = 1 << 24
        self.eq_coeff  = 16
        self.fft_shift = 0x3ff
        self.insel     = 0
        self.int_time  = self.acc_len / SAMP_RATE
        self.sync_sel  = True
        self.count     = 0

if __name__ == '__main__':
    roach = FakeROACH('')
    roach.get_model('rpoco8')
    roach.set_attributes('psa898_v003', 2)
    roach.start_bof()

    # Read the data into UV files.
    try:
        roach.uv_open()
        roach.retrieve_data()
    except KeyboardInterrupt:
        print
        roach.uv_close()
    finally:
        roach.cleanup()
