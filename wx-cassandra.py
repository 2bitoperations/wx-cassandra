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
    week_ago = datetime.datetime.now() - datetime.timedelta(weeks=1)
    return render_template('highstocks_random_loader.html', start_millis=datetime_to_epochmillis(week_ago))

@app.route('/jquery_data')
def render_graph_query():
    callback = request.args.get('callback')
    inEnd = request.args.get('end')
    inStart = request.args.get('start')
    local = pytz.timezone ("America/Chicago")
    utc_epoch = pytz.utc.localize(datetime.datetime.utcfromtimestamp(0))
    local_epoch = local.localize(datetime.datetime.utcfromtimestamp(0))

    if inEnd:
        end_naive = datetime.datetime.fromtimestamp(int(inEnd) / 1000)
        end_local = local.localize(end_naive, is_dst=None)
        end = end_local.astimezone(pytz.utc)
    else:
        end = pytz.utc.localize(datetime.datetime.utcnow())

    if inStart:
        start_naive = datetime.datetime.fromtimestamp(int(inStart) / 1000)
        start_local = local.localize(start_naive, is_dst=None)
        start = start_local.astimezone(pytz.utc)
    else:
        start = pytz.utc.localize(datetime.datetime.utcnow() - datetime.timedelta(weeks=1))

    end_millis = long((end - utc_epoch).total_seconds() * 1000)
    start_millis = long((start - utc_epoch).total_seconds() * 1000)
    day = long(end_millis / 86400000)

    logging.debug("requesting data for day %s between %s and %s" % (day, start, end))
    rows = session.execute(prepared_query, ['FrontPorch3', day, end_millis, start_millis])

    data = []
    for row in rows:
        if row.type == 'temperature':
            # do a stupid dance to convert the UTC time back to local:
            logging.debug("row millis %s " % row.millis)
            ts = pytz.utc.localize(datetime.datetime.utcfromtimestamp(row.millis / 1000))
            logging.debug("row %s" % ts)
            local_ts = ts.astimezone(local)
            logging.debug("match time %s local %s value %s" % (ts, local_ts, row.value))
            local_millis = long((local_ts - local_epoch).total_seconds() * 1000)
            logging.debug("local millis %s" % local_millis)
            data.append([local_millis, row.value])

    return "%s(%s)" % (callback, json.dumps(data))

def datetime_to_epochmillis(date):
    return int((date - datetime.datetime(year=1970, month=1, day=1, hour=0, minute=0, second=0)).total_seconds() * 1000)

if __name__ == '__main__':
    app.run(debug=True)
