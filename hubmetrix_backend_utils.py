from bigcommerce.api import BigcommerceApi
from dynamodb_utils import *
from contextlib import contextmanager
import pendulum
import json


@contextmanager
def bc_customer_manager(data, config):
    data = json.loads(data)
    app_user = get_app_user(data)
    client = get_bc_client(app_user, config)
    customer = get_bc_customer(client, data)
    customer_address = get_bc_customer_address(customer)
    yield (client, app_user, customer, customer_address)


def hubmetrix_last_sync_timestamp(func):
    def wrapper(payload, user):
        func(payload, user)
        user.update(actions=[
            AppUser.hm_last_sync_timestamp.set(pendulum.now().to_cookie_string())]
        )
    return wrapper


def get_bc_store_hash(data):
    bc_store_hash = data['producer'].split('/')[1]

    return bc_store_hash


def get_app_user(data):
    store_hash = get_bc_store_hash(data)
    return get_query_first_result(AppUser, store_hash)


def get_bc_client(user, config):
    bc_client = BigcommerceApi(client_id=get_bc_client_id(config),
                               store_hash=user.bc_store_hash,
                               access_token=user.bc_access_token)

    return bc_client


def get_bc_customer(client, data):
    customer_id = get_customer_id_from_webhook(client, data)
    return client.Customers.get(customer_id)


def get_bc_customer_address(customer):
    address = customer.addresses(customer.id)
    if hasattr(address, 'id'):
        return address
    else:
        if hasattr(address, 'append'):
            return address[0]


def get_customer_id_from_webhook(client, data):
    scope = data['scope']
    if 'order' in scope:
        order_id = data['data']['id']
        order = client.Orders.get(order_id)
        return order.customer_id
    # If it's not an order payload, it's a customer
    # in which case, 'id' is the customer id
    return data['data']['id']


def get_all_customer_orders(client, customer_id, page=1, order_list=None):
    temp_order_list = client.Orders.all(customer_id=customer_id, is_deleted=False, limit=250, page=page)

    # When paging is exhausted we get an instance of Orders, not a list
    if hasattr(temp_order_list, 'extend'):
        order_list.extend(temp_order_list)
        page += 1
        get_all_customer_orders(client, customer_id, page=page, order_list=order_list)

    return order_list


def get_bc_client_id(config):
    return config['BC_CLIENT_ID']


def get_bc_client_secret(config):
    return config['BC_CLIENT_SECRET']


def get_hs_client_id(config):
    return config['HS_CLIENT_ID']


def get_hs_client_secret(config):
    return config['HS_CLIENT_SECRET']


def get_hs_redir_uri(config):
    return config['HS_REDIRECT_URI']
