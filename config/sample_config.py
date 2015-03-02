#!/usr/bin/env python2

# Sample configuration file. Edit as necessary.
config = {                      # This dictionary MUST be named 'config.'
    'ip':'10.0.1.4',            # IP Address of the ROACH
    'rpoco':'rpoco8',           # ROACH bof process
    'calfile':'psa898_v003',    # Calibration file
    'nyquist':2,                # Nyquist zone
    'port':7147,                # KATCP port
    'acc_len':1<<30,            # Accumulation length (integration time)
    'fft_shift':0x3ff,          # FFT Shift
    'eq_coeff':16,              # Equalizer coefficient
    'insel':0                   # Input selector
}
