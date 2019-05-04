# Importing the necessary libraries
from flask import *
import mysql.connector
import sqlite3
import json
from testing_new_alg import MbientFusion, Sensor, RecordToDatabase
import time

app = Flask(__name__)

credentials = json.load(open("credentials.json", "r"))

""" This is the local hostname ('169.254.29.231'), it is subject to change
if the pi is being accessed wirelessly.  If the pi is connected to WiFi,
connect to the Pi terminal via Ethernet and type the command
'hostname -I', the result is the  hostname and should be updated in the hostname variable below"""
HOSTNAME = '169.254.29.231'

"""This is the MBient Accelerometer IP address.  It is subject to change in the event that a different accelerometer is 
used.  The IP address cal be found as a sticker on the accelerometer.
"""
MBIENT_ADDRESS = "FB:87:E7:94:0E:34"

# The analog to digital converter channel.  This value is not likely to change without change to the PCB
ADC_INPUT_CHANNEL = 1

"""This is the default path that is loaded when trying to connect to the website
It will redirect the user to a login page if cached data does not already exist
for login"""


@app.route('/', methods=['GET'])
def index():
    if 'username' in session:  # If the user has logged in
        # Get the following values
        nickname = request.args.get('nickname')
        record_exhale = request.args.get('record_exhale')
        record_gups = request.args.get('record_gups')
        # Once data is accessed return to the main page with the given information
        return redirect(url_for('temp_chart', nickname=nickname, record_exhale=record_exhale, record_gups=record_gups))
    # If not return to the login page
    return redirect(url_for('login'))


"""This is the main page directory.  It currently renders the inhale exhale and gup exercise"""


@app.route('/temp_chart', methods=['GET'])
def temp_chart():
    # Get the previously sent data from the session
    nickname = request.args.get('nickname')
    record_exhale = request.args.get('record_exhale')
    record_gups = request.args.get('record_gups')
    # Render the SEED html template
    return render_template('SEED_page.html', username=nickname, record_exhale=record_exhale, record_gups=record_gups)


"""This is the login page.  Users enter their login information or enter blank data to create a new username"""


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Connect to the user database
    error = None
    conn = sqlite3.connect("static/database/user_data.db", check_same_thread=False)
    curr = conn.cursor()
    if 'username' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username_form = request.form['username']
        password_form = request.form['password']

        curr.execute(
            "SELECT username FROM users WHERE username = '" + username_form + "' ;")  # CHECKS IF USERNAME EXSIST
        try:
            if curr.fetchone()[0]:
                curr.execute(
                    "SELECT password FROM users WHERE username = '" + username_form + "' ;")  # FETCH THE HASHED PASSWORD
                for row in curr.fetchall():
                    if password_form == row[
                        0]:  # If the passwords match (This could be improved in future versions to encode the password - more robust)
                        session['username'] = username_form
                        curr.execute("SELECT nickname FROM users WHERE username = '" + username_form + "' ;")
                        nickname = curr.fetchone()[0]
                        curr.execute("SELECT record_exhale FROM users WHERE username = '" + username_form + "' ;")
                        record_exhale = curr.fetchone()[0]
                        curr.execute("SELECT record_gups FROM users WHERE username = '" + username_form + "' ;")
                        record_gups = curr.fetchone()[0]

                        conn.commit()
                        conn.close()
                        return redirect(
                            # Given the data we have queried, return to the main page with this info
                            url_for('index', nickname=nickname, record_exhale=record_exhale, record_gups=record_gups))

                    else:
                        # Other wise raise an error (displayed on the login page) that tells the user that they input the wrong password
                        error = "Invalid Password"
            else:
                error = "Invalid Credential"
        except:
            # If incorrect data is entered, the user is prompted to create a new account (this could also be improved upon)
            return redirect(url_for('new_user'))
    return render_template('login.html', error=error)


"""This is the page to create a new username.  The page requests various meta data for each user that may be used at a later date"""


@app.route('/new_user', methods=['GET', 'POST'])
def new_user():
    conn = sqlite3.connect("static/database/user_data.db", check_same_thread=False)
    curr = conn.cursor()
    error = None
    # Insert the new user data to the user database for future use
    if request.method == 'POST':
        username_form = request.form['username']
        password_form = request.form['password']
        nickname_form = request.form['nickname']
        age_form = request.form['age']
        weight_form = request.form['weight']
        gender_form = request.form['gender']

        curr.execute(
            "INSERT INTO users (username, password, nickname, age, weight, gender, record_exhale, record_gups) VALUES ('" + username_form +
            "', '" + password_form + "', '" + nickname_form + "', " + age_form + ", " + weight_form + ", '" + gender_form + "', 0, 0 );")
        conn.commit()
        conn.close()
        session['username'] = username_form
        return redirect(url_for('index', nickname=nickname_form, record_exhale=0, record_gups=0))

    return render_template('new_user.html', error=error)


"""This is the process which constantly accesses the exercise status from the gup status database
This page is accesses as json data by the javascript.  This page is not visible to the user"""


@app.route('/gup_stat', methods=['GET'])
def gup_stat():
    database = mysql.connector.connect(
        host=credentials["host"],
        user=credentials["user"],
        passwd=credentials["password"],
        database=credentials["database"]
    )
    # Create the cursor which is able to commit and query values from the database
    cursor = database.cursor()

    # get the last timestamp
    since_timestamp = request.args.get("since")
    print(since_timestamp)
    if since_timestamp is None:
        # Still waiting for data
        since_timestamp = "0"
    # Get the latest data from the database
    cursor.execute("SELECT * FROM gup_status where timestamp > '" + since_timestamp + "'")
    data = cursor.fetchall()

    cursor.close()
    database.close()
    return json.dumps(data)


"""This is the logout page.  It removes all user session data"""


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


# This is the secret key which allows data to be saved privately and to have a more secure session
app.secret_key = 'A0Zr15j/0yX R~gxH!jmN]LFX/,?JT'

# This chunk of code is always run unless the file is called externally
if __name__ == "__main__":
    """The try except statement will handle any unexpected errors and make sure the website and all
    devices close/ disconnect properly in any event 
    """
    try:
        # Start the accel and band recording to database code
        recording = RecordToDatabase(MbientFusion(MBIENT_ADDRESS), Sensor(ADC_INPUT_CHANNEL))
        recording.start()  # Start the recording session
        # Run the Application
        app.run(host=HOSTNAME, port=5000, debug=False, threaded=True)
        while True:
            time.sleep(.1)
    except:
        print("Keyboard Interupt raised")
        recording.stop()  # Stop the recording session
