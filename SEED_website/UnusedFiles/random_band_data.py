import mysql.connector
# import datetime
# import smbus
import time
import random
# import board
# import busio

# print("Elastic Band Data Logger\n")
# print("DATE\t   TIME \t   GUP STATUS")
# print("-----------------------------")




class ML_database:
    def __init__(self):
        self.time_last = time.time()
        self.write_to_db()

    def write_to_db(self):
        try:
            while True:

                    # Create connection cnx
                    cnx = mysql.connector.connect(user='egarvey', \
                                                  password='dreamteam', \
                                                  database='band_v0')

                    # Create cursor, that executes commands
                    cursor = cnx.cursor()

                    add_entry = "INSERT INTO `band_data` (`timestamp`, `voltage`, `raw_value`) VALUES (%s,%s,%s);"

                    # Get Time
                    now = time.time()  # datetime.datetime.now().strftime("%S.%f")

                    # Get Temperature Info
                    value, voltage = self.read_value()

                    # Print info
                    # timestamp = now.strftime("%m/%d/%Y %H:%M:%S")
                    outstring = str(now) + "\t" + str(format(value, '10.4f')) + "C" + str(
                        format(voltage, '10.4f')) + "F" + "\n"
                    print (outstring.rstrip())

                    entry = (now, voltage, value)

                    cursor.execute(add_entry, entry)

                    cnx.commit()
                    cursor.close()
                    cnx.close()
                    time.sleep(0.1)
        except KeyboardInterrupt: #exit gracefully
            try: #throws an exception if they are already committed
                cnx.commit()
                cursor.close()
                cnx.close()
            except:
                pass

    def read_value(self):
        return random.randint(1,10), random.randint(1,10),




if __name__ == "__main__":
    ML_database()