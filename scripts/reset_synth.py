#!/usr/bin/env python2

import sys
import valon_synth as vs

def run_action(function, *args):
    """
    Send some command to the valon synth.
    """
    if not function(*args):
        raise RuntimeError('Unable to set synth.')

def reset_synth(tty_addr):
    """
    This function sets the default settings for the synth to use for
    the ROACH pocket correlator running at 200 MHz.

    freq: 200 MHz
    rf_level: 5 dBm
    """
    synth = vs.Synthesizer(tty_addr)
    run_action(synth.set_frequency, vs.SYNTH_A, 200.0)
    run_action(synth.set_frequency, vs.SYNTH_B, 200.0)
    run_action(synth.set_rf_level, vs.SYNTH_A, 5)
    run_action(synth.set_rf_level, vs.SYNTH_B, 5)
    run_action(synth.flash)
    print 'Synthesizer set to output 200 MHz at 5 dBm.'

if __name__ == '__main__':
    if len(sys.argv) > 1:
        reset_synth(sys.argv[1])
    else:
        reset_synth('/dev/ttyUSB0')
