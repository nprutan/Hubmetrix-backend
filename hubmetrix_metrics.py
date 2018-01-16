from flask import Flask, request
from metrics_computation import *
from hubmetrix_backend_utils import *
from hubspot_data import *
import os

app = Flask(__name__)


app.config['STAGE-PREFIX'] = os.environ.get('STAGE-PREFIX')
app.config['APP_URL'] = os.environ.get('APP_URL', 'http://localhost')
app.config['BC_CLIENT_ID'] = os.environ.get('BC_CLIENT_ID')
app.config['BC_CLIENT_SECRET'] = os.environ.get('BC_CLIENT_SECRET')
app.config['SESSION_SECRET'] = os.environ.get('SESSION_SECRET')
app.config['HS_REDIRECT_URI'] = os.environ.get('HS_REDIRECT_URI')
app.config['HS_CLIENT_ID'] = os.environ.get('HS_CLIENT_ID')
app.config['HS_CLIENT_SECRET'] = os.environ.get('HS_CLIENT_SECRET')

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
    with bc_customer_manager(request.data, app.config) as ctx:
        client, app_user, customer, customer_address = ctx

        if customer:
            metrics_empty = compute_metrics([], app_user, customer)

            with hubspot_housekeeping_manager(app_user, app.config, metrics_empty):
                payload = create_base_hubspot_payload(metrics_empty, customer, customer_address)
                post_batch_to_hubspot(payload, app_user)

    return 'Ok'


@app.route('/bc-ingest-orders', methods=["POST"])
def bc_ingest_orders():
    with bc_customer_manager(request.data, app.config) as ctx:
        client, app_user, customer, customer_address = ctx

        if customer:
            orders = get_all_customer_orders(client, customer.id, order_list=[])
            metrics = compute_metrics(orders, app_user, customer)

            with hubspot_housekeeping_manager(app_user, app.config, metrics):
                payload = metrics_to_hubspot_payload(metrics, customer, customer_address)
                post_batch_to_hubspot(payload, app_user)

    return 'Ok'


@app.route('/bc-ingest-shipments', methods=["POST"])
def bc_ingest_shipments():
    return 'Ok'


if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, port=8100)