#!/usr/bin/env python2

################################################################################
## This script is for generating instructions for the POCO input selector.
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

import sys
import argparse

def check_inputs(args, max_inputs):
    """
    This function checks that the inputs are valid and returns them.
    """
    nslice  = {'insel':16, 'delay': 8,  'seed': 4}[args['name']]
    shift   = 32 / nslice # Registers are 32-bits
    max_sel = (1 << shift) - 1

    # Check that no slice higher than
    selectors = []
    for i, c in enumerate(map(str, range(max_inputs))):
        if i >= nslice and args[c] or args[c] > max_sel:
            raise ValueError('Out of range.')
        else:
            selectors.append(args[c])

    return (nslice, shift, selectors)

if __name__ == '__main__':
    usage_str = ' '.join([sys.argv[0], '[-ant_num sel]'])
    description = ' '.join(['This script generates an integer that can be',
                            'written to the insel, delay, and seed software',
                            'registers on the pocket correlator. The inputs',
                            'that one can use in this function are the antenna',
                            'number and a number in [0, 1, 2, 3] that',
                            'instructs which input to use for that channel.',
                            'The possible inputs are the ADC input (0), noise',
                            'source 1 (1), noise source 2 (2), or a constant,',
                            '(3).'])
    parser = argparse.ArgumentParser(usage=usage_str, epilog=description)
    parser.add_argument('-n', '--name',
                        default='insel',
                        choices=['insel', 'delay', 'seed'],
                        metavar='reg',
                        help=' '.join(['Software register to generate the',
                                       'integer containing the instructions',
                                       '(insel, delay, seed).']))
    max_inputs = 16 # Maximum number of bit-slices available.
    for i in range(max_inputs):
        parser.add_argument('-' + str(i),
                            type=int,
                            default=0,
                            choices=range(1 << 8), # seed goes up to 8 bits.
                            metavar='sel',
                            help = argparse.SUPPRESS)

    # Get the arguments in the form of a dictionary and create the bits.
    nslice, shift, args = check_inputs(vars(parser.parse_args()), max_inputs)
    insel = 0
    for i in range(nslice):
        insel += args[i] << i*shift
    print insel
