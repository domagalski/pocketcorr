#!/usr/bin/env python2

################################################################################
## This module defines a class for interfacing with a ROACH pocket correlator.
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

import os         as _os
import aipy       as _aipy
import time       as _time
import numpy      as _np
from corr import katcp_wrapper as _katcp

BRAM_SIZE   = 4 << 11
NCHAN       = 1 << 10
SAMP_RATE   = 200e6
POCO_BOF8   = 'rpoco8.bof'
POCO2_BOF8  = 'rpoco8_r2.bof'
POCO2_BOF16 = 'rpoco16.bof'
POCO2_BOF32 = None
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
        self.model = None
        self.antennas = None

        # Display options
        self.verbose = False
        self.filename = 'poco'

        # Set some null values for FPGA parameters.
        self.acc_len   = None
        self.eq_coeff  = None
        self.fft_shift = None
        self.insel     = None
        self.sync_sel  = None

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
        print 'Opening FPGA client.'

    def check_running(self):
        """
        This function checks to see if the bof process for the
        correlator has been initialized on the ROACH. I've put a
        constant in the design that I use to "ping" the correlator,
        and if it can be read, this indicates that the bof process has
        been started.
        """
        try:
            return bool(self.read_int('ping'))
        except RuntimeError:
            return False

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

    def get_model(self, rpoco):
        """
        This function determines which ROACH type is being used and
        sets the appropriate class data members (model, antennas,
        boffile). Currently, this will throw an error for ROACH2
        designs, since they haven't been made yet.

        Input:

        - ``rpoco``: Name of the correlator model.
        """
        if self.verbose:
            print 'Detecting ROACH model.\n'

        # Get the antenna info from the pocketcorr design
        rpoco = rpoco.lower()
        if rpoco == 'rpoco8':
            self.model = 1
            self.antennas = 8
            self.boffile = POCO_BOF8
        elif rpoco == 'rpoco8_r2':
            self.model = 2
            self.antennas = 8
            self.boffile = POCO2_BOF8
        elif rpoco == 'rpoco16':
            self.model = 2
            self.antennas = 16
            self.boffile = POCO2_BOF16
        elif rpoco == 'rpoco32':
            self.model = 2
            self.antennas = 32
            self.boffile = POCO2_BOF32
        else:
            raise ValueError('Invalid rpoco routine.')

        # Update the filename to reflect the POCO version.
        self.filename += str(self.antennas)

        # Raise error for not implimented yet
        if self.model == 2: # and self.antennas != 16:
            # XXX there are timing errors in the current rpoco16 model
            raise RuntimeError('This is not implimented yet.')

        if self.verbose:
            print 'Detected ROACH' + (self.model == 2 and '2' or ''),
            print 'board with', self.antennas, 'ADC inputs.\n'

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

    def poco_init(self, sync_sel=True):
        """
        This function performs some initial procedures for the pocket
        correlator, setting the equalization coefficients and the sync.

        Input:

        - ``sync_sel``: This parameter tells whether or not to use an \
                onboard syncronizer (True) or an external one (False).
        """
        # Set the eq_coeff parameter.
        # 0-16 coeff, 17 coeff-en, 20-25 coeff-addr, 30-31 ant-pair-sel
        for ant_sel in range(self.antennas/2):
            for addr in range(EQ_ADDR_RANGE):
                if self.verbose:
                    items = (ant_sel, addr, self.eq_coeff)
                    print 'RPOCO%d:' % self.antennas,
                    print 'ant_sel=%d, addr=%2d, eq_coeff=%d' % items
                eq_coeff  = (self.eq_coeff) + (1 << 17)
                eq_coeff += (addr << 20) + (ant_sel << 28)
                self.write_int('eq_coeff', eq_coeff)

        # Sync selection
        self.sync_sel = sync_sel
        self.write_int('Sync_sync_sel', self.sync_sel)
        if self.sync_sel:
            for i in (0, 1, 0):
                if self.verbose:
                    print 'RPOCO%d:' % self.antennas, 'sync_pulse:', i
                self.write_int('Sync_sync_pulse', i)

        print 'Starting the correlator.'
        self.count = 0
        self.write_int('acc_length', self.acc_len)

        # The first integration is all junk.
        while self.count < 1:
            self.poll()

    def poco_recall(self):
        """
        If the bof process is alredy running, this function retrieves
        the sync selection and the integration counter from the
        correlator.
        """
        self.sync_sel = self.read_int('Sync_sync_sel')
        self.count = self.read_int('acc_num')

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
        real_raw = self.read(real_dev, BRAM_SIZE)
        if corr_pair[0] != corr_pair[1]:
            imag_raw = self.read(imag_dev, BRAM_SIZE)
        else:
            imag_raw = '\x00' * BRAM_SIZE

        # Convert the strings to numeric data
        cx_data      = _np.zeros(NCHAN << 1, dtype=_np.complex64)
        cx_data.real = _np.fromstring(real_raw, '>i4')
        cx_data.imag = _np.fromstring(imag_raw, '>i4')

        # The data needs to be reshaped to account for the two FFT stages
        return cx_data.reshape((NCHAN, 2)).transpose()

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

    def retrieve_data(self):
        """
        This function retrieves data off of the ROACH and writes it to
        uv files.
        """
        ants  = self.antennas
        start = self.count
        while True:
            jd = self.poll()
            print 'RPOCO%d: Integration count: %d' % (ants, self.count)

            # Read and save data from all BRAM's
            try:
                for fst, snd in zip(self.fst, self.snd):
                    corr_data = self.read_corr(fst)
                    self.uv_update(fst, corr_data[0], jd)
                    if snd[0] > snd[1]:
                        self.uv_update(snd, _np.conj(corr_data[1]), jd)
                    else:
                        self.uv_update(snd, corr_data[1], jd)
            except RuntimeError:
                print 'WARNING: Cannot reach the ROACH. Skipping integration.'
                self.reconnect()
                continue

            # Check if there is time for more integrations
            if self.limit is not None and self.count + 1 > self.limit:
                print 'Time limit reached.'
                self.uv_close()
                return

            # Make a new UV file every 300 integrations
            if (self.count - start) % 300 == 0:
                print 'Closing UV file.'
                self.uv_close()
                print 'Reopening a new UV file.'
                self.uv_open()

    def set_attributes(self, calfile, nyquist_zone, bandpass=None):
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
        nyquist_ghz = SAMP_RATE / 2 / 1e9
        sdf = nyquist_ghz / NCHAN
        if nyquist_zone % 2:
            sfreq = (nyquist_zone - 1) * nyquist_ghz
        else:
            sfreq = nyquist_zone * nyquist_ghz
            sdf *= -1

        # Get basic attributes of the observation and the correlator
        self.aa = _aipy.cal.get_aa(calfile, sdf, sfreq, NCHAN)
        self.fst, self.snd = self.get_xmult()
        self.sdf = sdf
        self.sfreq = sfreq
        self.nchan = NCHAN
        self.bandpass = bandpass
        self.samp_rate = SAMP_RATE
        self.nyquist = nyquist_zone

    def set_filename(self, filename):
        """
        This function sets the filename prefix for the output files.
        The files are saved as 'filename.<julian_date>.uv.'

        Input:

        - ``filename``: Filename base for the UV files.
        """
        _os.system('mkdir -pv ' + _os.path.dirname(_os.path.abspath(filename)))
        self.filename = filename

    def set_verbose(self, state):
        """
        This function sets the verbosity of the output.
        """
        self.verbose = state
        if self.verbose:
            print 'Enabling verbose output.'

    def scheduler(self, n_integ=None, start=None, stop=None, interval=None):
        """
        This function schedules start times, stop times, number of
        integrations, and time intervals to run the correlator.

        Input:

        - ``n_integ``: Number of integrations to do.
        - ``start``: Starting time (%Y-%m-%d-%H:%M)
        - ``stop``: Stopping time (%Y-%m-%d-%H:%M)
        - ``interval``: Time interval to collect integrations \
                (U,time)

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
            raise ValueError('ERROR: n_integ and stop cannot both be set.')
        if n_integ is not None and interval is not None:
            raise ValueError('ERROR: n_integ and interval cannot both be set.')
        if stop is not None and interval is not None:
            raise ValueError('ERROR: stop and interval cannot both be set.')

        # Convert the start time into an integer.
        if start is None:
            start = _time.time()
            wait  = False
        else:
            start = get_seconds(start)
            if start <= _time.time():
                raise ValueError('Starting time cannot be in the past.')
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
                        raise ValueError('Invalid interval unit: ' + unit)

                    stop = start + conversion * float(interval)
            else:
                stop = get_seconds(stop)
                if stop <= start:
                    raise ValueError(' '.join(['The stopping time must occur',
                                               'after the starting time.']))

            # stop is None when there is a start time but no stopping limit
            # since I didn't want to wait until the start time to check if the
            # starting and stopping limits are valid.
            if stop is None:
                n_integ = None
            else:
                n_integ = int((stop - start) / self.int_time)

        # Check of the number of integrations is valid.
        if n_integ is not None and n_integ < 1:
            raise ValueError(' '.join(['The correlator must be running for',
                                       'at least the length of one',
                                       'integration.']))

        # This is meant to be done after all of the calculations in case there
        # was a user error in setting the intervals so that it can be known as
        # soon as possible and nobody has to wait for it.
        if wait:
            print 'Waiting until start time:', _time.ctime(start)
            _time.sleep(start - _time.time())

        # The limit variable is the last integration that can be performed
        # before the retrieve_data function returns and exits.
        self.count = self.read_int('acc_num')
        if n_integ is not None:
            self.limit = self.count + n_integ

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
        prog_bof = not self.check_running()
        poco_bof = self.boffile

        if force_restart:
            print 'WARNING: Forcing a restart of the bof process.'
            self.progdev('')
            prog_bof = True

        # The ROACH2 has different initialization prcedures than the ROACH.
        if prog_bof:
            if self.model == 1:
                print 'Initializing bof process on FPGA.'
                self.progdev(poco_bof)
            elif self.model == 2:
                _os.system(' '.join(['adc16_init.rb', self.host, poco_bof]))
        else:
            print 'Bof process already running on FPGA.'
        if self.verbose:
            print 'bof process:', poco_bof
            print

        # Save some FPGA parameters.
        self.acc_len   = acc_len
        self.eq_coeff  = eq_coeff
        self.fft_shift = fft_shift
        self.insel     = insel
        self.int_time  = self.acc_len / SAMP_RATE

        # Write FPGA parameters to the ROACH
        if prog_bof:
            print 'Configuring pocket correlator.'
            if self.verbose:
                print '%-20s:\t%d' % ('acc_length', self.acc_len)
                print '%-20s:\t%d' % ('eq_coeff', self.eq_coeff)
                print '%-20s:\t%d' % ('ctrl_sw', self.fft_shift)
                print '%-20s:\t%d' % ('insel_insel_data', self.insel)
                print
            self.write_int('eq_coeff',         self.eq_coeff)
            self.write_int('ctrl_sw',          self.fft_shift)
            self.write_int('insel_insel_data', self.insel)

        # Return whether the bof file was started.
        return prog_bof

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
        print 'RPOCO%d: Closing UV file and renaming to %s.' % (ants, filename)
        _os.rename('TMP_FILE', filename)

    def uv_open(self):
        """
        This function opens a Miriad UV file for writing.
        """
        if self.model is None:
            raise RuntimeError('ROACH model not detected.')
        uv = _aipy.miriad.UV('TMP_FILE', status = 'new')
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
        uv['inttime'] = self.acc_len/self.samp_rate

        if self.bandpass is None:
            self.bandpass = _np.ones(BRAM_SIZE, dtype=_np.complex)
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
