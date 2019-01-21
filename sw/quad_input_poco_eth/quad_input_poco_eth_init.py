import time
import struct
import casperfpga
import argparse

NCHANS = 2048
ADC_CLK = 250e6

def str2ip(ip_str):
    """
    Given an IP sting, eg. '10.0.0.16',
    return it's integer representation, eg. 0x0a000010
    """
    octets = map(int, ip_str.split('.'))
    ip = (octets[0] << 24) + (octets[1] << 16) + (octets[2] << 8) + octets[3]
    return ip

def select_chans(chan_sel, n_bits):
    """
    output channens from the `chan_sel` array, in
    `n_bit` format.
    """
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--prog', action='store_true', default=False,
                        help='Use this flag to programthe FPGA (THIS SCRIPT DOES NOT DO ADC CALIBRATION)')
    parser.add_argument('-b', '--fpgfile', default='dual_input_poco_2017-03-22_1748.bof',
                        help='Which fpgfile to program')
    parser.add_argument('-f', '--fftshift', type=int, default=0xffff,
                        help='FFT shift schedule as an integer. Default:0xffff')
    parser.add_argument('-a', '--acc_len', type=int, default=2**20,
                        help='Number of spectra to accumulate. Default:2^20')
    parser.add_argument('-s', '--snap', default='10.10.10.101',
                        help='SNAP hostname of IP. Default:10.10.10.101')
    parser.add_argument('-i', '--dest_ip', default='10.0.0.100',
                        help='Destination IP. Default:10.0.0.100')
    parser.add_argument('-m', '--dest_mac', type=str, default="0x020304050607",
                        help='Destination MAC address. Must be specified as \
                              a hex string. Default:0x020304050607')
    parser.add_argument('-P', '--dest_port', type=int, default=10000,
                        help='Destination UDP port. Default:10000')
    parser.add_argument('-S', '--spec_per_packet', type=int, default=8,
                        help='Number of spectra per packet. Default:8')
    parser.add_argument('-B', '--bytes_per_spectra', type=int, default=128,
                        help='Number of valid bytes per packet. Default:128')

    opts = parser.parse_args()

    print 'Connecting to %s' % opts.snap
    r = casperfpga.CasperFpga(opts.snap, transport=casperfpga.KatcpTransport)
    time.sleep(0.05)

    if r.is_connected():
        print 'Connected!'
    else:
        print 'Failed to Connect!'
        exit()

    if opts.prog:
        print 'Trying to program with fpgfile %s' % opts.fpgfile
        print '(You probably don\'t want to do this -- this script won\'t configure the ADCs)'
        print 'TODO: see the spectrometer tutorial for details of how to calibrate SNAP\'s ADCs using casperfpga'
        r.upload_to_ram_and_program(opts.fpgfile)
        print 'done'

    print 'FPGA board clock is', r.estimate_fpga_clock()

    # Configure registers
    print 'Setting FFT shift to %x' % opts.fftshift
    r.write_int('pfb0_fft_shift', opts.fftshift & 0xffff)
    r.write_int('pfb1_fft_shift', opts.fftshift & 0xffff)
    print 'Checking for FFT overflows...'
    oflow = False
    for i in range(5):
        oflow = oflow or bool(r.read_int('pfb0_fft_of'))
        oflow = oflow or bool(r.read_int('pfb1_fft_of'))
        time.sleep(1)
    if oflow:
        print 'Overflows detected -- consider increasing FFT shift'
    else:
        print 'No overflows detected'



    print 'Setting accumulation length to %d spectra' % opts.acc_len,
    print '(%.2f seconds)' % (opts.acc_len * 2 * NCHANS / ADC_CLK)
    r.write_int('acc_len', opts.acc_len)

    print 'Reseting packetizer'
    r.write_int('output_rst', 1)
    r.write_int('gbe_output_en', 0)
    print 'Setting spectra per packet to %d' % opts.spec_per_packet
    r.write_int('output_ctrl_spec_per_pkt', opts.spec_per_packet)
    print 'Setting bytes per spectra to %d' % opts.bytes_per_spectra
    r.write_int('output_ctrl_bytes_per_spec', opts.bytes_per_spectra)
    print 'Setting 1GbE destination IP to %s' % opts.dest_ip
    r.write_int('gbe_output_dest_ip', str2ip(opts.dest_ip))
    print 'Setting 1GbE destination Port to %d' % opts.dest_port
    r.write_int('gbe_output_dest_port', opts.dest_port)
    #print 'Setting 1GbE destination Mac to 0x%x' % opts.dest_mac
    ## just set every available destination in the arp table to the same address for laziness
    mac = int(opts.dest_mac, 16)
    for i in range(256):
        r.write('gbe_output_one_gbe', struct.pack('>Q', mac), offset=0x3000 + 8*i)
    print 'Enabling 1GbE output core'
    r.write_int('gbe_output_en', 1)
    r.write_int('output_rst', 0) # will start sending on next sync

    print 'Triggering sync from a software trigger (NOT a GPS PPS). I think the time is:', time.ctime()
    r.write_int('cnt_rst', 0)
    r.write_int('sw_sync', 0)
    r.write_int('sw_sync', 1)
    trig_time = time.time()
    r.write_int('sw_sync', 0)
    r.write_int('cnt_rst', 1)
    r.write_int('cnt_rst', 0)



