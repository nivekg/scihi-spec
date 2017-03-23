import time
import struct
import corr
import argparse
import sys
import numpy as np
import cPickle as pickle

NCHANS = 512
ADC_CLK = 250e6

def get_data(r):
    """
    Return a dictionary of numpy data arrays, which may or may not be complex
    """
    rv = {}
    rv['xx']  = np.fromstring(r.read('xx', 8*NCHANS), dtype='>i8')
    rv['yy']  = np.fromstring(r.read('yy', 8*NCHANS), dtype='>i8')
    rv['xy']  = np.fromstring(r.read('xy_r', 8*NCHANS), dtype='>i8') + 1j*np.fromstring(r.read('xy_r', 8*NCHANS), dtype='>i8')
    return rv

def write_file(d, t, prefix='dat_poco_snap_simple'):
    fname = prefix + '-%s.pkl' % time.time()
    print 'Writing %s' % fname,
    t0 = time.time()
    with open(fname, 'w') as fh:
        pickle.dump({'data': d, 'times': t}, fh)
    t1 = time.time()
    print 'Done in %.2f seconds' % (t1-t0)
        

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--prog', action='store_true', default=False,
                        help='Use this flag to programthe FPGA (THIS SCRIPT DOES NOT DO ADC CALIBRATION)')
    parser.add_argument('-b', '--boffile', default='dual_input_poco_2017-03-22_1748.bof',
                        help='Which boffile to program')
    parser.add_argument('-f', '--fftshift', type=int, default=0xffff,
                        help='FFT shift schedule as an integer. Default:0xffff')
    parser.add_argument('-a', '--acc_len', type=int, default=2**20,
                        help='Number of spectra to accumulate. Default:2^20')
    parser.add_argument('-t', '--filetime', type=int, default=600,
                        help='Time in seconds of each data file. Default:600')
    parser.add_argument('-s', '--snap', default='10.10.10.101',
                        help='SNAP hostname of IP. Default:10.10.10.101')

    opts = parser.parse_args()


    #if len(args) == 0:
    #    print 'No SNAP hostname given. Usage: poco_snap_simple.py [options] <katcp_host>'

    print 'Connecting to %s' % opts.snap
    r = corr.katcp_wrapper.FpgaClient(opts.snap)
    time.sleep(0.05)

    if r.is_connected():
        print 'Connected!'
    else:
        print 'Failed to Connect!'
        exit()

    if opts.prog:
        print 'Trying to program with boffile %s' % opts.boffile
        print '(You probably don\'t want to do this -- this script won\'t configure the ADCs)'
        if opts.boffile in r.listbof():
            r.progdev(opts.boffile)
            print 'done'
        else:
            print 'boffile %s does not exist on server!' % opts.boffile
            exit()

    print 'FPGA board clock is', r.est_brd_clk()

    # Configure registers
    print 'Setting FFT shift to %x' % opts.fftshift
    r.write_int('fft_shift', opts.fftshift & 0xffff)
    print 'Checking for FFT overflows...'
    oflow = False
    for i in range(5):
        oflow = oflow or bool(r.read_int('fft_of'))
        time.sleep(1)
    if oflow:
        print 'Overflows detected -- consider increasing FFT shift'
    else:
        print 'No overflows detected'



    print 'Setting accumulation length to %d spectra' % opts.acc_len,
    print '(%.2f seconds)' % (opts.acc_len * 2 * NCHANS / ADC_CLK)
    r.write_int('acc_len', opts.acc_len)

    print 'Triggering sync'
    r.write_int('cnt_rst', 0)
    r.write_int('sw_sync', 0)
    r.write_int('sw_sync', 1)
    trig_time = time.time()
    r.write_int('sw_sync', 0)
    r.write_int('cnt_rst', 1)
    r.write_int('cnt_rst', 0)

    this_acc = 0
    this_acc_time = trig_time
    file_start_time = time.time()
    data  = []
    times = []
    while(True):
        try:
            latest_acc = r.read_int('acc_cnt')
            latest_acc_time = time.time()
            if latest_acc == this_acc:
                time.sleep(0.05)
            elif latest_acc == this_acc + 1:
                print 'Got %d accumulation after %.2f seconds' % (latest_acc, (latest_acc_time - this_acc_time))
                data  += [get_data(r)]
                times += [latest_acc_time]
                this_acc = latest_acc
                this_acc_time = latest_acc_time
                if time.time() > (file_start_time + opts.filetime):
                    write_file(data, times)
                    file_start_time = time.time()
                    data  = []
                    times = []
            else:
                print 'Last accumulation was number %d' % this_acc,
                print 'Next accumulation is number %d' % latest_acc,
                print 'Bad!'
                this_acc = latest_acc
                this_acc_time = latest_acc_time
        except KeyboardInterrupt:
            'Exiting'
            write_file(data, times)
            exit()
            




