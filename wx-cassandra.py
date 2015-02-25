# requires:
# pip install python
#
from flask import Flask, render_template
import gviz_api
import datetime
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

@app.route('/graph_query')
def render_graph_query():
    table_description = {"date": ("date", "Date"),
                         "some_number": ("number", "Some Random Number")}
    data_table = gviz_api.DataTable(table_description=table_description)

    data = []
    DAYS=900
    for i in range(0, DAYS):
        date = datetime.datetime.now() - datetime.timedelta(days=(DAYS - i))
        data.append({"date": date, "some_number": random.randint(1, 1000)})

    data_table.LoadData(data)

    return data_table.ToJSonResponse(columns_order=("date", "some_number"),
                                     order_by="date")


if __name__ == '__main__':
    app.run(debug=True)
