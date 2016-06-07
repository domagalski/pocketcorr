#!/usr/bin/env python2

################################################################################
## This script sets up a shell to controll pocket correlators.
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
import sys
import time
import socket
import argparse

POCO_PORT = 1420
TCP_RECV_SIZE = 64 << 10
UDP_RECV_SIZE = 1024

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

SHELL_PROMPT = bcolors.OKBLUE + 'poco> ' + bcolors.ENDC

class POCOserver(socket._socketobject):
    def client_readout(self, localdir, tcp_addr):
        """
        Read data to disk. I did a quick test and it takes longer to
        compress an 87 MB uv file using tar on a raspberry pi than it
        does to scp the same file off of a raspberry pi, so this
        function does not compress data before readout.
        """
        # Connect to the client. The UDP send on the server sends after the TCP
        # server has been made
        tcp_cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        message, udp_addr = self.recvfrom(UDP_RECV_SIZE)
        if message[:5] == 'ERROR':
            print message
            return 1
        tcp_cli.connect(tcp_addr)

        # The server sends info about how many files there are as a string that
        # can be exec'd (nfiles = <number>)
        exec(recvsend(tcp_cli, 'ready')) # new variable nfiles

        # Read each file
        try:
            start_time = time.time()
            for i in range(nfiles):
                message = 'Receiving UV file %d/%d:' % (i+1, nfiles)
                print message,
                if tcp_recv_uv(tcp_cli, localdir, TCP_RECV_SIZE):
                    break
            print 'Total time:', round(time.time() - start_time, 1) / 60, 'min'
        except KeyboardInterrupt:
            tcp_cli.send('quit')
            print
            print 'ERROR: Aborting file transfer.'
        tcp_cli.close()
        return 0

    def exec_cmd(self, command, addr):
        """
        Send a command to the server and return the response.
        """
        self.sendto(command, addr)

        if command[:7] == 'readout':
            cmd = command.split()
            if len(cmd) > 1:
                local_dir = cmd[1]
            else:
                local_dir = os.getcwd()

            if self.client_readout(local_dir, addr):
                return

        try:
            message, _ = self.recvfrom(UDP_RECV_SIZE)
            return message
        except KeyboardInterrupt:
            print

def is_localhost(addr):
    """
    Determine if an IP is localhost.
    """
    return addr == '127.0.0.1' or addr == 'localhost'

def print_progress(step, total, prog_str='Percent complete:'):
    """
    Print the progress of some iteration through data. The step is the
    current i for i in range(total). This function can also display
    progress quietly by writing it to a file.

    Input:

    - ``step``: The iteration, starting at 0, of progress.
    - ``total``: Total number of iterations completed.
    - ``prog_str``: Message to print with the progress number.
    """
    progress = round(100 * float(step+1) / total, 2)
    progress = '\r' + prog_str + ' ' + str(progress) + '%\t\t'
    print progress,
    if step == total:
        print
    else:
        sys.stdout.flush()

def recvsend(tcpsocket, reply, bufsize=1024):
    """
    Recieve a message from the server and send a reply
    """
    message = tcpsocket.recv(bufsize)
    tcpsocket.send(reply)
    return message

def tcp_recv_uv(tcpsocket, output_dir, bufsize):
    """
    Copy a UV file using TCP.
    """
    start_time = time.time()

    # Create the UV file directory
    basename = tcpsocket.recv(1024)
    uvfile = os.path.join(output_dir, basename)
    print uvfile
    if os.path.exists(uvfile):
        if os.path.isdir(uvfile):
            print 'Skipping ' + uvfile + ': file exists.'
            tcpsocket.send('skip')
            return 0
        else:
            print 'ERROR: conflicting file: ' + uvfile
            tcpsocket.send('quit')
            return 1
    else:
        try:
            os.mkdir(uvfile)
        except OSError:
            print 'ERROR: Cannot create uv file: ' + uvfile
            tcpsocket.send('quit')
            return 1
    tcpsocket.send('ready')

    # This should be the same for every file, but I want this function
    # to work without that assumption
    uvnames = recvsend(tcpsocket, 'ready').split()
    exec(recvsend(tcpsocket, 'ready')) # new variable uvsize
    total_bytes_read = 4096 # Size of UV directory
    last_read = 0
    for name in uvnames:
        # Get the number of data chunks to be read out
        exec(recvsend(tcpsocket, 'ready')) # new variable nbytes
        nchunks = nbytes / bufsize + bool(nbytes % bufsize)

        # Write the file
        filedata = ''
        while len(filedata) != nbytes:
            filedata += tcpsocket.recv(bufsize)
            progress_len = total_bytes_read + len(filedata)
            if progress_len - last_read > (1 << 20) or progress_len == uvsize:
                print_progress(progress_len, uvsize)
                last_read = progress_len
        tcpsocket.send('next')

        total_bytes_read += len(filedata)

        filename = os.path.join(uvfile, name)
        with open(filename, 'wb') as f:
            f.write(filedata)

    read_time = time.time() - start_time

    # Create size formatting
    if uvsize < (1 << 10):
        read_size = uvsize
        size_unit = 'Bytes'
    elif uvsize < (1 << 20):
        read_size = uvsize / float(1 << 10)
        size_unit = 'KiB'
    elif uvsize < (1 << 30):
        read_size = uvsize / float(1 << 20)
        size_unit = 'MiB'
    else:
        read_size = uvsize / float(1 << 30)
        size_unit = 'GiB'

    # Create speed formatting
    uvspeed = uvsize / read_time
    if uvspeed < (1 << 10):
        read_speed = uvspeed
        speed_unit = 'Bytes/s'
    elif uvspeed < (1 << 20):
        read_speed = uvspeed / float(1 << 10)
        speed_unit = 'KiB/s'
    elif uvspeed < (1 << 30):
        read_speed = uvspeed / float(1 << 20)
        speed_unit = 'MiB/s'
    else:
        read_speed = uvspeed / float(1 << 30)
        speed_unit = 'GiB/s'

    # Print readout size/speed results.
    print 'Read', round(read_size, 1), size_unit, 'in', round(read_time, 1),
    print 's (' + str(round(read_speed, 1)), speed_unit
    return 0

if __name__ == '__main__':
    # Parse command-line options
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--ip', dest='ip', required=True,
                        help='IP address of pocketcorr server')

    args = parser.parse_args()

    # Open a socket to send/receive data
    poco = POCOserver(socket.AF_INET, socket.SOCK_DGRAM)
    poco_addr = (args.ip, POCO_PORT)

    # Print a welcome message
    print '# POCKETCORR'
    print '# Server: ' + poco_addr[0]
    print '# To view commands, type ? or help.'
    message = poco.exec_cmd('status', poco_addr)
    if message is not None:
        print message
        print

    # Run the shell
    while True:
        try:
            user_input = raw_input(SHELL_PROMPT).strip()
        # Ctrl-D
        except EOFError:
            print
            sys.exit(0)
        # Ctrl-C
        except KeyboardInterrupt:
            print
            continue

        # Determine whether to quit the shell
        if user_input in ['exit', 'logout', 'quit']:
            break

        # Go to the next inpit if the user enters nothing
        if not len(user_input):
            continue

        # Clear the terminal window
        if user_input == 'clear':
            sys.stderr.write("\x1b[2J\x1b[H")
            continue

        # This isn't even security, but whatever
        if user_input == 'kill-server':
            print 'ERROR: Cannot kill server from shell.'
            continue

        # Yeah, it's that easy
        message = poco.exec_cmd(user_input, poco_addr)
        if message is not None:
            print message
