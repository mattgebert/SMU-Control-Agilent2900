"""
Opens a communication port to the Agilent B2902A SMU using PyVISA over a TCP connection
"""
import threading
import time
import matplotlib.pyplot as plt
import AgilentB2902A

if __name__ == "__main__":
    # Connect & setup
    inst = AgilentB2902A.AgilentB2902A()
    inst.setup()
    ### Create a new thread
    new_thread = threading.Thread(target=inst.run_measurement, args=(
        #turn_on_time,  turn_on_voltage, delay, turn_off_voltage=0, meas_interval=0.005
        1, 0.8, 1, 0, 0.005
    ))
    
    new_thread.start()
    
    time.sleep(10)
    
    inst.stoptrigger = True
    
    new_thread.join()
    
    # get the data
    data = inst.datapoints
    
    # plot the data
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
    ax1.plot(data[:, 0], data[:, 1], label='Current (A)')
    ax1.set_ylabel('Current (A)')
    ax1.legend()
    ax2.plot(data[:, 0], data[:, 2], label='Voltage (V)', color='orange')
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Voltage (V)')
    ax2.legend()
    plt.show()
    