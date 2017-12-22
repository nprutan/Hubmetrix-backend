from flask import Flask, request
import os

app = Flask(__name__)


app.config['APP_URL'] = os.getenv('APP_URL', 'https://abtggwksuh.execute-api.us-west-1.amazonaws.com')
app.config['SESSION_SECRET'] = os.getenv('SESSION_SECRET', os.urandom(64))


app.secret_key = app.config['SESSION_SECRET']


@app.route('/')
def index():
    return 'Welcome to the Hubmetrix metrics backend!'


@app.route('/bc-ingest-customers', methods=["POST"])
def bc_ingest_customers():
    return 'request is: {}'.format(request.args)


@app.route('/bc-ingest-orders', methods=["POST"])
def bc_ingest_orders():
    return 'request is: {}'.format(request.get_json(force=True))


@app.route('/bc-ingest-shipments', methods=["POST"])
def bc_ingest_shipments():
    return 'request is: {}'.format(request.args)



if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, port=8100)