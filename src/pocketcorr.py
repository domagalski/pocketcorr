#!/usr/bin/env python2

################################################################################
## This module defines a class for interfacing with a ROACH pocket correlator.
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

import os           as _os
import sys          as _sys
import aipy         as _aipy
import time         as _time
import numpy        as _np
import struct       as _struct
import numpy.random as _npr
from corr import katcp_wrapper as _katcp

POCO_BOF8   = 'rpoco8_100.bof'
POCO2_BOF8  = 'rpoco8_100_r2.bof'
POCO2_BOF16 = 'rpoco16_100.bof'
SNAP_BOF12  = 'spoco12_100.bof'
SNAP_BOF6   = 'spoco6_250.bof'
TIME_FMT    = '%Y-%m-%d-%H:%M'

EQ_ADDR_RANGE = 1 << 6

UV_VAR_TYPES = {
    'source':   'a', 'operator': 'a', 'version':  'a', 'telescop': 'a',
    'antpos':   'd', 'freq':     'd', 'inttime':  'r', 'nants':    'i',
    'nchan':    'i', 'nspect':   'i', 'sfreq':    'd', 'sdf':      'd',
    'ischan':   'i', 'nschan':   'i', 'restfreq': 'd', 'npol':     'i',
    'epoch':    'r', 'veldop':   'r', 'vsource':  'r', 'longitu':  'd',
    'latitud':  'd', 'dec':      'd', 'obsdec':   'd', 'nspect':   'i',
    'ischan':   'i', 'epoch':    'r', 'veldop':   'r', 'vsource':  'r',
    'ra':       'd', 'obsra':    'd', 'lst':      'd', 'pol':      'i',
}

class POCO(_katcp.FpgaClient):
    """
    Class for communicating with a ROACH board running a pocket
    correlator.
    """
    def __init__(self, *args, **kwargs):
        """
        Create the ROACH object and store the model type. The
        arguments for this class constructor are the exact same as
        those of the corr.katcp.FpgaClient class.
        """
        # Open a connection to the ROACH and verify it.
        _katcp.FpgaClient.__init__(self, *args, **kwargs)

        # Default values for ROACH model
        self.poco = None
        self.model = None
        self.antennas = None
        self.nchan = None

        # Display options
        self.verbose = False
        self.filename = _os.path.abspath('poco')
        self.writedir = _os.path.dirname(self.filename)
        self.tmp_file = _os.path.join(self.writedir, 'TMP_FILE')

        # Set some null values for FPGA parameters.
        self.samp_rate = None
        self.acc_len   = None
        self.int_time  = None
        self.eq_coeff  = None
        self.fft_shift = None
        self.insel     = None
        self.sync_sel  = True

        # Data collection parameters
        self.limit = None

        # Placeholder for the optional multiprocessing mode.
        self.mp = False
        self.socket = None
        self.queue = None

    def check_connected(self, timeout=10):
        """
        This function checks that the ROACH is actually connected. If
        the client cannot connect to the ROACH after a certain amount
        of seconds, the client raises an IOError.

        Input:

        - ``timeout``: The amount of seconds to wait before connection \
                failure.
        """
        if not self.wait_connected(timeout):
            raise IOError('Cannot connect to the ROACH.')
        self.log('Opening FPGA client.')

    def check_corr(self, pair, antenna_list=None):
        """
        This function checks if both antennas in a correlation pair are
        in an antenna list. If ``antenna_list`` is None, then it is
        assumed that any antenna pair is automatically valid.

        Input:

        - ``pair``: Pair of antennas for a baseline.
        - ``antenna_list``: List of valid antennas.
        """
        if antenna_list is None:
            return True
        else:
            return pair[0] in antenna_list and pair[1] in antenna_list

    def check_running(self):
        """
        This function checks to see if the bof process for the
        correlator has been initialized on the ROACH. I've put a
        constant in the design that I use to "ping" the correlator,
        and if it can be read, this indicates that the bof process has
        been started. The correlator hasn't been configured if acc_num
        is at zero. It's possible for the correlator to be running, but
        not configured yet.
        """
        try:
            return bool(self.read_int('ping')), self.read_int('acc_num') > 1
        except RuntimeError:
            return False, False

    def cleanup(self):
        if _os.path.exists(self.tmp_file):
            _os.system('rm -rf ' + self.tmp_file)

    def get_ant_ext(self, ant_num):
        """
        This function gets a string representing an antenna of a ROACH
        or ROACH2. For correlator designs with less than 26 inputs, the
        extension is just a letter of the alphabet. For rpoco32, the
        extension is a1,...,a4,b1,...,b4,...,h1,...,h4.

        Input:

        - ``ant_num``: Numeric identifier of ROACH feed.

        Return:

        - ``ext``: String representation of ant_num
        """
        if self.antennas > 26:
            ext = chr(ord('a') + ant_num / 4) + str(ant_num % 4 + 1)
        else:
            ext = chr(ord('a') + ant_num)
        return ext

    def get_ant_ind(self, ant_name):
        """
        This function maps ROACH2/SNAP channel names to antenna indices.

        Input:

        - ``ant_name``: Name of ROACH2 channel.
        """
        snap_board = self.antennas % 6 == 0
        if snap_board:
            demux = 4 * self.antennas / 12
        else:
            demux = 4 * self.antennas / 32 # XXX I'm probably not doing rpoco24

        # Get the number associated with the letter.
        letter = ord(ant_name[0])
        if snap_board and letter >= ord('A') and letter <= ord('C'):
            letter -= ord('A')
        elif snap_board and letter >= ord('a') and letter <= ord('c'):
            letter -= ord('a')
        elif not snap_board and letter >= ord('A') and letter <= ord('H'):
            letter -= ord('A')
        elif not snap_board and letter >= ord('a') and letter <= ord('h'):
            letter -= ord('a')
        else:
            raise ValueError('Invalid antenna name.')

        # Get the number withing the letter channel.
        try:
            number = int(ant_name[1]) - 1
        except IndexError:
            number = 0
        if number not in range(demux):
            raise ValueError('Inactive channel.')

        # return the antenna index.
        return letter * demux + number

    def get_corr_name(self, corr_pair):
        """
        This function generates a string identifying a
        cross-multiplication. For 8 and 16 input designs, the names
        go as aa, ab, ac, ad, etc... For rpoco32, the names go as
        a1_a1, a1_a2, a1_a3, etc...

        Input:

        - ``corr_pair``: Tuple containing antenna numbers.

        Return:

        - String indentifying the cross-correlation
        """
        if self.antennas > 26:
            sep = '_'
        else:
            sep = ''
        return sep.join(map(self.get_ant_ext, sorted(corr_pair)))

    def get_model(self, poco):
        """
        This function determines which ROACH type is being used and
        sets the appropriate class data members (model, antennas,
        boffile). Currently, this will throw an error for ROACH2
        designs, since they haven't been made yet.

        Input:

        - ``rpoco``: Name of the correlator model.
        """
        if self.verbose:
            self.log('Detecting ROACH model.\n')

        # Get the antenna info from the pocketcorr design
        powchan = 10
        self.poco = poco.lower()
        if self.poco == 'rpoco8':
            self.model = 1
            self.antennas = 8
            self.boffile = POCO_BOF8
        elif self.poco == 'rpoco8_r2':
            self.model = 2
            self.antennas = 8
            self.boffile = POCO2_BOF8
        elif self.poco == 'rpoco16':
            self.model = 2
            self.antennas = 16
            self.boffile = POCO2_BOF16
        elif self.poco == 'spoco6':
            self.model = 2 # Pretending the SNAP board is like a ROACH2
            self.antennas = 6
            self.boffile = SNAP_BOF6
        elif self.poco == 'spoco12':
            powchan = 9
            self.model = 2 # Pretending the SNAP board is like a ROACH2
            self.antennas = 12
            self.boffile = SNAP_BOF12
        else:
            raise ValueError('Invalid poco routine.')

        # Set the bram size and number of channels
        self.bram_size = 4 << (powchan + 1 - is_demux2(self.poco))
        self.nchan = 1 << powchan

        # Update the filename to reflect the POCO version.
        self.filename += str(self.antennas)

        # Get the cross-multiplications XXX snap6 friendlines needed.
        if is_demux2(self.poco):
            self.pairs = self.get_xmult()
        else:
            self.fst, self.snd = self.get_xmult()

        # Raise error for not implimented yet
        if self.model == 2 and self.antennas > 16:
            raise RuntimeError('This is not implimented yet.')

        if self.verbose:
            message = 'Detected '
            if 'rpoco' in self.poco:
                message += 'ROACH' + (self.model == 2 and '2' or '')
            else:
                message += 'SNAP'
            message += ' board with %d ADC inputs.\n' % self.antennas
            self.log(message)

    def get_xmult(self):
        """
        This function gets all of the cross-multiplication combos that
        the correlator multiplies. This is useful for testing purposes
        and the class data member ``antennas`` needs to be set to use
        this function. This function returns a table of all of the
        cross-correlation pairs that are on the ROACH. Since the FFT of
        the ROACH comes in two stages, there are two sets of xmult
        tables that are returned as a tuple.
        """
        size = self.antennas
        # This part gets the first set of cross multiplications based on their
        # location in the matrix of index pairs.
        fst   = [(j,i) for i in range(size/2) for j in range(i+1)]
        fst  += [(i,j) for i in range(size/4) for j in range(size/2, 3*size/4)]
        fst  += [(i,j) for i in range(size/4, size/2) for j in range(3*size/4, size)]

        # The second set of cross multiplications is done by mapping the
        # multiplication indices.
        keys    = range(size)
        values  = range(size/2, size) + range(size/4, size/2) + range(size/4)
        mapping = dict(zip(keys, values))
        snd =  [(mapping[i], mapping[j]) for (i, j) in fst]

        return (fst, snd)

    def log(self, message, send_pipe=False, status=0):
        """
        Simple logger. If the correlator is in multiprocessing mode,
        then send a message back to the control process.

        Input:

        - ``message``: A string to print.
        """
        if self.mp:
            self.queue.put(message)
            if send_pipe:
                self.socket.send((status, message))
        else:
            print message

    def mp_init(self, connection, queue):
        """
        This function

        Input:

        - ``connection``: Python Connection object created with \
                multiprocessing.Pipe()
        """
        self.mp = True
        self.socket = connection
        self.queue = queue

    def poco_init(self):
        """
        This function performs some initial procedures for the pocket
        correlator, setting the equalization coefficients and the sync.

        Input:

        - ``sync_sel``: This parameter tells whether or not to use an \
                onboard syncronizer (True) or an external one (False).
        """
        # Set the eq_coeff parameter.
        # 0-16 coeff, 17 coeff-en, 20-25 coeff-addr, 30-31 ant-pair-sel
        if self.poco == 'snap12': # XXX impliment this system for all correlators.
            size = self.antennas / 2
            eq_coeff = int(self.eq_coeff) # Test to see if scalar
            shape = (size, 2*self.nchan)
            self.eq_coeff = eq_coeff * _np.ones(shape, dtype=_np.uint32)

            # Set the eq_coeff parameter on the FPGA.
            for i in range(size):
                eq_name = '_'.join(['eq', str(2*i), str(2*i+1), 'coeffs'])
                for j, coeff in enumerate(self.eq_coeff[i]):
                    if self.verbose:
                        message = 'POCO%d: ' % self.antennas
                        message += eq_name + '[%d]: %d' % (j, coeff)
                        self.log(message) # XXX sending mp in loop?
                    self.write_int(eq_name, coeff, offset=j)
        else:
            for ant_sel in range(self.antennas/2):
                for addr in range(EQ_ADDR_RANGE):
                    if self.verbose:
                        items = (ant_sel, addr, self.eq_coeff)
                        message = 'POCO%d: ' % self.antennas
                        message += 'ant_sel=%d, addr=%2d, eq_coeff=%d' % items
                        self.log(message) # XXX
                    eq_coeff  = (self.eq_coeff) + (1 << 17)
                    eq_coeff += (addr << 20) + (ant_sel << 28)
                    self.write_int('eq_coeff', eq_coeff)

        # Sync selection
        # TODO completely remove the sync_sel register from all designs. This
        # design does not need an external sync...
        self.sync_sel = True
        self.write_int('Sync_sync_sel', self.sync_sel)
        if self.sync_sel:
            for i in (0, 1, 0):
                if self.verbose:
                    self.log('POCO%d: sync_pulse: %d' % (self.antennas, i))
                self.write_int('Sync_sync_pulse', i)

        self.log('Starting the correlator.')
        self.count = 0
        self.write_int('acc_length', self.acc_len)
        self.log('Integration time: ' + str(self.int_time) + ' s')

        # The first integration is all junk.
        while self.count < 1:
            self.poll()

    def poco_recall(self):
        """
        If the bof process is alredy running, this function retrieves
        the sync selection and the integration counter from the
        correlator.
        """
        self.count = self.read_int('acc_num')
        self.acc_len = self.read_int('acc_length')
        self.fft_shift = self.read_int('ctrl_sw')
        self.insel = self.read_int('insel_insel_data')
        self.int_time  = self.acc_len / self.samp_rate

    def poll(self):
        """
        This function waits until the integration count has been
        incrimented and returns the Julian date of the integration.

        Return:

        - ``jd``: Julian date of the accumulation.
        """
        self.count = self.read_int('acc_num')
        while self.read_int('acc_num') == self.count:
            _time.sleep(0.001)
        jd = get_jul_date(_time.time() - 0.5*self.int_time)
        _time.sleep(0.001)
        self.count = self.read_int('acc_num')
        return jd

    def read_corr(self, corr_pair):
        """
        This function reads out cross-multiplied data from a specific
        BRAM on the ROACH and returns data from the two FFT stages.

        Input:

        - ``corr_pair``: Tuple telling which two antennas being \
                cross-correlated need to be read from the ROACH.

        Return:

        - Data in the structure np.array([stage1, stage2])
        """
        # Generate the device names
        prefix   = 'xengine%d_muxed_' % self.antennas
        prefix  += self.get_corr_name(corr_pair) + '_'
        real_dev = prefix + 'real'
        imag_dev = prefix + 'imag'

        # Read the BRAM's
        real_raw = self.read(real_dev, self.bram_size)
        if corr_pair[0] != corr_pair[1]:
            imag_raw = self.read(imag_dev, self.bram_size)
        else:
            imag_raw = '\x00' * self.bram_size

        # Convert the strings to numeric data
        cx_data      = _np.zeros(self.nchan << 1, dtype=_np.complex64)
        cx_data.real = _np.fromstring(real_raw, '>i4')
        cx_data.imag = _np.fromstring(imag_raw, '>i4')

        # The data needs to be reshaped to account for the two FFT stages
        return cx_data.reshape((self.nchan, 2)).transpose()

    def reconnect(self):
        """
        This function can be run if the correlator can't be reached
        in the middle of data collection. This should only be run if
        the bof process for the spectrometer has been already started.
        """
        while True:
            try:
                self.read_int('ping')
                break
            except:
                _time.sleep(0.1)

    def retrieve_data(self, antenna_list=None):
        """
        This function retrieves data off of the ROACH and writes it to
        uv files.
        """
        ants  = self.antennas
        start = self.count
        if antenna_list is not None and self.model == 2:
            antenna_list = map(self.get_ant_ind, antenna_list)

        self.uv_open()
        while True:
            jd = self.poll()
            if not self.mp:
                print 'POCO%d: Integration count: %d' % (ants, self.count)

            # Read and save data from all BRAM's
            try:
                for fst, snd in zip(self.fst, self.snd):
                    fst_in_list = self.check_corr(fst, antenna_list)
                    snd_in_list = self.check_corr(snd, antenna_list)
                    if fst_in_list or snd_in_list:
                        corr_data = self.read_corr(fst)
                    if fst_in_list:
                        self.uv_update(fst, corr_data[0], jd)
                    if snd_in_list:
                        if snd[0] > snd[1]:
                            self.uv_update(snd, _np.conj(corr_data[1]), jd)
                        else:
                            self.uv_update(snd, corr_data[1], jd)
            except RuntimeError:
                self.log('WARNING: Cannot connect. Skipping integration.')
                self.reconnect()
                continue

            # Check for a quit signal from the controller if in server mode
            if self.mp and self.socket.poll():
                cmd = self.socket.recv()
                if cmd == 'stop':
                    self.log('Received stop command from user.')
                    self.socket.send((0, 'Stopping data collection.'))
                    self.uv_close()
                    return
                elif cmd == 'status':
                    self.log('Received status command from user.')
                    msg = 'POCO%d: Writing data to disk\n' % ants
                    msg += 'POCO%d: Integration count: %d' % (ants, self.count)
                    self.socket.send((0, msg))
                elif cmd == 'kill-server':
                    msg = 'Cannot shut down. Data writing in progress.'
                    self.socket.send((1, msg))
                else:
                    self.socket.send((1, 'The correlator is already running.'))
                    if not isinstance(cmd, str):
                        cmd = ' '.join(cmd)
                    self.log('POCO: Received invalid command: ' + cmd)

            # Check if there is time for more integrations
            if self.limit is not None and self.count + 1 > self.limit:
                self.log('Time limit reached.')
                self.uv_close()
                return

            # Make a new UV file every 300 integrations
            if (self.count - start) % 300 == 0:
                self.log('Closing UV file.')
                self.uv_close()
                self.log('Reopening a new UV file.')
                self.uv_open()

    def set_attributes(self, calfile, samp_rate, nyquist_zone, bandpass=None):
        """
        This function sets certain attributes of the observation being
        made, such as which antenna calibration file to use and which
        Nyquist zone to use for data storage.

        Input:

        - ``calfile``: Antenna calibration file.
        - ``nyquist_zone``: Nyquist zone to use. The frequency range \
                for each Nyquist zone is defined to be \
                :math:`(n-1) \\dfrac{f_{samp}}{2} \le f \le n \
                \\dfrac{f_{samp}}{2}`, where the lowest order Nyquist \
                zone, :math:`n = 1`, represents the frequencies going \
                from :math:`0 \le f \le \\dfrac{f_{samp}}{2}`.
        - ``bandpass``: Bandpass is the digital equalization that \
                needs to be divided from the output data, with \
                dimensions ``(nant, nchans)`` and dtype ``complex64``.
        """
        if self.model is None:
            raise RuntimeError('ROACH model not detected.')

        # Use the nyquiqt zone to determine frequency information that will be
        # written to the miriad file. Frequencies are in GHz (not sure why...)
        nyquist_ghz = samp_rate / 2 / 1e9
        sdf = nyquist_ghz / self.nchan
        if nyquist_zone % 2:
            sfreq = (nyquist_zone - 1) * nyquist_ghz
        else:
            sfreq = nyquist_zone * nyquist_ghz
            sdf *= -1

        # Get basic attributes of the observation and the correlator
        self.aa = _aipy.cal.get_aa(calfile, sdf, sfreq, self.nchan)
        self.sdf = sdf
        self.sfreq = sfreq
        self.bandpass = bandpass
        self.samp_rate = samp_rate
        self.nyquist = nyquist_zone

    def set_filename(self, filename):
        """
        This function sets the filename prefix for the output files.
        The files are saved as 'filename.<julian_date>.uv.'

        Input:

        - ``filename``: Filename base for the UV files.
        """
        fname, wdir, tmp = self.filename, self.writedir, self.tmp_file
        self.filename = _os.path.abspath(filename)
        self.writedir = _os.path.dirname(self.filename)
        self.tmp_file = _os.path.join(self.writedir, 'TMP_FILE')
        if _os.system('mkdir -pv ' + self.writedir):
            self.log('ERROR: Cannot set filename for saving. Using old values.')
            self.filename = fname
            self.writedir = wdir
            self.tmp_file = tmp
            return 1
        else:
            return 0

    def set_verbose(self, state):
        """
        This function sets the verbosity of the output.
        """
        self.verbose = state
        if self.verbose:
            self.log('Enabling verbose output.')

    def scheduler(self,
                  n_integ=None,
                  start=None,
                  stop=None,
                  interval=None,
                  no_run=False):
        """
        This function schedules start times, stop times, number of
        integrations, and time intervals to run the correlator.

        Input:

        - ``n_integ``: Number of integrations to do.
        - ``start``: Starting time (%Y-%m-%d-%H:%M)
        - ``stop``: Stopping time (%Y-%m-%d-%H:%M)
        - ``interval``: Time interval to collect integrations \
                (U,time)
        - ``no_run``: Check if the arguments are valid and exit.

        The ``n_integ``, ``stop``, and ``interval`` arguments are
        mutually exclusive and can't simultaneously be used.

        Units to be used with the ``interval`` keyword argument:

        - ``D``: Number of days to integrate for.
        - ``H``: Number of hours to integrate for.
        - ``M``: Number of minutes to integrate for.

        Example: To integrate for 5 minutes, set ``interval='M,5'``.
        """
        # Check for redundant values.
        if n_integ is not None and stop is not None:
            err_str = 'ERROR: n_integ and stop cannot both be set.'
            if no_run:
                return (1, err_str)
            else:
                raise ValueError(err_str)
        if n_integ is not None and interval is not None:
            err_str = 'ERROR: n_integ and interval cannot both be set.'
            if no_run:
                return (1, err_str)
            else:
                raise ValueError(err_str)
        if stop is not None and interval is not None:
            err_str = 'ERROR: stop and interval cannot both be set.'
            if no_run:
                return (1, err_str)
            else:
                raise ValueError(err_str)

        # Convert the start time into an integer.
        if start is None:
            start = _time.time()
            wait  = False
        else:
            start = get_seconds(start)
            if start <= _time.time():
                err_str = 'Starting time cannot be in the past.'
                if no_run:
                    return (1, err_str)
                else:
                    raise ValueError(err_str)
            wait = True

        # Determine the number of integrations to perform
        self.limit = None
        if n_integ is None:
            if stop is None:
                if interval is None:
                    # If we are waiting to start and there is no stop time, the
                    # variable "stop" remains None. This is supposed to happen.
                    if not wait:
                        return
                else:
                    # Convert interval to seconds
                    unit, interval = interval.split(',')
                    if unit == 'D':
                        conversion = 86400
                    elif unit == 'H':
                        conversion = 3600
                    elif unit == 'M':
                        conversion = 60
                    else:
                        err_str = 'Invalid interval unit: ' + unit
                        if no_run:
                            return (1, err_str)
                        else:
                            raise ValueError(err_str)

                    stop = start + conversion * float(interval)
            else:
                stop = get_seconds(stop)
                if stop <= start:
                    err_str = ' '.join(['The stopping time must occur',
                                        'after the starting time.'])
                    if no_run:
                        return (1, err_str)
                    else:
                        raise ValueError(err_str)

            # stop is None when there is a start time but no stopping limit
            # since I didn't want to wait until the start time to check if the
            # starting and stopping limits are valid.
            if stop is None:
                n_integ = None
            else:
                n_integ = int((stop - start) / self.int_time)

        # Check of the number of integrations is valid.
        if n_integ is not None and n_integ < 1:
            err_str = ' '.join(['The correlator must be running for',
                                'at least the length of one integration.'])
            if no_run:
                return (1, err_str)
            else:
                raise ValueError(err_str)

        # No need to run the correlator if just checking parameters.
        if no_run:
            return (0, '')

        # This is meant to be done after all of the calculations in case there
        # was a user error in setting the intervals so that it can be known as
        # soon as possible and nobody has to wait for it.
        if wait:
            self.log('Waiting until start time: ' + _time.ctime(start))
            _time.sleep(start - _time.time())

        # The limit variable is the last integration that can be performed
        # before the retrieve_data function returns and exits.
        self.count = self.read_int('acc_num')
        if n_integ is not None:
            self.limit = self.count + n_integ

    def start_bof(self, acc_len, eq_coeff, fft_shift, insel, force_restart,
                  internal_synth=False, synth_file=None, synth_value=None):
        """
        This function starts the bof file on the ROACH. This docstring
        only gives a brief overview of the parameters, and more
        comprehensive explanations can be found elsewhere within the
        documentation.

        Input:

        - ``acc_len``: Integration/dump time. This can be converted \
                to a time in seconds as \
                :math:`t = \\dfrac{acc\_len}{f_{samp}}`.
        - ``eq_coeff``: Equalization coefficient for the ROACH.
        - ``fft_shift``: Integer telling which stages in the pocket \
                correlator's FFT block to shift.
        - ``insel``: Selects which input to use.
        - ``force_restart``: This function forces the pocket \
                correlator to be restarted, as opposed to letting \
                it continue running if it was.

        Return:

        - ``prog_bof``: True if the ROACH was reprogrammed with the bof file. \
                False if the bof file was already running.
        """
        # Start the bof process if it isn't running already.
        prog_bof, configure = [not b for b in self.check_running()]
        poco_bof = self.boffile

        if force_restart:
            self.log('WARNING: Forcing a restart of the bof process.')
            self.progdev('')
            prog_bof = True

        # The ROACH2 has different initialization prcedures than the ROACH.
        if prog_bof:
            if self.model == 1:
                self.log('Initializing bof process on FPGA.')
                self.progdev(poco_bof)
            elif self.model == 2:
                if self.poco == 'spoco12' and internal_synth:
                    self.snap_synth(synth_file, synth_value)
                self.progdev('')
                prog_cmd = ['adc16_init.rb', self.host, poco_bof]
                if _os.system(' '.join(prog_cmd)):
                    raise RuntimeError('ERROR: Cannot initialize ADC.')
        else:
            self.log('Bof process already running on FPGA.')
        if self.verbose:
            self.log('bof process: ' + poco_bof + '\n')

        # Write FPGA parameters to the ROACH and save them.
        if prog_bof or configure:
            self.log('Configuring pocket correlator.')
            self.acc_len   = acc_len
            self.eq_coeff  = eq_coeff
            self.fft_shift = fft_shift
            self.insel     = insel
            self.int_time  = self.acc_len / self.samp_rate
            if self.verbose:
                message = '%-20s:\t%d\n' % ('acc_length', self.acc_len)
                message += '%-20s:\t%d\n' % ('ctrl_sw', self.fft_shift)
                message += '%-20s:\t%d\n\n' % ('insel_insel_data', self.insel)
                self.log(message)
            self.write_int('ctrl_sw',          self.fft_shift)
            self.write_int('insel_insel_data', self.insel)

        # Return whether the bof file was started or configured
        return prog_bof or configure

    def snap_synth(self, synth_file=None, synth_value=None):
        """
        This function programs the synthesizer on SNAP boards. This
        is to be done before programming the ADC.

        Input:

        - ``synth_file``: Hex file exported from CodeLoader.
        - ``synth_value``: Synthesizer frequency in MHz.
        """
        # Simple value checking to make sure everything is chill.
        if synth_file is not None and synth_value is not None:
            raise ValueError('ERROR: Duplicate synth values given.')
        if synth_file is None and synth_value is None:
            raise ValueError('ERROR: No synth programming provided.')

        # When the external synth gets programmed, it stays programmed
        # even if the FPGA gets reprogrammed, or so I think...
        self.progdev(self.boffile)
        if synth_file is not None:
            self.synth_codeloader(synth_file)
        elif synth_value is not None:
            raise RuntimeError('ERROR: Cannot set synth from arbitrary value.')

    def uv_close(self):
        """
        This function closes the current UV file and renames it to a
        unique filename based on the Julian date.
        """
        # Check if a uv file has been opened before moving it.
        try:
            del self.uv
        except AttributeError:
            return

        ants = self.antennas
        filename = '.'.join([self.filename, str(get_jul_date()), 'uv'])
        self.log('POCO%d: Closing UV file and renaming to %s.' % (ants, filename))
        _os.rename(self.tmp_file, filename)

    def synth_codeloader(self, filename):
        """
        This function reads a file produced by Code Loader containing
        values to write to the lmx_ctrl register.
        """
        # Read in the lines from the file and convert them to integers
        # Assumptions: files have DOS line endings (made from Windows) and the
        # last thing in each line is a hex string.
        with open(filename) as f:
            nums = [int(l[-12:-2], 16) for l in f.readlines()]

        # Enable the synth
        self.write_int('adc16_use_synth', (1 << 31) - 1)

        for i, n in enumerate(nums):
            self.write_int('lmx_ctrl', n, True)

        # Right now, the only way I've been able to use the synth is to redirect
        # the debugging output into the clock input. Setting this to 0 will
        # still keep the synth running, but will use the sample clock. This
        # needs to be changed if the synth works.
        self.write_int('adc16_use_synth', 0)

    def uv_open(self):
        """
        This function opens a Miriad UV file for writing.
        """
        if self.model is None:
            raise RuntimeError('ROACH model not detected.')
        uv = _aipy.miriad.UV(self.tmp_file, status = 'new')
        for v in UV_VAR_TYPES:
            uv.add_var(v, UV_VAR_TYPES[v])
        rpoco = 'rpoco' + str(self.antennas)
        uv['history'] = rpoco
        uv['obstype'] = 'mixed'
        uv['source'] = 'zenith'
        uv['operator'] = rpoco
        uv['telescop'] = rpoco
        uv['version'] = '0.1'
        uv['nants'] = self.antennas
        ants = _np.array([self.aa[i].pos for i in range(uv['nants'])]).transpose()
        uv['antpos'] = ants.flatten()
        uv['npol'] = 1
        uv['epoch'] = 2000.
        uv['nspect'] = 1
        uv['ischan'] = 1
        uv['veldop'] = uv['vsource'] = 0.
        uv['longitu'] = self.aa.long
        uv['latitud'] = uv['dec'] = uv['obsdec'] = self.aa.lat
        uv['sfreq'] = uv['freq'] = uv['restfreq'] = self.sfreq
        uv['sdf'] = self.sdf
        uv['nchan'] = uv['nschan'] = self.nchan
        uv['inttime'] = self.int_time

        if self.bandpass is None: # XXX why is this bram_size?
            self.bandpass = _np.ones(self.bram_size, dtype=_np.complex)
        uv['bandpass']= self.bandpass.flatten()
        uv['nspect0'] = self.antennas
        uv['nchan0'] = self.nchan
        uv['ntau'] = uv['nsols'] = 0
        uv['nfeeds'] = 1
        uv['ngains'] = uv['nants']*(uv['ntau'] + uv['nfeeds'])
        uv['freqs'] = (uv['nants'],) + (self.nchan, self.sfreq, self.sdf) * uv['nants']
        self.uv = uv

    def uv_update(self, pair, data, jd):
        """
        This function updates the uv file for a given baseline.

        Input:

        - ``pair``: Pair of indices identifying the cross-correlation.
        - ``data``: Numeric data for a cross-correlation.
        - ``jd``: Julian date of the observation.
        """
        i, j = sorted(pair)
        uvw = _np.array([i,j,0], dtype=_np.double)
        preamble = (uvw, jd, (i,j))

        # to get rid of the dc offset. causes plots to be "quantized"
        data[-2] = 0
        data[-1] = 0
        data[0] = 0
        data[1] = 0

        self.uv['ra'] = self.uv['obsra'] = self.uv['lst'] = self.aa.sidereal_time()
        self.uv['pol'] = _aipy.miriad.str2pol['xx']
        flags = _np.zeros(data.shape, dtype = _np.int)
        flags[-2] = 1.
        flags[-1] = 1.
        flags[0] = 1.
        flags[1] = 1.

        # Write to the UV file (what a helpful comment right there...)
        self.uv.write(preamble, data, flags=flags)

    def write_testvec(self, ant_num, vector):
        """
        This function writes a test vector to the ADC for a particular
        antenna. This is only supported on the SNAP correlator.
        """
        if self.poco != 'spoco12':
            message = 'WARNING: ADC test vectors not supported on '
            message += self.poco + '. Ignorning.'
            self.log(message)
            return 1

        # Convert to 32 bits, then swap endianness
        nbytes = len(vector)
        vector = vector.astype(_np.int8)
        vector = _struct.pack(nbytes*'b', *vector)
        vector = ''.join([3*'\x00' + b for b in vector])

        # Write the data to the device
        bram_name = 'test_vec_' + str(ant_num) + '_ram'
        self.write(bram_name, vector)
        return 0

class POCOdemux2(POCO):
    # TODO funtions to impliment:
    # start_bof
    # poco_init
    # poco_recall
    # read_corr
    # retrieve_data
    def get_xmult(self):
        """
        This function gets all of the cross-multiplication combos that
        the correlator multiplies. This is useful for testing purposes
        and the class data member ``antennas`` needs to be set to use
        this function. This function returns a table of all of the
        cross-correlation pairs that are on the correlator.
        """
        size = self.antennas
        return [(i, j) for i in range(size) for j in range(size) if i <= j]

    def poco_init(self):
        """
        This function performs some initial procedures for the pocket
        correlator, setting the equalization coefficients and the sync.

        Input:

        - ``sync_sel``: This parameter tells whether or not to use an \
                onboard syncronizer (True) or an external one (False).
        """
        # Format the eq_coeff parameter to write it into the FPGA
        size = self.antennas
        error = 'ERROR: EQ coeff does not match correlator size.'
        try:
            eq_coeff = int(self.eq_coeff) # Test to see if scalar
            shape = (size, self.nchan)
            self.eq_coeff = eq_coeff * _np.ones(shape, dtype=_np.uint32)
        except TypeError:
            eq = np.array(self.eq_coeff, dtype=_np.uint32)
            if len(eq.shape) == 1:
                if eq.shape[0] == size:
                    clist = [eq[i]*_np.ones(self.nchan) for i in range(size)]
                elif eq.shape[0] == self.nchan:
                    clist = [eq for i in range(size)]
                else:
                    raise ValueError(error)
                self.eq_coeff = _np.array(clist)
            elif len(eq.shape) == 2:
                if eq.shape != (size, self.nchan):
                    raise ValueError(error)
                self.eq_coeff = eq
            else:
                raise ValueError(error)

        # Set the eq_coeff parameter on the FPGA.
        for i in range(size):
            eq_name = '_'.join(['eq', str(i), 'coeffs'])
            for j, coeff in enumerate(self.eq_coeff[i]):
                if self.verbose:
                    message = 'POCO%d: ' % self.antennas
                    message += eq_name + '[%d]:'% (j, coeff)
                    self.log(message)
                self.write_int(eq_name, coeff, offset=j)

        # Sync selection
        self.write_int('sync_arm', 0)
        for i in (1, 1 | (1 << 4), 0):
            if self.verbose:
                self.log('POCO%d: sync_arm: %d' % (self.antennas, i))
            self.write_int('sync_arm', i)

        self.log('Starting the correlator.')
        self.count = 0
        self.write_int('acc_length', self.acc_len)
        self.log('Integration time: ' + str(self.int_time) + ' s')

        # The first integration is all junk.
        while self.count < 1:
            self.poll()

    def poco_recall(self):
        """
        If the bof process is alredy running, this function retrieves
        the sync selection and the integration counter from the
        correlator.
        """
        self.count = self.read_int('acc_num')
        self.acc_len = self.read_int('acc_length')
        self.fft_shift = self.read_int('pfb_ctrl')
        self.insel = self.read_int('input_source_sel')
        self.int_time  = self.acc_len / self.samp_rate

    def read_corr(self, corr_pair):
        """
        This function reads out cross-multiplied data from a specific
        BRAM on the ROACH and returns data from the two FFT stages.

        Input:

        - ``corr_pair``: Tuple telling which two antennas being \
                cross-correlated need to be read from the ROACH.

        Return:

        - Data in the structure np.array([stage1, stage2])
        """
        # Generate the device names
        prefix   = 'xengine%d_' % self.antennas
        prefix  += self.get_corr_name(corr_pair) + '_'
        real_dev = prefix + 'real'
        imag_dev = prefix + 'imag'

        # Read the BRAM's
        real_raw = self.read(real_dev, self.bram_size)
        if corr_pair[0] != corr_pair[1]:
            imag_raw = self.read(imag_dev, self.bram_size)
        else:
            imag_raw = '\x00' * self.bram_size

        # Convert the strings to numeric data
        cx_data      = _np.zeros(self.nchan, dtype=_np.complex64)
        cx_data.real = _np.fromstring(real_raw, '>i4')
        cx_data.imag = _np.fromstring(imag_raw, '>i4')
        return cx_data

    def retrieve_data(self, antenna_list=None):
        """
        This function retrieves data off of the ROACH and writes it to
        uv files.
        """
        ants  = self.antennas
        start = self.count
        if antenna_list is not None and self.model == 2:
            antenna_list = map(self.get_ant_ind, antenna_list)
        while True:
            jd = self.poll()
            if self.mp:
                self.queue.put(('num', self.count))
            else:
                print 'POCO%d: Integration count: %d' % (ants, self.count)

            # Read and save data from all BRAM's
            try:
                for pair in self.pairs:
                    if self.check_corr(pair, antenna_list):
                        corr_data = self.read_corr(pair)
                        self.uv_update(pair, corr_data, jd)
            except RuntimeError:
                self.log('WARNING: Cannot reach the ROACH. Skipping integration.')
                self.reconnect()
                continue

            # Check if there is time for more integrations
            if self.limit is not None and self.count + 1 > self.limit:
                self.log('Time limit reached.')
                self.uv_close()
                return

            # Make a new UV file every 300 integrations
            if (self.count - start) % 300 == 0:
                self.log('Closing UV file.')
                self.uv_close()
                self.log('Reopening a new UV file.')
                self.uv_open()

    def start_bof(self, acc_len, eq_coeff, fft_shift, insel, force_restart):
        """
        This function starts the bof file on the ROACH. This docstring
        only gives a brief overview of the parameters, and more
        comprehensive explanations can be found elsewhere within the
        documentation.

        Input:

        - ``acc_len``: Integration/dump time. This can be converted \
                to a time in seconds as \
                :math:`t = \\dfrac{acc\_len}{f_{samp}}`.
        - ``eq_coeff``: Equalization coefficient for the ROACH.
        - ``fft_shift``: Integer telling which stages in the pocket \
                correlator's FFT block to shift.
        - ``insel``: Selects which input to use.
        - ``force_restart``: This function forces the pocket \
                correlator to be restarted, as opposed to letting \
                it continue running if it was.

        Return:

        - ``prog_bof``: True if the ROACH was reprogrammed with the bof file. \
                False if the bof file was already running.
        """
        # Start the bof process if it isn't running already.
        prog_bof, configure = [not b for b in self.check_running()]
        poco_bof = self.boffile

        if force_restart:
            self.log('WARNING: Forcing a restart of the bof process.')
            self.progdev('')
            prog_bof = True

        # The ROACH2 has different initialization prcedures than the ROACH.
        if prog_bof:
            prog_cmd = ['adc16_init.rb', '-d', '2', self.host, poco_bof]
            if _os.system(' '.join(prog_cmd)):
                raise RuntimeError('ERROR: Cannot initialize ADC.')
        else:
            self.log('Bof process already running on FPGA.')
        if self.verbose:
            self.log('bof process: ' + poco_bof + '\n')

        # Write FPGA parameters to the ROACH and save them.
        if prog_bof or configure:
            self.log('Configuring pocket correlator.')
            self.acc_len   = acc_len
            self.eq_coeff  = eq_coeff
            self.fft_shift = fft_shift
            self.insel     = insel
            self.int_time  = self.acc_len / self.samp_rate
            if self.verbose:
                message = '%-20s:\t%d\n' % ('acc_length', self.acc_len)
                message += '%-20s:\t%d\n' % ('pfb_ctrl', self.fft_shift)
                message += '%-20s:\t%d\n\n' % ('input_source_sel', self.insel)
            self.write_int('pfb_ctrl', self.fft_shift)
            self.write_int('input_source_sel', self.insel)

        # Return whether the bof file was started or configured
        return prog_bof or configure

# Debugging class
class FakeROACH(POCO):
    """
    Simulated ROACH board for offline testing.
    """
    def check_connected(self):
        return True

    def poco_init(self):
        return

    def poco_recall(self):
        return

    def poll(self):
        """
        Wait until the accumulation number has updated.
        """
        _time.sleep(self.int_time)
        jd = get_jul_date(_time.time() - 0.5*self.int_time)
        self.count += 1
        return jd

    def progdev(self, *args, **kwargs):
        return 'ok'

    def read_corr(self, corr_pair):
        """
        Generate fake data to store in the UV file.
        """
        # Convert the strings to numeric data
        lendat  = self.nchan << 1
        window  = 10 * _np.abs(2*_np.sin(_np.pi * _np.arange(lendat) / lendat))
        cx_data = _np.zeros(lendat, dtype=_np.complex64)
        cx_data.real = _npr.randn(lendat) + window
        cx_data.imag = _npr.randn(lendat) + window
        cx_data[100:200] += 20.0

        # The data needs to be reshaped to account for the two FFT stages
        return cx_data.reshape((self.nchan, 2)).transpose()

    def read_int(self, bram):
        return 0

    def start_bof(self, acc_len=1<<24, eq_coeff=16, fft_shift=0x3ff, insel=0,
                 force_restart=None, internal_synth=False, synth_file=None,
                 synth_value=None):
        """
        Set object variables in the POCO start_bof function.
        """
        self.acc_len   = acc_len
        self.eq_coeff  = eq_coeff
        self.fft_shift = fft_shift
        self.insel     = insel
        self.int_time  = self.acc_len / self.samp_rate
        self.sync_sel  = True
        self.count     = 0
        return True

def get_ant_index(model, index):
    """
    This function returns the numerical index of an antenna based on
    the label on the xengine BRAM block or the label on the ROACH2 ADC.

    Input:

    - ``model``: The pocket correlator (rpoco8, rpoco16, rpoco24...).
    - ``index``: The label of the channel.
    """
    if model not in ['rpoco8', 'rpoco16', 'rpoco24', 'rpoco32']:
        raise ValueError('Invalid input.')
    antennas = int(model[5:]) # Turn this into a number

    try:
        ant_num = int(index)
    except ValueError:
        if len(index) == 1:
            ant_num = ord(index) - ord('a')
        elif len(index) == 2: # ROACH2 antenna names
            if antennas > 16:
                raise RuntimeError('This is not implimented yet.')

            letter, number = index[0], int(index[1]) - 1
            if number < 0 or number > 3:
                raise ValueError('Invalid antenna number.')
            if antennas == 8:
                # Check if the input is valid
                if number or ord(letter) < ord('a') or ord(letter) > 'h':
                    raise ValueError('Invalid antenna number.')
                ant_num = ord(letter) - ord('a')
            elif antennas == 16:
                # Check if the input is valid
                if number > 1 or ord(letter) < ord('a') or ord(letter) > 'h':
                    raise ValueError('Invalid antenna number.')

                letnum = ord(letter) - ord('a')
                ant_num = letnum * 2 + number
        else:
            raise ValueError('Invalid antenna number.')

    # Check that the index is valid
    if ant_num < antennas:
        return ant_num
    else:
        raise ValueError('Antenna number out of range.')

def get_jul_date(unixtime=None):
    """
    This function computes the Julian date based on unix time.

    Input:

    - ``unixtime``: Seconds since the Epoch. If this argument isn't \
            passed into the function, the current time is used.

    Return:

    - Returns the Julian date.
    """
    if unixtime is None:
        unixtime = _time.time()
    return unixtime / 86400.0 + 2440587.5

def get_model_uv(infiles):
    """
    This function gets the poco model from UV files.

    Input:

    - ``infiles``: The UV files to use to detect the poco model.
    """
    models = list(set([_aipy.miriad.UV(f)['operator'][:-1] for f in infiles]))
    if len(models) > 1:
        raise ValueError('Input UV files are from different ROACH models.')

    model = models[0]
    if model in ['rpoco8', 'rpoco16', 'rpoco32']:
        return model
    else:
        return 'rpoco8'

def get_seconds(date=None, fmt=TIME_FMT):
    """
    This function takes a date of some format and converts it to
    the number of seconds since the Epoch.

    Input:

    - ``date``: Date to be converted. Defaults to current time.
    - ``fmt``: Format of the date string. Default: %Y-%m-%d-%H:%M

    Return:

    - Number of seconds since Epoch.
    """
    if date is None:
        return _time.time()
    else:
        return _time.mktime(_time.strptime(date, fmt))

def is_demux2(poco):
    """
    This function detects if a poco model needs demux2 ADC settings.

    Input:

    - ``poco``: Name of a correlator model.
    """
    return poco == 'spoco6'

def mode_list2int(modelist):
    """
    list is [board, board version, demux, antennas]
    """
    modelist = modelist[:] # Don't use the original.
    assert len(modelist) == 4, 'Attribute list must have 4 items.'
    modelist[0] = ord(modelist[0].lower()[0]) - ord('a') # position in alphabet
    attr_bits = [5,3,3,5]
    bitpos = _np.r_[0, _np.cumsum(attr_bits[:-1])]
    attr = zip(modelist, bitpos)
    mode = sum([a << b for a, b in attr])
    return mode

def mode_int2list(mode):
    """
    list is [board, board version, demux, antennas]
    """
    # TODO finish writing the comment on the next line
    # Bits per
    attr_bits = [5,3,3,5]
    bitpos = _np.r_[0, _np.cumsum(attr_bits[:-1])]

    # Get info out of number
    modelist = []
    for nb, pos in zip(attr_bits, bitpos):
        sel = sum([1 << i for i in range(nb)]) << pos
        modelist.append((mode & sel) >> pos)

    # Set the board
    if modelist[0] == ord('r') - ord('a'):
        modelist[0] = 'roach'
    elif modelist[0] == ord('s') - ord('a'):
        modelist[0] = 'snap'

    return modelist

def spec_list(infiles, ant_i, ant_j, verbose=False):
    """
    Originally in plot_mean_corr.py
    """
    # Initialize arrays to store the spectra
    spectra_r = []
    spectra_i = []
    last_nchan = -1
    nfiles = len(infiles)

    # Read spectra from the UV files into numpy arrays
    for num, infile in enumerate(map(_os.path.abspath, infiles)):
        uv = _aipy.miriad.UV(infile)
        uv.select('antennae', ant_i, ant_j)
        nchan = uv['nchan']
        if last_nchan > 0  and nchan != last_nchan:
            raise ValueError('Number of channels do not match across inputs.')
        last_nchan = nchan

        # Get all of the spectra
        for i, (preamble, data) in enumerate(uv.all()):
            spectra_r.append(_np.real(data.take(range(nchan))))
            spectra_i.append(_np.imag(data.take(range(nchan))))

        if num < nfiles - 1:
            del uv

        # Display a cute progress meter.
        if nfiles > 1 and verbose:
            print_progress(num, nfiles)

    return (spectra_r, spectra_i)


def print_progress(step,
                   total,
                   prog_str='Percent complete:',
                   quiet=False,
                   progfile='progress'):
    """
    Print the progress of some iteration through data. The step is the
    current i for i in range(total). This function can also display
    progress quietly by writing it to a file.

    Input:

    - ``step``: The iteration, starting at 0, of progress.
    - ``total``: Total number of iterations completed.
    - ``prog_str``: Message to print with the progress number.
    - ``quiet``: Setting this to true saves the progress to a file.
    - ``progfile``: The file to save progress to when in quiet mode.
    """
    progress = round(100 * float(step+1) / total, 2)
    progress = '\r' + prog_str + ' ' + str(progress) + '%\t\t'
    if quiet:
        if step + 1 == total:
            _os.system('rm -f ' + progfile)
        else:
            with open(progfile, 'w') as f:
                f.write(progress[1:-2] + '\n')
    else:
        print progress,
        if step == total - 1:
            print
        else:
            _sys.stdout.flush()
