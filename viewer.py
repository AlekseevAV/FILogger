from flask import Flask, render_template
import sqlite3
import json
app = Flask(__name__, static_folder='static')


@app.route('/')
@app.route('/index')
def index():
    con = sqlite3.connect('find_iphone_logger.db').cursor()
    locations = con.execute('SELECT * FROM locations').fetchall()
    return render_template("map_index.html", locations=json.dumps(locations))


def func_to_test(x):
    return x**2


if __name__ == "__main__":
    app.run()
