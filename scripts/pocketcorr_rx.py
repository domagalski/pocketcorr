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

import os
import glob
import time
import socket
import argparse
import threading
import pocketcorr
import multiprocessing as mp

ctrl_cmd_noargs = [
                   'bofkill',   # Kill the bof process.
                   'status',    # Get correlator status.
                   'start',     # Start writing data to disk.
                   'stop',      # Stop writing data to disk.
                  ]

ctrl_cmd_onearg = [
                   'bofstart',  # Start the bof process
                   'data_dir',  # Set the data directory
                   'fft_shift', # Set the fft shifting stage
                   'insel',     # Select the input sources
                  ]

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

CLIENT_PROMPT = bcolors.OKBLUE + 'poco> ' + bcolors.ENDC

def collect_data(roach, args, manager=None):
    """
    Open a UV file and read data into it.
    """
    if manager is not None:
        manager['writing'] = True
    if args.channels is None:
        roach.retrieve_data()
    else:
        channels = args.channels.split(',')
        if roach.model == 1:
            channels = map(int, channels)


        roach.retrieve_data(channels)

    if manager is not None:
        manager['writing'] = False

def ctrl_help():
    """
    Basic help message
    """
    helpstr = 'Available commands:'
    helpstr += '\n\tbofkill             Kill the bof process'
    helpstr += '\n\tbofstart [force]    Start the bof process'
    helpstr += '\n\tdata_dir [dir]      View or set the save directory'
    helpstr += '\n\tfft_shift <shift>   Set the FFT shifting stages'
    helpstr += '\n\tinsel <selector>    Select the input sources'
    helpstr += '\n\thelp                Show this help message'
    helpstr += '\n\treadout             Copy data from server to client'
    helpstr += '\n\tstatus              Get the correlator status'
    helpstr += '\n\tstart               Start writing data to disk'
    helpstr += '\n\tstop                Stop writing data to disk'
    return helpstr

def ctrl_msg(lock, queue):
    """
    Print messages from the correlator thread
    """
    lock.acquire()
    while True:
        print queue.get()
    lock.release()

def ctrl_poco(lock, queue, pipe, manager):
    """
    Read commands from the network and control the correlator
    """
    # Set up the message thread.
    msg_thread = threading.Thread(target=ctrl_msg, args=(lock, queue))
    msg_thread.daemon = True
    msg_thread.start()

    # Create the network socket to listen on.
    ctrl_port = 1420 # yeah, i'm using the hydrogen rest frequency for this.
    messenger = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    messenger.bind(('', ctrl_port))

    # Create a shell
    server = True
    netcat_shell = False
    netcat_prompt = '\n' + CLIENT_PROMPT
    while server:
        data, addr = messenger.recvfrom(1024)
        data = data.strip('\n').split()

        # Hitting enter while in netcat or ncat will bring up a prompt
        if not len(data):
            if netcat_shell:
                messenger.sendto(netcat_prompt[2:], addr)
            if not netcat_shell:
                netcat_shell = True
                pipe.send('status')
                _, status = pipe.recv()
                message = '# POCKETCORR NETCAT CLIENT\n'
                message += '# To view commands, type ? or help.\n'
                message += status + netcat_prompt
                messenger.sendto(message, addr)
            continue

        # Print help options
        if data[0] == 'help' or data[0] == '?':
            message = ctrl_help()
            if netcat_shell:
                message += netcat_prompt
            messenger.sendto(message, addr)
            continue

        # Create a TCP client to readout data
        if data[0] == 'readout':
            if netcat_shell:
                message = 'ERROR: use pocketcorr_shell.py for readout.'
                message += netcat_prompt
                messenger.sendto(message, addr)
            elif manager['writing']:
                message = 'ERROR: Cannot readout data while writing.'
                messenger.sendto(message, addr)
            elif ctrl_readout(manager['data_dir'], messenger, addr, ctrl_port):
                messenger.sendto('Error reading data from server.', addr)
            else:
                messenger.sendto('Done.', addr)
            continue

        # Exit the server if a shutdown command is received.
        if data[0] == 'kill-server':
            if addr[0] == '127.0.0.1' or addr[0] == 'localhost':
                pipe.send(data[0])
                server = False
            else:
                message = 'ERROR: Server can only be shutdown from localhost.'
                message += ' ' + str(addr)
                if netcat_shell:
                    message += netcat_prompt
                messenger.sendto(message, addr)
                continue

        # Send control commands to the correlator process
        if data[0] in ctrl_cmd_noargs and data[0]:
            pipe.send(data[0])
        elif data[0] in ctrl_cmd_onearg:
            pipe.send(data)

        # The scheduler requires some manipulation
        elif data[0] == 'schedule':
            scheduler = {k:v for k, v in map(lambda s: s.split('='), data[1:])}
            if scheduler.has_key('n_integ'):
                scheduler['n_integ'] = int(scheduler['n_integ'])
            pipe.send(('schedule', scheduler))

        # Error messages for invalid commands
        elif data[0] != 'kill-server':
            message = 'Invalid command: ' + data[0]
            if netcat_shell:
                message += netcat_prompt
            messenger.sendto(message, addr)
            continue

        # Get info back from the roach thread and send to the client
        error, message = pipe.recv()
        if error:
            server = True
            message = 'ERROR (' + data[0] + '): ' + message
        if netcat_shell and (data[0] != 'kill-server' or error):
            message += netcat_prompt
        messenger.sendto(message, addr)


def ctrl_readout(data_dir, messenger, udp_addr, ctrl_port):
    """
    This function uses TCP to copy data files from the server. The UDP
    socket is used for messages and progress updates.

    I did a quick test and it takes longer to compress an 87 MB uv file
    using tar on a raspberry pi than it does to scp the same file off of
    a raspberry pi, so this function does not compress data before
    reading the data over the network.
    """
    # Set up the TCP file transfer machine
    filedump = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    filedump.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    filedump.bind(('', ctrl_port))
    filedump.listen(1)
    messenger.sendto('Preparing data transfer.', udp_addr)
    tcp_conn, tcp_addr = filedump.accept()

    fnames = sorted(glob.glob(os.path.join(data_dir, '*.uv')))

    # Send information about how many files there are and receive ready signal
    sendrecv(tcp_conn, 'nfiles = ' + str(len(fnames)))

    # Time to dump the UV files to the client
    for fname in fnames:
        if tcp_send_uv(tcp_conn, fname):
            tcp_conn.close()
            filedump.close()
            return 1
    tcp_conn.close()
    filedump.close()
    return 0

def get_acclen(acc_len, nspec, int_time, samp_rate=200):
    """
    This function gets the number of clock cycles pre integration.
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
        return int(args[2] * samp_rate * 1e6 / fft_size) * fft_size
    else:
        return default

def get_filesize(filename):
    """
    Get the number of bytes in a file.
    """
    filedata = open(filename, 'rb')
    filedata.seek(0, 2)
    nbytes = filedata.tell()
    filedata.close()
    return nbytes

def get_interface(args):
    """
    This function gets the proper correlator interface.
    """
    # Start up the ROACH board
    if args.debug:
        roach = pocketcorr.FakeROACH('')
    elif pocketcorr.is_demux2(args.rpoco):
        roach = pocketcorr.POCOdemux2(args.ip, args.port)
    else:
        roach = pocketcorr.POCO(args.ip, args.port)
    return roach

def get_status(manager):
    """
    Create a status message.
    """
    if manager['progbof']:
        status = 'FPGA is programmed with the correlator.\n'
        status += 'Data collection is paused.'
    else:
        status = 'FPGA is not programmed.'
    return status

def run_poco(args, connection=None, queue=None, manager=None):
    """
    This function sets up the correlator, runs it, and collects data.
    """
    # Start up the ROACH board
    roach = get_interface(args)

    # Server setup
    if args.server:
        roach.mp_init(connection, queue)

    # Set up the correlator
    rx_setup_attr(roach, args)
    rx_setup_bof(roach, args)
    if args.server:
        manager['progbof'] = True
        manager['data_dir'] = roach.writedir

    # Read the data into UV files.
    if args.server:
        rx_loop(roach, args, manager)
        rx_cleanup(roach, args.keep_running)
    else:
        try:
            rx_loop(roach, args)
        except KeyboardInterrupt:
            print
            roach.uv_close()
        finally:
            rx_cleanup(roach, args.keep_running)

def rx_cleanup(roach, keep_running=False):
    """
    Cleanup for when data acquisition stops.
    """
    roach.cleanup()
    if keep_running:
        roach.log('Bof process will continue running.')
    else:
        roach.log('Killing bof process.')
        roach.progdev('')

def rx_cmd(roach, args, manager):
    """
    Receive commands from the controller and execute them.
    """
    command = roach.socket.recv()
    if command == 'bofkill':
        roach.log('Killing bof process: ' + roach.boffile, True)
        manager['progbof'] = False
        roach.progdev('')

    elif command[0] == 'bofstart':
        if len(command) > 1 and command[1] == 'force':
            args.force_restart = True
        else:
            args.force_restart = False
        roach.log('Starting bof process: ' + roach.boffile, True)
        rx_setup_bof(roach, args)
        args.force_restart = False
        manager['progbof'] = True

    elif command[0] == 'data_dir':
        if len(command) == 1:
            manager['data_dir'] = roach.writedir
            roach.socket.send((0, 'data_dir: ' + roach.writedir))
        else:
            data_dir = os.path.abspath(command[0])
            filename = os.path.basename
            err = roach.set_filename(os.path.join(data_dir, filename))
            if err:
                roach.socket.send((1, 'data_dir: cannot create directory.'))
            else:
                manager['data_dir'] = roach.writedir
                roach.socket.send((0, 'data_dir: new value set.'))

    elif command[0] == 'fft_shift' or command[0] == 'insel':
        if len(command) == 1:
            roach.socket.send((1, 'no value supplied.'))
            return True

        if command[1][:2] == '0b':
            base = 2
        elif command[1][:2] == '0x':
            base = 16
        else:
            base = 10
        try:
            shift = int(command[1], base)
        except ValueError:
            roach.socket.send((1, command[0] + ': invalid value.'))
            return True

        roach.log('Writing ' + command[0] + ': ' + bin(shift), True)
        if command[0] == 'fft_shift':
            roach.fft_shift = shift
            register = 'fft_shift'
        if command[0] == 'insel':
            roach.insel = shift
            register = 'insel_insel_data'
        roach.write_int(register, shift)

    elif command == 'kill-server':
        roach.log('Shutting down the control server.', True)
        return False

    elif command[0] == 'schedule':
        if not len(command[1]):
            roach.socket.send('ERROR: The scheduler needs parameters.')
            return True

        err, msg = roach.scheduler(no_run = True, **command[1])
        if err:
            roach.socket.send((1, err))
            return True

        retmsg = 'Running scheduler with parameters:\n'
        for k in command[1].keys():
            retmsg += k + ' = ' + str(command[1][k])
        roach.socket.send((0, retmsg))
        roach.scheduler(**command[1])
        collect_data(roach, args, manager)

    elif command == 'status':
        roach.log('Received status command from user.')
        roach.socket.send((0, get_status(manager)))

    elif command == 'start':
        roach.log('Received start command from user.')
        roach.socket.send((0, 'Starting data collection.'))
        collect_data(roach, args, manager)

    else:
        roach.socket.send((1, 'Invalid command: ' + str(command)))

    return True

def rx_loop(roach, args, manager=None):
    """
    This functions runs data aqcuisiton, either on a schedule or
    indefinitely until the user kills the script.
    """
    # Arguments that the looper needs
    stop     = args.stop_time
    start    = args.start_time
    n_integ  = args.num_integs
    interval = args.interval

    # Grab data from the correlator
    if args.server:
        while rx_cmd(roach, args, manager):
            pass
    else:
        roach.scheduler(n_integ, start, stop, interval)
        collect_data(roach, args)

def rx_setup_attr(roach, args):
    """
    This sets up data collection attributes for the correlator.
    """
    roach.check_connected()
    roach.set_verbose(args.verbose)
    roach.get_model(args.rpoco)
    roach.set_attributes(args.calfile, args.samp_rate*1e6, args.nyquist)
    if args.filename is not None:
        roach.set_filename(args.filename)

def rx_setup_bof(roach, args):
    """
    This function sets up the bof file.
    """
    # Setup arguments
    insel         = args.insel
    acc_len       = args.acc_len
    acc_spec      = args.acc_spec
    eq_coeff      = args.eq_coeff
    int_time      = args.int_time
    fft_shift     = args.fft_shift
    int_synth     = args.snap_synth
    samp_rate     = args.samp_rate
    synth_file    = args.synth_file
    force_restart = args.force_restart

    acc_len = get_acclen(acc_len, acc_spec, int_time, samp_rate)
    if int_synth and synth_file is not None:
        samp_rate = None
    if roach.start_bof(acc_len, eq_coeff, fft_shift, insel, force_restart,
                       int_synth, synth_file, samp_rate):
        roach.poco_init()
    else:
        roach.poco_recall()

def sendrecv(tcpsocket, message):
    """
    Send a message and block until a reply exists.
    """
    tcpsocket.send(message)
    return tcpsocket.recv(1024)

def tcp_send_uv(tcpsocket, filename):
    """
    Send a UV file with a TCP socket.
    """
    # Send filename information
    basename = os.path.basename(filename)

    # Get status from the client to determine whether to send the file
    cli_reply = sendrecv(tcpsocket, basename)
    if cli_reply == 'skip':
        return 0
    elif cli_reply == 'quit':
        return 1

    # Send the components of the UV file to the client
    fullpaths = sorted(glob.glob(os.path.join(filename, '*')))
    uvdata = ' '.join(map(os.path.basename, fullpaths))
    if sendrecv(tcpsocket, uvdata) == 'quit':
        return 1

    # Send each part of the UV file to the client
    bufsize = 64 << 20 # Read 64 MiB at a time
    uvsize = 4096 + sum(map(get_filesize, fullpaths))
    if sendrecv(tcpsocket, 'uvsize = ' + str(uvsize)) == 'quit':
        return 1
    for path in fullpaths:
        # Send the length of the file to the client
        nbytes = get_filesize(path)
        if sendrecv(tcpsocket, 'nbytes = ' + str(nbytes)) == 'quit':
            return 1

        # Quickly read and send the data to the client socket
        nchunks = nbytes / bufsize + bool(nbytes % bufsize)
        filedata = open(path, 'rb')
        try:
            for i in range(nchunks):
                chunk = filedata.read(bufsize)
                tcpsocket.send(chunk)
            filedata.close()

            if tcpsocket.recv(1024) == 'quit':
                return 1
        except socket.error:
            return 1

    # Exit with success
    return 0

if __name__ == '__main__':
    time_fmt = pocketcorr.TIME_FMT.replace('%', '%%')

    # Parse command-line options
    parser = argparse.ArgumentParser()
    ninteg = parser.add_mutually_exclusive_group()
    acclen = parser.add_mutually_exclusive_group()
    parser.add_argument('-i', '--ip', dest='ip', required=True,
                        help='IP address of Pocket Correlator')
    parser.add_argument('-r', '--rpoco',
                        required=True,
                        help=' '.join(['Pocket correlator model (rpoco8,',
                                       'rpoco8_r2, rpoco16)']))
    parser.add_argument('-C', '--channels',
                        help='Comma separated list of antennas to get data from.')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Debugging mode (ROACH data is simulated).')
    parser.add_argument('--server', action='store_true',
                        help='Run the receiver in server mode.')
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
                        default=200,
                        type=float,
                        help='The ADC sample rate that is being used in MHz.')
    parser.add_argument('--snap-synth', action='store_true',
                        help='Use the onboard synth (SNAP boards only).')
    parser.add_argument('--synth-file',
                        help='Synth configuration file (SNAP boards only.')
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

    if args.server:
        # Set up the multiprocessing communication devices.
        lock = mp.Lock()
        srv_queue = mp.Queue()
        srv_pipe, cmd_pipe = mp.Pipe()
        manager = mp.Manager().dict()
        manager['progbof'] = False
        manager['writing'] = False
        manager['data_dir'] = './'

        # Start the control thread
        ctrl_args = (lock, srv_queue, cmd_pipe, manager)
        ctrl = mp.Process(target=ctrl_poco, args=ctrl_args)
        #ctrl.daemon = True
        ctrl.start()

        # Start the correlator
        poco_args = (args, srv_pipe, srv_queue, manager)
        poco = mp.Process(target=run_poco, args=poco_args)
        poco.start()

        poco.join()
        ctrl.join()

    else:
        run_poco(args)
