# requires:
# pip install python
#
from flask import Flask, render_template, request
import datetime
import json
import random

app = Flask(__name__)


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

    if inEnd:
        end = datetime.datetime.fromtimestamp(int(inEnd) / 1000)
    else:
        end = datetime.datetime.now()

    if inStart:
        start = datetime.datetime.fromtimestamp(int(inStart) / 1000)
    else:
        start = datetime.datetime.now() - datetime.timedelta(weeks=1)

    data = []
    DAYS=(end - start).days
    for i in range(0, DAYS):
        date = end - datetime.timedelta(days=(DAYS - i))
        data.append([datetime_to_epochmillis(date), random.randint(0, 1000)])

    HOURS=(end - datetime.timedelta(days=1)).hour
    for i in range(0, HOURS):
        date = end - datetime.timedelta(hours=(HOURS - i))
        data.append([datetime_to_epochmillis(date), random.randint(0, 1000)])

    return "%s(%s)" % (callback, json.dumps(data))


def datetime_to_epochmillis(date):
    return int((date - datetime.datetime(year=1970, month=1, day=1, hour=0, minute=0, second=0)).total_seconds() * 1000)

if __name__ == '__main__':
    app.run(debug=True)
