# Import Connector
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import mysql.connector
from keras.models import model_from_json
import tensorflow as tf
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


SIZE_PACKET = 30


class MbientAccel():
    def __init__(self, address=None):

        if address == None:
            address = select_device()

#        print(address)
        self.c = MetaWearClient(str(address), debug=True)

        time.sleep(1.0)
        self.c.accelerometer.set_settings(data_rate=100, data_range=4.0)
        time.sleep(1.0)
        self.c.accelerometer.high_frequency_stream = True
        self.a_value = [0,0,0]
        self.g_value = [0, 0, 0]


    def stop(self):
        self.c.accelerometer.notifications(None)
        time.sleep(5.0)
        self.c.disconnect()

    def handle_acc_notifications(self, data):
        xyz = data["value"]
        self.a_value = [xyz.x, xyz.y, xyz.z]


    def handle_gyro_notifications(self, data):
        xyz = data["value"]
        self.g_value = [xyz.x, xyz.y, xyz.z]

    def start(self):
        self.c.accelerometer.notifications(lambda data: self.handle_acc_notifications(data))
        self.c.gyroscope.notifications(lambda gdata: self.handle_gyro_notifications(gdata))

class Sensor(threading.Thread):
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
    def __init__(self, ml_model, graph, accel, band):
        threading.Thread.__init__(self)
        self.thread_stop = False

        self.graph = graph
        self.accel = accel
        self.band = band

        self.ml_model = ml_model
        self.cnx = None
        self.connect = None

        self.initialize_sensors()



    def stop(self):
        self.thread_stop = True
        # self.join()
        print("Stopping Gracefully")
        self.accel.stop()
        self.band.stop()

        try:  # throws an exception if they are already committed
                self.cnx.commit()
                self.cursor.close()
                self.cnx.close()
        except:
            pass

    def initialize_sensors(self):
        self.accel.start()
        self.band.start()



    def write_to_db(self):
        # Create connection cnx
        try:
            self.cnx, self.cursor = self.open_database('band_and_1accel')

            add_data_entry = "INSERT INTO `all_data` (`timestamp`, `a_x`, `a_y`, `a_z`, `g_x`, `g_y`, `g_z`, `voltage`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s);"
            add_status_entry = "INSERT INTO `gup_status` (`timestamp`, `gup_status`) VALUES (%s,%s);"

            # Get Time
            now = time.time()  # datetime.datetime.now().strftime("%S.%f")

            # Get Band Info.
            voltage = self.read_band_value()
            a_x, a_y, a_z, g_x, g_y, g_z = self.read_accel_value()


            previous_data = self.get_previous_data()


            if previous_data != False:
                status = self.evaluate_model(previous_data, [a_x, a_y, a_z, g_x, g_y, g_z, voltage])
            else:  # there is not enough previous data to go off of
                status = 0

            entry_data = (now, a_x, a_y, a_z, g_x, g_y, g_z, voltage)
            entry_status = (now, status)

            self.cursor.execute(add_data_entry, entry_data)
            self.cursor.execute(add_status_entry, entry_status)

            self.close_database()

            time.sleep(0.01)
        except KeyboardInterrupt:
            # print("############# Look at me !!!!!!############")
            self.stop()

    def run(self):
        while not self.thread_stop:
            self.write_to_db()


    def open_database(self, database):
        cnx = mysql.connector.connect(user='egarvey', \
                                      password='dreamteam', \
                                      database=database)
        # Create cursor, that executes commands
        cursor = cnx.cursor()

        return cnx, cursor

    def close_database(self):
        self.cnx.commit()
        self.cursor.close()
        self.cnx.close()

    def evaluate_model(self, prev_data, new_data):
        prev_data = np.array(prev_data)
        # print("Previous data set", prev_data)
        # print("New data set", new_data)
        data = np.array([np.append(prev_data, [new_data], axis=0)])

        print("shape is: ", data.shape)
        if data.shape != (1,30,7):
            print("SOMETHING has gone horribly wrong!!!!!!!!!!")
            print("shape is: ", data.shape)
            return 0
        # print(data.shape)

        with self.graph.as_default():
            status = self.ml_model.predict(data)

        # print("Survey says", status[0])
        if status[0][4] == 1:
            return 1
        else:
            print(status[0])
            return 0

    def get_previous_data(self):
        self.cursor.execute("SELECT AUTO_INCREMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'band_and_1accel' AND TABLE_NAME = 'all_data';")
        next_increment = self.cursor.fetchall()[0][0]
        # print("Next increment", next_increment)

        index = (next_increment) - SIZE_PACKET

        sql_string = "SELECT `a_x`, `a_y`, `a_z`, `g_x`, `g_y`, `g_z`, `voltage` FROM all_data WHERE id > {} ;".format(index)
        self.cursor.execute(sql_string)
        results = list(self.cursor.fetchall())

        sql_string = "DELETE FROM all_data WHERE id < {} ;".format(index)
        self.cursor.execute(sql_string)

        # print(len(results))

        if len(results) < (SIZE_PACKET-1):
            return False

        return results

    def read_band_value(self):
        return self.band.value

    def read_accel_value(self):
        return self.accel.a_value[0], self.accel.a_value[1], self.accel.a_value[2], self.accel.g_value[0], self.accel.g_value[1], self.accel.g_value[2]


if __name__ == "__main__":
    # K.clear_session()
    json_file = open('model2.json', 'r')

    global model
    loaded_model_json = json_file.read()
    json_file.close()
    model = model_from_json(loaded_model_json)
    model.load_weights("model2.h5")


    global graph
    graph = tf.get_default_graph()

    #"FB:87:E7:94:0E:34"
    recording = RecordToDatabase(model, graph, MbientAccel(), Sensor(0))

    recording.start()


