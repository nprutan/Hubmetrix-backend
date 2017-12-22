from bigcommerce.api import BigcommerceApi
from flask import Flask, request
from dynamodb_utils import *
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


@app.route('/')
def index():
    return 'Welcome to the Hubmetrix metrics backend!'


@app.route('/bc-ingest-customers', methods=["POST"])
def bc_ingest_customers():
    return 'request is: {}'.format(request.args)


@app.route('/bc-ingest-orders', methods=["POST"])
def bc_ingest_orders():
    data = json.loads(base64.b64decode(request.get_json(force=True)))

    orders = get_all_customer_orders(data)

    computed = compute_analytics(orders)

    if computed:
        return 200
    return 500


@app.route('/bc-ingest-shipments', methods=["POST"])
def bc_ingest_shipments():
    return 'request is: {}'.format(request.args)


def get_bc_client_id():
    return app.config['BC_CLIENT_ID']


def get_bc_client_secret():
    return app.config['BC_CLIENT_SECRET']


def get_hs_client_id():
    return app.config['HS_CLIENT_ID']


def get_hs_client_secret():
    return app.config['HS_CLIENT_SECRET']


def get_hs_redir_uri():
    return app.config['HS_REDIRECT_URI']


def get_bc_client(user):
    return BigcommerceApi(client_id=get_bc_client_id(),
                            store_hash=user.bc_store_hash,
                            access_token=user.bc_access_token)

def get_all_customer_orders(data):
    bc_store_hash = data['producer'].split('/')[1]
    app_user = get_query_first_result(AppUser, bc_store_hash)
    client = get_bc_client(app_user)

    order_id = data['data']['id']
    order = client.Orders.get(order_id)

    return client.Orders.all(customer_id=order.customer_id)


def compute_analytics(orders):
    return True

if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, port=8100)