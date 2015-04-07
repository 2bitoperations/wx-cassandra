# requires:
# pip install cassandra-driver
#
from flask import Flask, render_template, request
import datetime
import sys
import json
import logging
from cassandra.cluster import Cluster

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

FAKE_DAY_BIN = 86400000
app = Flask(__name__)

# todo: config
cluster = Cluster(['192.168.5.34', '192.168.5.31', '192.168.5.30'])
sensor_names = ['FrontPorch3', 'GalaxyTemp', 'GuestTempLight', 'Front Door', 'Back Door', 'garage', 'garden']

def mean(vals):
    logging.debug("using mean")
    return sum(vals) / float(len(vals))

types_and_agg = {'temperature': mean,
                 'humidity': mean,
                 'light': mean,
                 'flow': sum}
session = cluster.connect()

prepared_query = session.prepare("SELECT * FROM wx.wxrecord "
                                 "WHERE station_id=? "
                                 "AND day IN (?, ?, ?) "
                                 "AND millis < ? "
                                 "AND millis > ? ")

long_query = session.prepare("SELECT * FROM wx.days "
                                 "WHERE station_id=? "
                                 "AND millis < ? "
                                 "AND millis > ?")

compaction_select = session.prepare("SELECT * FROM wx.wxrecord "
                                    "WHERE station_id=? "
                                    "AND day=?")

compaction_insert = session.prepare("INSERT INTO wx.days "
                                    "(station_id, millis, type, value) "
                                    "VALUES "
                                    "(?, ?, ?, ?)")

insert_prepared = session.prepare("INSERT INTO wx.wxrecord "
                                  "(station_id, day, millis, type, value) VALUES "
                                  "(?, ?, ?, ?, ?)")


@app.route('/')
def hello_world():
    return 'Hello World!'

# @app.route('/convert')
# def convert():
#     # compact the previous day's data for a bunch of different sensors
#
#     yesterday = datetime_to_fakeday(datetime.datetime.utcnow() - datetime.timedelta(days=0))
#
#     for sensor in sensor_names:
#         logging.debug("starting to convert sensor %s for %s " % (sensor, yesterday))
#         rows = session.execute(compaction_select, [sensor, yesterday])
#
#         for row in rows:
#             if row.type == 'temperature':
#                 val = (row.value * 1.8) + 32
#                 session.execute(insert_prepared, [row.station_id, row.day, row.millis, row.type, val])
#
#     return "done"

@app.route('/compact')
def compact():
    # compact the previous day's data for a bunch of different sensors

    yesterday = datetime_to_fakeday(datetime.datetime.utcnow() - datetime.timedelta(days=1))

    for sensor in sensor_names:
        all_readings = dict()
        logging.debug("starting to compact sensor %s for %s " % (sensor, yesterday))
        rows = session.execute(compaction_select, [sensor, yesterday])

        for row in rows:
            # bin per 30-minute interval
            bin_millis = datetime_to_30_bin(row.millis)
            if bin_millis not in all_readings:
                all_readings[bin_millis] = dict()
            if row.type not in all_readings[bin_millis]:
                all_readings[bin_millis][row.type] = []

            all_readings[bin_millis][row.type].append(row.value)

        for bin_millis, types in all_readings.iteritems():
            for cur_type, values in types.iteritems():
                val = types_and_agg[cur_type](values)

                session.execute(compaction_insert, [sensor, bin_millis, cur_type, val])

    return "done"

@app.route('/graph_highstocks')
def render_highstocks_example():
    week_ago = datetime.datetime.utcnow() - datetime.timedelta(weeks=1)
    yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    return render_template('highstocks_random_loader.html',
                           week_millis=datetime_to_epochmillis(week_ago),
                           yesterday_millis=datetime_to_epochmillis(yesterday),
                           sensor_names=sensor_names)

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
    day = datetime_to_fakeday(end)

    logging.debug("requesting data for day %s between %s and %s" % (day, start, end))

    total_time = end - start
    if total_time > datetime.timedelta(days=3):
        rows = session.execute(long_query, [name, end_millis, start_millis])
    else:
        rows = session.execute(prepared_query, [name, day - 1, day, day + 1, end_millis, start_millis])

    data = []
    for row in rows:
        if row.type == 'temperature':
            data.append([long(row.millis / 1000) * 1000, row.value])

    return "%s(%s)" % (callback, json.dumps(data))

def datetime_to_epochmillis(date):
    return long((date - datetime.datetime.utcfromtimestamp(0)).total_seconds() * 1000)

def datetime_to_fakeday(date):
    millis = datetime_to_epochmillis(date)
    return long(millis / FAKE_DAY_BIN)

def datetime_to_30_bin(millis):
    return millis - (millis % 1800000)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
