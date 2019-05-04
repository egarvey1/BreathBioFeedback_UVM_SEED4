# Import Connector
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import mysql.connector
# import datetime
# import smbus
import time
import numpy as np
import random

# from pymetawear.discover import select_device
# from pymetawear.client import MetaWearClient
# from mbientlab.metawear.cbindings import SensorFusionData, SensorFusionGyroRange, SensorFusionAccRange, SensorFusionMode
#
#
# import board
# import busio

from keras.models import model_from_json

SIZE_PACKET = 30

print("Elastic Band Data Logger\n")
print("DATE\t   TIME \t   GUP STATUS")
print("-----------------------------")


class RecordToDatabase:
    def __init__(self, ml_model):
        self.ml_model = ml_model
        self.time_last = time.time()
        self.write_to_db()

    def write_to_db(self):
        try:
            while True:
                # Create connection cnx
                cnx, cursor = self.open_database('band_and_1accel')

                add_data_entry = "INSERT INTO `all_data` (`timestamp`, `voltage`, `raw_value`, `a_x`, `a_y`, `a_z`, `g_x`, `g_y`, `g_z`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s);"
                add_status_entry = "INSERT INTO `gup_status` (`timestamp`, `gup_status`) VALUES (%s,%s);"

                # Get Time
                now = time.time()  # datetime.datetime.now().strftime("%S.%f")

                # Get Temperature Info.
                value, voltage = self.read_band_value()
                a_x, a_y, a_z, g_x, g_y, g_z = self.read_accel_value()

                previous_data = self.get_previous_data(cursor)

                if previous_data != False:
                    status = self.evaluate_model(previous_data, [value, voltage, a_x, a_y, a_z, g_x, g_y, g_z])
                else: #there is not enough previous data to go off of
                    status = 0

                entry_data = (now, voltage, value, a_x, a_y, a_z, g_x, g_y, g_z)
                entry_status = (now, status)

                # print(add_data_entry)
                # print(entry_data)
                #
                # print(add_status_entry)
                # print(entry_status)

                cursor.execute(add_data_entry, entry_data)
                cursor.execute(add_status_entry, entry_status)

                self.close_database(cnx, cursor)

                time.sleep(0.1)
        except KeyboardInterrupt:  # exit gracefully
            try:  # throws an exception if they are already committed
                cnx.commit()
                cursor.close()
                cnx.close()
            except:
                pass
    def open_database(self, database):
        cnx = mysql.connector.connect(user='egarvey', \
                                      password='dreamteam', \
                                      database=database)
        # Create cursor, that executes commands
        cursor = cnx.cursor()

        return cnx, cursor

    def close_database(self, cnx, cursor):
        cnx.commit()
        cursor.close()
        cnx.close()

    def evaluate_model(self, prev_data, new_data):
        prev_data = np.array(prev_data)
        print("Previous data set", prev_data)
        print("New data set",new_data)
        data = np.append(prev_data, [new_data], axis=0)
        print(data)
        status = self.ml_model.predict(data)

        return status

    def get_previous_data(self, cursor):
        cursor.execute("SELECT AUTO_INCREMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'band_and_1accel' AND TABLE_NAME = 'all_data';")
        next_increment = cursor.fetchall()[0][0]
        # print("Next increment", next_increment)

        index = (next_increment) - SIZE_PACKET

        sql_string = "SELECT `voltage`, `raw_value`, `a_x`, `a_y`, `a_z`, `g_x`, `g_y`, `g_z` FROM all_data WHERE id > {} ;".format(index)
        # print("String", sql_string)
        cursor.execute(sql_string)
        results = list(cursor.fetchall())
        # print("The results: ", results)
        # print("Length of results:", len(results))

        if len(results) < (SIZE_PACKET-1):
            return False

        return results

    def read_band_value(self):
        return random.randint(1, 10), random.randint(1, 10)

    def read_accel_value(self):
        return random.randint(1, 10), random.randint(1, 10), random.randint(1, 10), random.randint(1,10), random.randint(1, 10), random.randint(1, 10)


if __name__ == "__main__":
    json_file = open('model.json', 'r')
    loaded_model_json = json_file.read()
    json_file.close()

    loaded_model = model_from_json(loaded_model_json)
    loaded_model.load_weights("model.h5")

    RecordToDatabase(loaded_model)
