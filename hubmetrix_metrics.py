from flask import Flask, request
from metrics_computation import *
from customer_utils import *
import os
import base64
import json

app = Flask(__name__)


app.config['APP_URL'] = os.getenv('APP_URL', 'https://abtggwksuh.execute-api.us-west-1.amazonaws.com')
app.config['BC_CLIENT_ID'] = os.getenv('BC_CLIENT_ID', '5sdgtpwp82lxz5elfh5c5e2uvjzd07g')
app.config['BC_CLIENT_SECRET'] = os.getenv('BC_CLIENT_SECRET', 'rua2g02c6t6b6eloudlne400jnmod4z')
app.config['SESSION_SECRET'] = os.getenv('SESSION_SECRET', os.urandom(64))
app.config['HS_REDIRECT_URI'] = 'https://9kr5377xjf.execute-api.us-west-1.amazonaws.com/dev/hsauth'
app.config['HS_CLIENT_ID'] = 'f0e25e19-d1f3-48fe-93fc-59d744e2326e'
app.config['HS_CLIENT_SECRET'] = '74c80cfa-9bed-4770-8e31-a581df04a181'

app.secret_key = app.config['SESSION_SECRET']


def error_info(e):
    content = ""
    try:  # it's probably a HttpException, if you're using the bigcommerce client
        content += str(e.headers) + "<br>" + str(e.content) + "<br>"
        req = e.response.request
        content += "<br>Request:<br>" + req.url + "<br>" + str(req.headers) + "<br>" + str(req.body)
    except AttributeError as e:  # not a HttpException
        content += "<br><br> (This page threw an exception: {})".format(str(e))
    return content


@app.errorhandler(500)
def internal_server_error(e):
    content = "Internal Server Error: " + str(e) + "<br>"
    content += error_info(e)
    return content, 500


@app.errorhandler(400)
def bad_request(e):
    content = "Bad Request: " + str(e) + "<br>"
    content += error_info(e)
    return content, 400


@app.route('/')
def index():
    return 'Welcome to the Hubmetrix metrics backend!'


@app.route('/bc-ingest-customers', methods=["POST"])
def bc_ingest_customers():
    return 'request data is: {}'.format(json.loads(request.data))


@app.route('/bc-ingest-orders', methods=["POST"])
def bc_ingest_orders():
    data = json.loads(request.data)
    orders = get_all_customer_orders(data, app.config, order_list=[])

    app_user = get_app_user(data)
    metrics = compute_metrics(orders, app_user)
    print('Monthly total: {}'.format(metrics.monthly))

    return 'Ok'


@app.route('/bc-ingest-shipments', methods=["POST"])
def bc_ingest_shipments():
    return 'request is: {}'.format(request.args)


if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, port=8100)