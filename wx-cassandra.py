# requires:
# pip install python cassandra-driver
#
from flask import Flask, render_template, request
import datetime
import sys
import json
import logging
import pytz

rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(thread)d - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
fileLogger = logging.FileHandler("/tmp/client.log")
fileLogger.setLevel(logging.WARN)
fileLogger.setFormatter(formatter)
rootLogger.addHandler(ch)
rootLogger.addHandler(fileLogger)

from cassandra.cluster import Cluster

app = Flask(__name__)

# todo: config
cluster = Cluster(['192.168.5.34', '192.168.5.31', '192.168.5.30'])
session = cluster.connect()

prepared_query = session.prepare("SELECT * FROM wx.wxrecord "
                                 "WHERE station_id=? "
                                 "AND day=? "
                                 "AND millis < ? "
                                 "AND millis > ? ")

@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/graph')
def render_graph():
    return render_template('google_example_graph.html')

@app.route('/graph_dynamic')
def render_dynamic_graph():
    return render_template('google_example_dynamic.html')

@app.route('/graph_highstocks')
def render_highstocks_example():
    week_ago = datetime.datetime.utcnow() - datetime.timedelta(weeks=1)
    return render_template('highstocks_random_loader.html', start_millis=datetime_to_epochmillis(week_ago))

@app.route('/jquery_data')
def render_graph_query():
    callback = request.args.get('callback')
    inEnd = request.args.get('end')
    inStart = request.args.get('start')
    name = request.args.get('name')

    if not name:
        name = 'FrontPorch3'

    if inEnd and inEnd != 'NaN':
        end = datetime.datetime.utcfromtimestamp(int(inEnd) / 1000)
    else:
        end = datetime.datetime.utcnow()

    if inStart and inStart != 'NaN':
        start = datetime.datetime.utcfromtimestamp(int(inStart) / 1000)
    else:
        start = datetime.datetime.utcnow() - datetime.timedelta(weeks=1)

    end_millis = datetime_to_epochmillis(end)
    start_millis = datetime_to_epochmillis(start)
    day = long(end_millis / 86400000)

    logging.debug("requesting data for day %s between %s and %s" % (day, start, end))
    rows = session.execute(prepared_query, [name, day, end_millis, start_millis])

    data = []
    for row in rows:
        if row.type == 'temperature':
            data.append([long(row.millis / 1000) * 1000, row.value])

    return "%s(%s)" % (callback, json.dumps(data))

def datetime_to_epochmillis(date):
    return long((date - datetime.datetime.utcfromtimestamp(0)).total_seconds() * 1000)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
