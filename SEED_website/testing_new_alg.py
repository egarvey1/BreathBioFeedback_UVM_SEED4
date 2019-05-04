# Import all packages that are used
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import mysql.connector
import transformations as tf
from statistics import mean
import csv
from pymetawear.discover import select_device
from pymetawear.client import MetaWearClient
from mbientlab.metawear.cbindings import SensorFusionData, SensorFusionGyroRange, SensorFusionAccRange, SensorFusionMode
import time
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from functools import partial
import numpy as np
import threading
import board
import busio

"""These are important constant parameters
They can be adjusted to detect different types of gups and inhale/exhales
S = slope
UB = upper boundary for error
LB = lower boundary for error
"""
SIZE_PACKET = 33
INHALE_SLOPE_THRESH = 0.004
EXHALE_SLOPE_THRESH = 0.004
RAD_CONV = 180 / 3.14159

S1_LB = -20.5
S1_UB = -2.75

S2_LB = -6.5
S2_UB = 6.5

S3_LB = -1 * S1_UB
S3_UB = -1 * S1_LB


def best_fit_slope(xs, ys):
    """A helper function for finding the best fit slope given an array of x and y values

        Parameters
        ----------
        xs, ys : np.array()
            The x and y array values to be fit to a linear line of best fit, respectively

        Returns
        -------
        m: float
            The slope of the line of best fit
        """
    m = (((mean(xs) * mean(ys)) - mean(xs * ys)) /
         ((mean(xs) * mean(xs)) - mean(xs * xs)))
    return m


def check_if_gup(data_chunk):
    """The check_if_gup function takes an input array of rotational IMU data (specifically roll euler angle)
    and determines if a gup exists within that dataset by comparing it to previously defined gup waveform data

        Parameters
        ----------
        data_chunk : list
            The chunk of data to be tested

        Returns
        -------
        boolean
            the T/F value of the input data array
        """
    # Section the array into 3 shapes
    section_1 = np.reshape(np.array(data_chunk[0:4]), (4,))
    section_2 = np.reshape(np.array(data_chunk[4:7]), (3,))
    section_3 = np.reshape(np.array(data_chunk[7:]), (4,))

    # Get the line of best fit for these data entries
    s1_slope = best_fit_slope2(section_1)
    s2_slope = best_fit_slope2(section_2)
    s3_slope = best_fit_slope2(section_3)

    # Follows the conditional statements and error ranges to determine gup validity
    if (s1_slope > S1_LB and s1_slope < S1_UB):
        if (s2_slope > S2_LB and s2_slope < S2_UB):
            if (s3_slope > S3_LB and s3_slope < S3_UB):
                return True

    else:
        return False


def best_fit_slope2(ys):
    """The best_fit_slope2 function is identical to that of the best_fit_slope function above except
    that it does not require an xs input for equally spaced data where the x axis is arbitrary (example our time
    data)

           Parameters
           ----------
           ys : np.array()
               The y values to be evaluated for line of best fit

           Returns
           -------
           m: float
               The line of best fit slope
           """
    xs = np.linspace(0.1, 1, num=len(ys))

    m = (((mean(xs) * mean(ys)) - mean(xs * ys)) /
         ((mean(xs) * mean(xs)) - mean(xs * xs)))

    return m


class MbientFusion():
    """The MbientFusion class is meant to allow easy access to the Mbient IMU extended Kalman Filter Fusion data

           Parameters
           ----------
           address : str, optional
               The IP address of the particular IMU.  If no value is passed a menu will appear to choose a device

           """

    def __init__(self, address=None):
        if address == None:
            address = select_device()

        self.c = MetaWearClient(str(address), debug=True)

        time.sleep(1.0)
        # Setting the IMU to IMU Plus fusion mode which according to research is the most applicable to our products needs
        self.c.sensorfusion.set_mode(SensorFusionMode.IMU_PLUS)
        time.sleep(1.0)

        # Initialize the accel (a) and gyro (g) data
        self.a_value = [0, 0, 0]
        self.g_value = [0, 0, 0]

    def stop(self):
        # Stops the stream of IMU data properly (crucial!)
        self.c.sensorfusion.notifications(None)
        time.sleep(5.0)
        self.c.disconnect()

    def handle_acc_notifications(self, data):
        xyz = data["value"]
        self.a_value = [xyz.x, xyz.y, xyz.z]

    def handle_gyro_notifications(self, data):
        xyz = data["value"]

    def handle_quat_notifications(self, data):
        xyz = data["value"]
        self.quat_value = [xyz.w, xyz.x, xyz.y, xyz.z]
        # Get the Euler angles from the quaternion
        euler = tf.euler_from_quaternion(self.quat_value)
        # Converted the euler angles from radians to degrees
        in_rad = [val * RAD_CONV for val in euler]
        self.g_value = in_rad

    def start(self):
        # Starts the stream of IMU data by initializing the accel, quaternion and gyro notifications
        self.c.sensorfusion.notifications(
            corrected_acc_callback=partial(self.handle_acc_notifications),
            quaternion_callback=partial(self.handle_quat_notifications),
            corrected_gyro_callback=partial(self.handle_gyro_notifications))


class MbientAccel():
    """The MbientAccel class is identical to the MbientFusion Class except that it utilizes pure output data from
    the gyros and accels without any sensor fusion.  We do NOT use this in our application but I will keep it incase it
    it needed for future iterations

               Parameters
               ----------
               address : str, optional
                   The IP address of the particular IMU.  If no value is passed a menu will appear to choose a device

               """

    def __init__(self, address=None, random=True):
        self.random = random

        if self.random == False:
            if address == None:
                address = select_device()

            #        print(address)
            self.c = MetaWearClient(str(address), debug=True)

            time.sleep(1.0)
            self.c.accelerometer.set_settings(data_rate=200, data_range=4.0)
            time.sleep(1.0)
            self.c.accelerometer.high_frequency_stream = True
            time.sleep(1.0)
            self.c.gyroscope.set_settings(data_rate=200)
            time.sleep(1.0)
            self.c.gyroscope.high_frequency_stream = True
            self.a_value = [0, 0, 0]
            self.g_value = [0, 0, 0]

    def stop(self):
        if self.random == False:
            self.c.accelerometer.notifications(None)
            time.sleep(2.0)
            self.c.gyroscope.notifications(None)
            time.sleep(5.0)
            self.c.disconnect()

    def handle_acc_notifications(self, data):
        xyz = data["value"]
        self.a_value = [xyz.x, xyz.y, xyz.z]

    def handle_gyro_notifications(self, data):
        xyz = data["value"]
        self.g_value = [xyz.x, xyz.y, xyz.z]

    def start(self):
        if self.random == False:
            print("Subscribing to accel")
            self.c.accelerometer.notifications(lambda data: self.handle_acc_notifications(data))
            print("Subscribing to gyro")
            self.c.gyroscope.notifications(lambda gdata: self.handle_gyro_notifications(gdata))


class Sensor(threading.Thread):
    """The Sensor CLass is kept generic to allow any analog device to be connected to the ADC on the Pi

               Parameters
               ----------
               channel : int
                   The channel that the sensor is connected to on the ADC

               """

    def __init__(self, channel):
        threading.Thread.__init__(self)
        self.thread_stop = False

        self.GAIN = 1
        self.channel = channel

        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS.ADS1115(self.i2c, gain=self.GAIN)
        self.chan = AnalogIn(self.ads, ADS.P0, ADS.P1)

        self.value = self.chan.voltage

    def stop(self):
        self.thread_stop = True
        self.join()

    def update_value(self):
        self.value = self.chan.voltage

    #        print(self.value)
    def run(self):
        #        try:
        while not self.thread_stop:
            self.update_value()


#            time.sleep(.1)

class RecordToDatabase(threading.Thread):
    """The RecordToDatabase class is an extension of the threading class to allow for multiple processes to happen
    simultaneously.  This class controls the committing of sensor values to the main databases and to the gup_status
    database.  It is the brains behind our operation

               Parameters
               ----------
               accel : Object of the MbientFusion class
                  MBientFusion IMU class object that is initialized upon calling start
                band: Object of the Sensor class
                    The Sensor class is initialized upon calling start

               """

    def __init__(self, accel, band):
        threading.Thread.__init__(self)
        self.thread_stop = False

        self.accel = accel
        self.band = band

        self.cnx = None
        self.connect = None
        self.look_for_gups = False

        self.initialize_sensors()

        # Allows us to collect data samples for later processing
        self.file = open("sample_gups.csv", 'w')
        self.csv_writer = csv.writer(self.file, delimiter=',')
        self.csv_writer.writerow(['time', 'a_x', 'a_y', 'a_z', 'g_x', 'g_y', 'g_z', 'band'])

    def stop(self)
        """The stop function safely ends all processes across all sensors and joins threads as necessary            
            """
        self.thread_stop = True
        print("Stopping Gracefully")
        self.accel.stop()
        self.band.stop()
        self.file.close()

        try:  # throws an exception if they are already committed
            self.cnx.commit()
            self.cursor.close()
            self.cnx.close()
        except:
            pass

    def initialize_sensors(self):
        """The Initialize sensors function properly starts all of the sensor threads.
                   """
        self.accel.start()
        self.band.start()

    def write_to_db(self):
        """The write to db function will write all values to the database
                   """
        self.cnx, self.cursor = self.open_database('band_and_1accel')

        add_data_entry = "INSERT INTO `all_data` (`timestamp`, `a_x`, `a_y`, `a_z`, `g_x`, `g_y`, `g_z`, `voltage`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s);"
        add_status_entry = "INSERT INTO `gup_status` (`timestamp`, `gup_status`, `breath_in_status`, `breath_out_status`) VALUES (%s,%s,%s,%s);"

        # Get Time
        now = time.time()  # datetime.datetime.now().strftime("%S.%f")

        # Get Band Info.
        voltage = self.read_band_value()
        a_x, a_y, a_z, g_x, g_y, g_z = self.read_accel_value()

        # Write values to the csv if desired
        self.csv_writer.writerow([now, a_x, a_y, a_z, g_x, g_y, g_z, voltage])

        # Get previous data as well
        previous_data = self.get_previous_data()

        # If no previous data exists, initialize the database with all zeros (nothing is happening)
        if previous_data != False:
            # If previous data exists, check if the user is breathing or gupping or nether
            status = self.evaluate_model(previous_data, [a_x, a_y, a_z, g_x, g_y, g_z, voltage])
        else:  # there is not enough previous data to go off of
            status = [0, 0, 0, 0, 0]

        entry_data = (now, a_x, a_y, a_z, g_x, g_y, g_z, voltage)

        # Add the timestamp and relevant boolean data (gup, breath in, breath out) data to db
        entry_status = (now, status[4], status[0], status[1])

        # Commit the data
        self.cursor.execute(add_data_entry, entry_data)
        self.cursor.execute(add_status_entry, entry_status)

        # Close the database
        self.close_database()

        # Delay sometime
        time.sleep(0.01)

    def run(self):
        # This is the inherited thread function that is overwritten.  Essentially it drives all of the processes
        while not self.thread_stop:
            self.write_to_db()

    def open_database(self, database):
        # This function connects to the existing database
        # It creates the cursor and connection objects
        cnx = mysql.connector.connect(user='egarvey', \
                                      password='dreamteam', \
                                      database=database)
        # Create cursor, that executes commands
        cursor = cnx.cursor()
        return cnx, cursor

    def close_database(self):
        # This function closes the database properly
        self.cnx.commit()
        self.cursor.close()
        self.cnx.close()

    def evaluate_model(self, prev_data, new_data):
        """The evaluate model function concatenates old and new data togetehr and determines if what the user is doing
        (breathing in, out or gupping)

                   Parameters
                   ----------
                   prev_data : list
                       previous ~30 datapoints from the band and IMU
                   new_data: list
                        the newest datapoint to be concatenated with the old data

                   """
        prev_data = np.array(prev_data)
        data = np.array(np.append(prev_data, [new_data], axis=0))
        breath_data = data[:, 6]

        # print("All data: ", data)
        if self.look_for_gups != True:
            breath_result = self.detect_breath(breath_data)
            # print("Returned result: ", breath_result)

            if breath_result[0] == 1:  # if inhale detected
                # print("Breath in detected")
                return [1, 0, 0, 0, 0]  # return that we are still inhaling

            elif breath_result[1] == 1:
                # print("Breathe out detected")
                return [0, 1, 0, 0, 0]
            else:  # a local maxima or minima
                x_array = np.array(range(0, len(breath_data[-20:-5])))
                slope = best_fit_slope(x_array, breath_data[-20:-5])
                print(slope)

                self.look_for_gups = True


        else:
            is_gup = self.detect_gup(data[:, 3])  # send in only gyro data
            if is_gup:
                print("Gup detected")
                return [0, 0, 0, 0, 1]
            else:
                breath_result = self.detect_breath(breath_data)
                if breath_result[1] == 1:  # detected that we are now breathing out
                    self.look_for_gups = False  # TODO this will probably trigger too often (need to show a trend of exhale)
                    # print("Exhale after gup predicted")
                    return [0, 1, 0, 0, 0]

                elif breath_result[0] == 1:  # detected that we are now breathing out
                    self.look_for_gups = False  # TODO this will probably trigger too often (need to show a trend of exhale)
                    # print("Inhale after gup predicted")
                    return [1, 0, 0, 0, 0]

        # returns all zeros if nothing is detected
        result = [0, 0, 0, 0, 0]
        return result

    def detect_gup(self, gyro_data):
        # checks chunks of 11 datapoints through the check if gup fucntion to determine if a gup is returned
        recent_window1 = gyro_data[-11:]
        check1 = check_if_gup(recent_window1)
        recent_window2 = gyro_data[-22:-11]
        check2 = check_if_gup(recent_window2)
        recent_window3 = gyro_data[-33:-22]
        check3 = check_if_gup(recent_window3)

        return check1 or check2 or check3

    def detect_breath(self, data):
        # Detects if an inhale, exhale or local max/min breath is detected by evaluating the line of best fit
        num_data_pts = -15
        x_array = np.array(range(0, len(data[num_data_pts:])))

        slope = best_fit_slope(x_array, data[num_data_pts:])
        print(slope)

        if slope > INHALE_SLOPE_THRESH:
            print("inhale")
            event_array = [1, 0, 0, 0, 0]

        elif slope < (-1 * EXHALE_SLOPE_THRESH):
            print("exhale")
            event_array = [0, 1, 0, 0, 0]
        else:
            print("local max/min")
            event_array = [0, 0, 0, 0, 0]

        return event_array

    def get_previous_data(self):
        # Grabs the previous ~30 datapoints.  Deletes any data that is not recent within 30 datapoints
        # previous data is deleted to maximize efficiency in opening and closing the database
        self.cursor.execute(
            "SELECT AUTO_INCREMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'band_and_1accel' AND TABLE_NAME = 'all_data';")
        next_increment = self.cursor.fetchall()[0][0]

        index = (next_increment) - SIZE_PACKET

        sql_string = "SELECT `a_x`, `a_y`, `a_z`, `g_x`, `g_y`, `g_z`, `voltage` FROM all_data WHERE id > {} ;".format(
            index)
        self.cursor.execute(sql_string)
        results = list(self.cursor.fetchall())

        sql_string = "DELETE FROM all_data WHERE id < {} ;".format(index)
        self.cursor.execute(sql_string)

        sql_string = "DELETE FROM gup_status WHERE id < {} ;".format(index)
        self.cursor.execute(sql_string)

        if len(results) < (SIZE_PACKET - 1):
            return False

        return results

    def read_band_value(self):
        return self.band.value

    def read_accel_value(self):
        print("reading accel value")
        return self.accel.a_value[0], self.accel.a_value[1], self.accel.a_value[2], self.accel.g_value[0], \
               self.accel.g_value[1], self.accel.g_value[2]


# This chunk of data only runs if the file is called internally not if it is imported to another file
if __name__ == "__main__":

    try:
        recording = RecordToDatabase(MbientFusion("FB:87:E7:94:0E:34"), Sensor(1))
        recording.start()
        while True:
            time.sleep(.1)
    except:
        print("Keyboard Interupt raised")
        recording.stop()  # = True
