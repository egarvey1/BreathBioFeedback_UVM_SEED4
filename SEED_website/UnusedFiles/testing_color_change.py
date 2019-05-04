from flask import *
# import mysql.connector
# import sqlite3
import json
from time import time
from random import random
import sys

app = Flask(__name__)


credentials = json.load(open("credentials.json", "r"))

@app.route('/', methods=['GET'])
def index():
    return render_template('testing123.html')


app.secret_key = 'A0Zr15j/0yX R~gxH!jmN]LFX/,?JT'


if __name__ == "__main__":
    # app.run(host='10.245.193.55', port=5000, debug=True)
    app.run()

