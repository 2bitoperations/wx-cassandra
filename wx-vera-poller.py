from cassandra.cluster import Cluster
import requests
import logging
import sys
import datetime
import time

rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(thread)d - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
fileLogger = logging.FileHandler("/tmp/server.log")
fileLogger.setLevel(logging.WARN)
fileLogger.setFormatter(formatter)
rootLogger.addHandler(ch)
rootLogger.addHandler(fileLogger)

# todo: config
cluster = Cluster(['192.168.5.34', '192.168.5.31', '192.168.5.30'])
session = cluster.connect()

sensors = ['Back Door',
           'Front Door',
           'FrontPorch3',
           'GalaxyTemp',
           'GuestTempLight']

types = ['temperature',
         'humidity',
         'light']

insert_prepared = session.prepare("INSERT INTO wx.wxrecord "
                                  "(station_id, day, millis, type, value) VALUES "
                                  "(?, ?, ?, ?, ?)")


def record_reading(device, curr_type):
    if curr_type in device:
        if curr_type == 'temperature':
            # convert to celcius. we are engineers.
            val = (float(device[curr_type]) - 32) / 1.800
        else:
            val = float(device[curr_type])
        logging.debug("saving %s for device %s as %s" % (curr_type, device['name'], val))
        session.execute(insert_prepared, [device['name'], day, millis, curr_type, val])


while True:
    r = requests.get('http://192.168.5.45:3480/data_request?id=sdata')

    if r.status_code != 200:
        logging.warn("couldn't query vera %s", r)
        time.sleep(10)
        continue

    data = r.json()

    devices = data['devices']

    for device in devices:
        if device['name'] in sensors:
            logging.debug("keyed on device %s" % device['name'])
            # ok need to make a record. get the day.
            now = datetime.datetime.utcnow()
            millis = long((now - datetime.datetime.utcfromtimestamp(0)).total_seconds() * 1000)
            day = long(millis / 86400000)

            for curr_type in types:
                record_reading(device, curr_type)
    time.sleep(30)