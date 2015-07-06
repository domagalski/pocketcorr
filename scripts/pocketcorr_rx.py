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

import argparse
import pocketcorr

def get_acclen(acc_len, nspec, int_time, samp_rate=200e6):
    """
    This function
    """
    fft_size = 2048
    default = 1 << 30

    # at most, only one of these isn't None.
    args = [acc_len, nspec, int_time]
    if args[0] is not None:
        return args[0]
    elif args[1] is not None:
        return args[1] * 2048
    elif args[2] is not None:
        return int(args[2] * samp_rate / fft_size) * fft_size
    else:
        return default

if __name__ == '__main__':
    time_fmt = pocketcorr.TIME_FMT.replace('%', '%%')

    # Parse command-line options
    parser = argparse.ArgumentParser()
    ninteg = parser.add_mutually_exclusive_group()
    acclen = parser.add_mutually_exclusive_group()
    parser.add_argument('-i', '--ip', dest='ip',
                        help='IP address of Pocket Correlator')
    parser.add_argument('-r', '--rpoco',
                        required=True,
                        help=' '.join(['Pocket correlator model (rpoco8,',
                                       'rpoco8_r2, rpoco16, rpoco32)']))
    parser.add_argument('-C', '--channels',
                        help='Comma separated list of antennas to get data from.')
    parser.add_argument('-F', '--filename',
                        help='Filename base of the output UV files.')
    parser.add_argument('-t', '--start-time',
                        help=' '.join(['Time in localtime to start collecting',
                                       'integrations. Format: ' + time_fmt]))
    ninteg.add_argument('-T', '--stop-time',
                        help=' '.join(['Time in localtime to stop collecting',
                                       'integrations. Format: ' + time_fmt]))
    ninteg.add_argument('-N', '--num_integs',
                        type=int,
                        help='Total number of integrations to collect.')
    ninteg.add_argument('-I', '--interval',
                        help=' '.join(['Amount of time to run the correlator',
                                       'for. Format: U,time. Valid units:',
                                       'D (days), H (hours), M (minutes)']))
    parser.add_argument('-c', '--calfile',
                        default='psa898_v003',
                        help='Antenna calibration file (default: psa898_v003).')
    parser.add_argument('-f', '--force-restart',
                        action="store_true",
                        help=' '.join(['Force restarting the bof process if',
                                       'it is already running.']))
    parser.add_argument('-k', '--keep-running',
                        action="store_true",
                        help=' '.join(['Keep the pocket correlator bof process',
                                       'running after this script exits.']))
    parser.add_argument('-n', '--nyquist-zone',
                        dest='nyquist',
                        metavar='zone',
                        type=int,
                        default=2,
                        help=' '.join(['Nyquist zone to use (1, 2, ...).',
                                       'Defaults to 2.']))
    parser.add_argument('-p', '--port',
                        dest='port',
                        default=7147,
                        type=int,
                        help='Port to use with the ROACH katcp wrapper.')
    parser.add_argument('-S', '--samp-rate',
                        dest='samp_rate',
                        default=200e6,
                        type=float,
                        help='The ADC sample rate that is being used.')
    parser.add_argument('-s', '--fft-shift',
                        dest='fft_shift',
                        type=int,
                        default = 0x3ff,
                        help='fft shift. default value = 0x3ff')
    parser.add_argument('-e', '--eq-coeff',
                        dest='eq_coeff',
                        type=int,
                        default = 16,
                        help=' '.join(['Value of equalization coefficient.',
                                       'default value = 16']))
    parser.add_argument('--insel',
                        type=int,
                        default=0x00000000,
                        help=' '.join(['Input selection. Hex word where each',
                                       'hex value corresponds to an input type',
                                       'on the roach. 0 = adc, 1,2 = digital',
                                       'noise, 3 = digital zero.']))
    acclen.add_argument('-l', '--acc-len',
                        dest='acc_len',
                        type=int,
                        #default = 0x40000000,
                        help=' '.join(['acclen. default value=0x4000000 ->',
                                       '5.34sec. Acclen/samp_rate =',
                                       'integration time.']))
    acclen.add_argument('-L', '--acc-spec',
                        dest='acc_spec',
                        type=int,
                        #default=1<<19,
                        help='Number of spectra per integration.')
    acclen.add_argument('-A', '--int-time',
                        dest='int_time',
                        type=float,
                        #default=(1<<30)/200e6,
                        help='Accumulation time in seconds.')
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='Enable verbose mode.')
    args = parser.parse_args()

    ip            = args.ip
    port          = args.port
    stop          = args.stop_time
    rpoco         = args.rpoco
    start         = args.start_time
    n_integ       = args.num_integs
    verbose       = args.verbose
    calfile       = args.calfile
    nyquist       = args.nyquist
    acc_len       = args.acc_len
    acc_spec      = args.acc_spec
    eq_coeff      = args.eq_coeff
    filename      = args.filename
    interval      = args.interval
    int_time      = args.int_time
    fft_shift     = args.fft_shift
    samp_rate     = args.samp_rate
    insel         = args.insel
    keep_running  = args.keep_running
    force_restart = args.force_restart

    # Start up the ROACH board
    roach = pocketcorr.POCO(ip, port)
    roach.check_connected()
    roach.set_verbose(verbose)
    roach.get_model(rpoco)
    roach.set_attributes(calfile, samp_rate, nyquist)
    if filename is not None:
        roach.set_filename(filename)

    acc_len = get_acclen(acc_len, acc_spec, int_time, samp_rate)
    if roach.start_bof(acc_len, eq_coeff, fft_shift, insel, force_restart):
        roach.poco_init()
    else:
        roach.poco_recall()

    # Read the data into UV files.
    try:
        roach.scheduler(n_integ, start, stop, interval)
        roach.uv_open()
        if args.channels is None:
            roach.retrieve_data()
        else:
            channels = map(int, args.channels.split(','))
            roach.retrieve_data(channels)
    except KeyboardInterrupt:
        print
        roach.uv_close()
    finally:
        if args.keep_running:
            print 'Bof process will continue running.'
        else:
            print 'Killing bof process.'
            roach.progdev('')

