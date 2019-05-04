from flask import *
import mysql.connector
import sqlite3
import json
from testing_new_alg import MbientFusion, Sensor, RecordToDatabase
import time
app = Flask(__name__)


credentials = json.load(open("credentials.json", "r"))

@app.route('/', methods=['GET'])
def index():
    if 'username' in session:
        nickname = request.args.get('nickname')
        record_exhale = request.args.get('record_exhale')
        record_gups = request.args.get('record_gups')
        return redirect(url_for('temp_chart', nickname=nickname, record_exhale=record_exhale, record_gups=record_gups))
        # return render_template('SEED_page.html', username=nickname, record_exhale=record_exhale, record_gups=record_gups, data = 'test' )
    return redirect(url_for('login'))

@app.route('/temp_chart', methods=['GET'])
def temp_chart():
    nickname = request.args.get('nickname')
    record_exhale = request.args.get('record_exhale')
    record_gups = request.args.get('record_gups')
    return render_template('SEED_page.html', username=nickname, record_exhale=record_exhale, record_gups=record_gups)

@app.route('/login', methods=['GET', 'POST'])
def login():
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
                    if password_form == row[0]:
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
                            url_for('index', nickname=nickname, record_exhale=record_exhale, record_gups=record_gups))

                    else:
                        error = "Invalid Password"
            else:
                error = "Invalid Credential"
        except:
            return redirect(url_for('new_user'))
    return render_template('login.html', error=error)

@app.route('/new_user', methods=['GET', 'POST'])
def new_user():
    conn = sqlite3.connect("static/database/user_data.db", check_same_thread=False)
    curr = conn.cursor()
    error = None

    if request.method == 'POST':
        username_form = request.form['username']
        password_form = request.form['password']
        nickname_form = request.form['nickname']
        age_form = request.form['age']
        weight_form = request.form['weight']
        gender_form = request.form['gender']

        curr.execute("INSERT INTO users (username, password, nickname, age, weight, gender, record_exhale, record_gups) VALUES ('"+username_form+
                     "', '"+password_form+"', '"+nickname_form+"', "+age_form+", "+weight_form+", '"+gender_form+"', 0, 0 );")
        conn.commit()
        conn.close()
        session['username'] = username_form
        return redirect(url_for('index', nickname=nickname_form, record_exhale=0, record_gups=0))

    return render_template('new_user.html', error=error)


@app.route('/gup_stat', methods=['GET'])
def gup_stat():
    database = mysql.connector.connect(
        host=credentials["host"],
        user=credentials["user"],
        passwd=credentials["password"],
        database=credentials["database"]
    )
    cursor = database.cursor()

    since_timestamp = request.args.get("since")
    print(since_timestamp)
    if since_timestamp is None:
        since_timestamp = "0"

    cursor.execute("SELECT * FROM gup_status where timestamp > '" + since_timestamp + "'")
    data = cursor.fetchall()

    cursor.close()
    database.close()
    return json.dumps(data)





@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))



app.secret_key = 'A0Zr15j/0yX R~gxH!jmN]LFX/,?JT'


if __name__ == "__main__":
    app.run(host='169.254.29.231', port=5000, debug=False, threaded=True)

    # app.run(host='10.245.72.238', port=5000, debug=True, threaded=True)

    # try:
    #     recording = RecordToDatabase(MbientFusion("FB:87:E7:94:0E:34"), Sensor(1))
    #     recording.start()
    #     while True:
    #         time.sleep(.1)
    # except:
    #     print("Keyboard Interupt raised")
    #     recording.stop() # = True

