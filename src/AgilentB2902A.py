import pyvisa
import time
import datetime
import numpy as np

class AgilentB2902A:
    def __init__(self, address = "TCPIP::169.254.5.2::INSTR"):
        """
        Initializes the Agilent B2902A SMU communication.

        Parameters
        ----------
        address : str, optional
            The VISA address, by default "TCPIP::169.254.5.2::INSTR".
            Note that the manual specifies the address example as:
            "TCPIP::ww.xx.yy.zz::5025::SOCKET"
        """
        self.address = address
        # Software interrupt trigger
        self.stoptrigger = False
        
        # Connect
        self.connect(address)

    def connect(self, address = None):
        address = address or self.address
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(address)
        self.inst.timeout = 5000  # Set timeout to 5 seconds

    def write(self, command):
        self.inst.write(command)

    def query(self, command):
        return self.inst.query(command)

    def close(self):
        self.inst.close()
        
    def beep_up(self):
        self.write(":SYST:BEEP:STAT ON")
        self.write(":SYST:BEEP 800, 0.1")
        self.write(":SYST:BEEP 1000, 0.1")
        self.write(":SYST:BEEP 1200, 0.1")
        self.write(":SYST:BEEP 1600, 0.4")

    def beep_dn(self):
        self.write(":SYST:BEEP:STAT ON")
        self.write(":SYST:BEEP 1600, 0.1")
        self.write(":SYST:BEEP 1200, 0.1")
        self.write(":SYST:BEEP 1000, 0.1")
        self.write(":SYST:BEEP 800, 0.4")
        
    def reset(self):
        """
        Resets the instrument to its default state.
        """
        self.write("*RST")
        
    def setup(self, voltage=0, measurement_time=0.001):
        """
        Sets up the instrument for voltage sourcing and current measurement.

        Parameters
        ----------
        voltage : float, optional
            The voltage to set on the output, by default 0.
        """
        self.reset()
        # Setup the system date and time
        now = datetime.datetime.now()
        date = now.strftime("%Y,%m,%d")
        time = now.strftime("%H,%M,%S")
        self.write(f":SYST:DATE {date}")
        self.write(f":SYST:TIME {time}")
        # Set the output to voltage mode and configure the measurement settings
        self.write(":SOUR:FUNC VOLT")
        # Set the voltage level
        self.write(":SOUR:VOLT {}".format(voltage))
        # Set the measurement function to current
        self.write(":SENS:FUNC 'CURR'")
        # Set the measurement time
        self.write(f":SENS:CURR:APER {measurement_time:0.3f}")
        # Enable the output
        self.write(":OUTP ON")
        
    def measure(self):
        current = self.query(":meas:curr? (@1)")
        voltage = self.query(":meas:volt? (@1)")
        return (current, voltage)
    
    def run_measurement(self, 
                        turn_on_time, 
                        turn_on_voltage, 
                        delay, 
                        turn_off_voltage=0, 
                        meas_interval=0.005):
        """
        Starts the measurement process.
        """
        t0 = time.time()
        self.datapoints = []
        switched = False
        while not self.stoptrigger:
            # Do measurement routine here
            t = time.time() - t0
            # Check for switch on
            if not switched and t >= turn_on_time:
                self.write(f":sour:volt {turn_on_voltage}")
                # Finish with a beep
                self.beep_up()
                switched = True
            # Measurement
            current, voltage = self.measure()
            self.datapoints.append((t, current, voltage))
            
            # Delay between measurements
            time.sleep(meas_interval)
        
        # Perform stop measurement
        # Switch straight away
        self.write(f":sour:volt {turn_off_voltage}")
        self.beep_dn()
        
        t = time.time() - t0 # global time to record
        t1 = t # check the time since turnoff
        while t < t1 + delay:
            # Keep measuring
            t = time.time() - t0
            current, voltage = self.measure()
            self.datapoints.append((t, current, voltage))
            # Delay between measurements
            time.sleep(meas_interval)
        
        self.datapoints = np.array(self.datapoints, dtype=float)
            
        return self.datapoints