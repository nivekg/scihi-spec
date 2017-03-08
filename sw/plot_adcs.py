import corr
import iadc
import time
import struct
import pylab

SNAPHOST = 'rpi3-2'
BOFFILE = 'extadc_snap_spec_2017-03-07_1741.bof'

print 'Connecting to', SNAPHOST
r = corr.katcp_wrapper.FpgaClient(SNAPHOST)
time.sleep(0.05)

print 'Programming with', BOFFILE
r.progdev(BOFFILE)

adc = iadc.Iadc(r)

# set up for dual-channel (non-interleaved) mode
adc.set_dual_input()

print 'Board clock is', r.est_brd_clk()

adc.set_data_mode()

xraw = r.snapshot_get('snapshot_ADC0', man_trig=True, man_valid=True)
x = struct.unpack('%db' % xraw['length'], xraw['data'])
yraw = r.snapshot_get('snapshot_ADC1', man_trig=True, man_valid=True)
y = struct.unpack('%db' % yraw['length'], yraw['data'])

pylab.figure()
pylab.subplot(2,1,1)
pylab.title('Channel 0')
pylab.plot(x[0:128])
pylab.subplot(2,1,2)
pylab.title('Channel 1')
pylab.plot(y[0:128])
pylab.show()


