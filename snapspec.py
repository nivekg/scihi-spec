#!/usr/bin/python
import corr,time,struct,sys,logging,pylab
import matplotlib.pyplot as plt
import os
import sys
import numpy as np
bitstream = 'snap_spectrometer_2015-10-23_1433.bof'
katcp_port=7147

def exit_fail():
	print 'FAILURE DETECTED. Log entries:\n',lh.printMessages()
	try:
		fpga.stop()
	except: pass
	raise
	exit()

def get_data():
	#acc_n = fpga.read_uint('acc_cnt')
	pol0 = np.array(struct.unpack('>2048Q', fpga.read('pol0',2048*8,0)))
	pol1 = np.array(struct.unpack('>2048Q', fpga.read('pol1',2048*8,0)))
	real = np.array(struct.unpack('>2048q', fpga.read('real',2048*8,0)))
	imaginary = np.array(struct.unpack('>2048q', fpga.read('imaginary',2048*8,0)))
	print(len(pol0))
	#print(pol0[0])
	#print(pol0[1])
	
	return pol0,pol1,real+1j*imaginary

def plot_spectrum():
	
	pol0, pol1, crossmult = get_data()
	
	freq = np.arange(0,250,.1220703125)
	plt.subplot(311)
	plt.plot(freq,pol0,'r')
	plt.subplots_adjust(hspace = 1.2)
	plt.xlabel('frequency(MHz)')
	plt.ylabel('Power')
	plt.title('Power Spectra of pol0')
	plt.subplot(312)
	plt.plot(freq,pol1,'k')
	plt.title('Power Spectra of pol1')
	plt.xlabel('frequency(MHz)')
	plt.ylabel('Power')
	plt.subplot(313)
	plt.plot(freq,np.angle(crossmult),'b')
	plt.title('Crossmult angle signal')
	plt.ylabel('Phase(radians)')
	plt.xlabel('frequency(MHz)')
	plt.show()
if __name__ == '__main__':
	from optparse import OptionParser
	

	p = OptionParser()
	p.set_usage('spectrometer.py <SNAP_HOSTNAME_or_IP> [options]')
	p.set_description(__doc__)
	p.add_option('-l', '--acc_len', dest='acc_len', type='int',default=2*(2**28)/2048,
		help='Set the number of vectors to accumulate between dumps. default is 2((2^28)/2048, or just under 2 seconds.')
	p.add_option('-s', '--skip', dest='skip', action='store_true',
		help='Skip reprogramming the FPGA and configuring EQ.')
	p.add_option('-b', '--bof', dest='boffile',type='str', default='',
		help='Specify the bof file to load')
	opts, args = p.parse_args(sys.argv[1:])

	if args==[]:
		print 'Please specify a SNAP board. Run with the -h flag to see all options.\nExiting.'
		exit()
	else:
		snap = args[0]
	if opts.boffile != '':
		bitstream = opts.boffile


logger = []
lh = corr.log_handlers.DebugLogHandler()
logger = logging.getLogger(snap)
logger.addHandler(lh)
logger.setLevel(10)

print('Connecting to server %s on port %i... '%(snap,katcp_port)),
fpga = corr.katcp_wrapper.FpgaClient(snap, katcp_port, timeout=10, logger=logger)
time.sleep(1)

if fpga.is_connected():
	print 'ok\n'
else:
	print 'ERROR connecting to server %s on port %i. \n' %(roach,katcp_port)
	exit_fail()



print '-------------------'
print 'Configuring accumulation period...'
fpga.write_int('acc_len', opts.acc_len)
fpga.write_int('fft_shift', 0xFFFFFFFF)
print 'done'

time.sleep(2)


plot_spectrum()





















