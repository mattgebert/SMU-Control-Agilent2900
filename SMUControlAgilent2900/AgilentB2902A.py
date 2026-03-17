"""Class to control the Agilent B2902A SMU using PyVISA over a TCP connection."""

import pyvisa
import time
import datetime
import numpy as np
import numpy.typing as npt
from enum import StrEnum


class AgilentB2902A:
    """
    Class to control the Agilent B2902A SMU using PyVISA over a TCP connection.

    This class provides methods to connect to the instrument, set source and sense modes,
    perform measurements, and run timed measurement routines.

    Parameters
    ----------
    address : str, optional
        The VISA address to connect to, by default "TCPIP::169.254.5.2::INSTR".
    sounds : bool, optional
        Whether to play sounds on connect/disconnect, by default True.

    Attributes
    ----------
    address : str
        The VISA address of the instrument.
    stoptrigger : bool
        A software interrupt trigger to stop timed measurement routines.
    source : mode
        The current source mode (VOLT or CURR).
    sense : mode
        The current sense mode (VOLT or CURR).
    sounds : bool
        Whether to play sounds on connect/disconnect and other actions.
    """

    class mode(StrEnum):
        """Enum for source and sense modes."""

        VOLT = "VOLT"
        CURR = "CURR"

    def __init__(self, address: str = "TCPIP::169.254.5.2::INSTR", sounds: bool = True):
        """
        Initialize the Agilent B2902A SMU communication.

        Parameters
        ----------
        address : str, optional
            The VISA address, by default "TCPIP::169.254.5.2::INSTR".
            Note that the manual specifies the address example as:
            "TCPIP::ww.xx.yy.zz::5025::SOCKET".
        sounds : bool, optional
            Whether to play sounds on connect/disconnect, by default True.
        """
        self.address = address
        # Software interrupt trigger
        self.stoptrigger = False

        # Setup the internal state
        self.source: AgilentB2902A.mode = AgilentB2902A.mode.VOLT
        self.sense: AgilentB2902A.mode = AgilentB2902A.mode.CURR
        self.sounds = sounds

        # Connect
        self.connect(address)

        # Reset the instrument to a known state
        self.reset()
        # Setup the system date and time
        now = datetime.datetime.now()
        date = now.strftime("%Y,%m,%d")
        time = now.strftime("%H,%M,%S")
        self.write(f":SYST:DATE {date}")
        self.write(f":SYST:TIME {time}")

        # Beep to indicate initialization is complete
        if self.sounds:
            self.beep_up()

    def connect(self, address=None):
        """
        Connect to the instrument using the specified VISA address.

        Parameters
        ----------
        address : str, optional
            The VISA address to connect to, by default None (uses self.address).
        """
        address = address or self.address
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(address)
        self.inst.timeout = 5000  # Set timeout to 5 seconds

    def write(self, command: str):
        """
        Write a command to the instrument.

        Parameters
        ----------
        command : str
            The command to send to the instrument.
        """
        self.inst.write(command)

    def query(self, command: str) -> str:
        """
        Query the instrument and returns the response.

        Parameters
        ----------
        command : str
            The command to send to the instrument.

        Returns
        -------
        str
            The response from the instrument.
        """
        return self.inst.query(command)

    def close(self):
        """
        Close the connection to the instrument.
        """
        if self.sounds:
            self.beep_dn()
        self.inst.close()

    def beep(self, frequency=1000, duration=0.1):
        """
        Play a beep sound with the specified frequency and duration.

        Parameters
        ----------
        frequency : int, optional
            The frequency of the beep in Hz, by default 1000.
        duration : float, optional
            The duration of the beep in seconds, by default 0.1.
        """
        self.write(":SYST:BEEP:STAT ON")
        self.write(f":SYST:BEEP {frequency}, {duration}")

    def beep_up(self):
        """
        Play a beep sound to indicate an action (e.g., turning on output).
        """
        self.write(":SYST:BEEP:STAT ON")
        self.write(":SYST:BEEP 800, 0.1")
        self.write(":SYST:BEEP 1000, 0.1")
        self.write(":SYST:BEEP 1200, 0.1")
        self.write(":SYST:BEEP 1600, 0.4")

    def beep_dn(self):
        """
        Play a beep sound to indicate an action (e.g., turning off output).
        """
        self.write(":SYST:BEEP:STAT ON")
        self.write(":SYST:BEEP 1600, 0.1")
        self.write(":SYST:BEEP 1200, 0.1")
        self.write(":SYST:BEEP 1000, 0.1")
        self.write(":SYST:BEEP 800, 0.4")

    def reset(self):
        """
        Reset the instrument to its default state.
        """
        self.write("*RST")

    def set_source(
        self, func: "AgilentB2902A.mode", amplitude: float | int | None = None
    ):
        """
        Set the source function of the instrument.

        Parameters
        ----------
        func : SourceFunction
            The source function to set (VOLT or CURR).
        amplitude : float or int, optional
            The amplitude to set for the source function, by default None (no change).
        """
        self.source = func
        self.write(f":SOUR:FUNC {func.value}")
        if amplitude is not None:
            if func == AgilentB2902A.mode.VOLT:
                self.write(f":SOUR:VOLT {amplitude}")
            elif func == AgilentB2902A.mode.CURR:
                self.write(f":SOUR:CURR {amplitude}")
        if self.sounds:
            self.beep_up()

    def set_output(self, on: bool):
        """
        Set the output state of the instrument.

        Parameters
        ----------
        on : bool
            True to turn on the output, False to turn it off.
        """
        self.write(f":OUTP {'ON' if on else 'OFF'}")
        if self.sounds:
            self.beep_up() if on else self.beep_dn()

    def set_sense(
        self, func: "AgilentB2902A.mode", measurement_time: float | int | None = None
    ):
        """
        Set the sense function of the instrument.

        Parameters
        ----------
        func : SourceFunction
            The sense function to set (VOLT or CURR).
        measurement_time : float or int, optional
            The measurement time (aperture) to set for the sense function, by default None (no change).
        """
        self.write(f":SENS:FUNC {func.value}")
        self.sense = func
        if measurement_time is not None:
            # Note, the two values (VOLT/CURR:APER) are tied together.
            self.write(f":SENS:{func.value}:APER {measurement_time:0.3f}")
        if self.sounds:
            self.beep_up()

    def setup_IV_measurement(self, voltage=0, measurement_time=0.001):
        """
        Set up the instrument for voltage sourcing and current measurement.

        Parameters
        ----------
        voltage : float, optional
            The voltage to set on the output, by default 0.
        measurement_time : float, optional
            The measurement time (aperture) to set for the current measurement, by default 0.001 (1 ms).
        """
        self.sounds = False
        self.set_source(AgilentB2902A.mode.VOLT, voltage)
        self.set_sense(AgilentB2902A.mode.CURR, measurement_time)

    def measure(self):
        """
        Perform a single measurement of voltage and current.

        Returns
        -------
        voltage : float
            The measured voltage.
        current : float
            The measured current.
        """
        current = self.query(":meas:curr? (@1)")
        voltage = self.query(":meas:volt? (@1)")
        return (voltage, current)

    def run_timed_electrochemical_measurement(
        self,
        turn_on_time,
        turn_on_voltage,
        delay: float | int = 0,
        turn_off_voltage: float | int = 0,
        meas_interval: float | int = 0.005,
    ):
        """
        Start a transient gating measurement routine.

        The output voltage is switched on after a `turn_on_time`.
        Measurements are made at regular intervals until AgilentB2902A.stoptrigger is set to True,
        at which point the output voltage is switched off and measurements continue for a further `delay` seconds.
        and then switched off after a `delay`, while continuously measuring the current and voltage.

        Parameters
        ----------
        turn_on_time : float
            Time in seconds after which the output voltage is switched on.
        turn_on_voltage : float
            The voltage to set when switching on the output.
        delay : float, optional
            Time in seconds to continue measurements after switching off the output, by default 0.
        turn_off_voltage : float, optional
            The voltage to set when switching off the output, by default 0.
        meas_interval : float, optional
            Time in seconds between measurements, by default 0.005 (5 ms).

        Returns
        -------
        np.ndarray
            A NumPy array containing the measurement data.
            First index is measurement index,
            second index is data type:
                - 0=time,
                - 1=current measured,
                - 2=voltage measured.
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

        t = time.time() - t0  # global time to record
        t1 = t  # check the time since turnoff
        while t < t1 + delay:
            # Keep measuring
            t = time.time() - t0
            current, voltage = self.measure()
            self.datapoints.append((t, current, voltage))
            # Delay between measurements
            time.sleep(meas_interval)

        self.datapoints = np.array(self.datapoints, dtype=float)

        return self.datapoints

    def run_timed_IV_measurement(
        self,
        voltages: list[float | int] | npt.NDArray[np.floating],
        meas_interval: float | int = 0.1,
        settle_time: float | int = 0.1,
    ) -> np.ndarray:
        """
        Start an IV measurement routine.

        Parameters
        ----------
        voltages : list of float
            A list of voltages to set sequentially on the output.
        meas_interval : float, optional
            Time in seconds between measurements, by default 0.1 (100 ms).
            The agilent gate time is set to 0.8*meas_interval (i.e. 80 ms for the default).
        settle_time : float, optional
            Time in seconds to wait after setting each voltage before starting measurements, by default 0.1.

        Returns
        -------
        np.ndarray
            A NumPy array containing the measurement data.
            First index is measurement index,
            second index is data type:
                - 0=time,
                - 1=voltage set,
                - 2=current measured,
                - 3=voltage measured.
        """
        t0 = time.time()
        self.datapoints = []

        # Set the voltage to the first value in the list
        presound = self.sounds
        self.sounds = False
        self.set_sense(AgilentB2902A.mode.CURR, meas_interval * 0.8)
        self.set_source(AgilentB2902A.mode.VOLT, voltages[0])
        self.sounds = True if presound else False
        self.set_output(True)

        # Now loop through the voltages and perform measurements
        for i, voltage in enumerate(voltages):
            self.sounds = False
            self.set_source(AgilentB2902A.mode.VOLT, voltage)
            # Wait the settle time before starting measurements
            t_set = time.time()
            """The time from setting the voltage"""
            t_current = time.time() - t_set
            """Time since voltage set"""
            # Add 2 seconds to the first voltage to allow for
            # large initial transient change
            while t_current < (settle_time if i > 0 else settle_time + 2):
                t_current = time.time() - t_set
                time.sleep(0.01)  # Sleep briefly to avoid busy waiting
            # Now perform a measurement
            t_meas = time.time() - t0
            """Time since start of routine"""
            vmeas, imeas = self.measure()
            self.datapoints.append((t_meas, voltage, imeas, vmeas))
            if presound:
                self.beep(100, 0.05)

        self.datapoints = np.array(self.datapoints, dtype=float)
        # Restore the original sound setting
        self.sounds = presound

        return self.datapoints
