from bigcommerce.api import BigcommerceApi
from dynamodb_utils import *


bc_client = None
hm_app_user = None
bc_store_hash = None


def get_bc_store_hash(data):
    global bc_store_hash

    if not bc_store_hash:
        bc_store_hash = data['producer'].split('/')[1]
        return bc_store_hash
    return bc_store_hash


def get_app_user(data):
    global hm_app_user

    if not hm_app_user:
        store_hash = get_bc_store_hash(data)
        hm_app_user = get_query_first_result(AppUser, store_hash)
    return hm_app_user


def get_bc_client(data, config):
    global bc_client
    global bc_store_hash
    if not bc_client:
        bc_store_hash = get_bc_store_hash(data)
        user = get_query_first_result(AppUser, bc_store_hash)
        bc_client = BigcommerceApi(client_id=get_bc_client_id(config),
                                store_hash=user.bc_store_hash,
                                access_token=user.bc_access_token)
        return bc_client
    return bc_client


def get_bc_customer(client, email):
    return client.Customers.all(email=email)[0]


def get_bc_customer_address(customer):
    return customer.addresses()[0]


def get_customer_id_from_webhook(data, config):
    client = get_bc_client(data, config)

    order_id = data['data']['id']
    order = client.Orders.get(order_id)
    return order.customer_id


def get_all_customer_orders(data, config, page=1, order_list=None):
    customer_id = get_customer_id_from_webhook(data, config)

    client = get_bc_client(data, config)

    temp_order_list = client.Orders.all(customer_id=customer_id, is_deleted=False, limit=250, page=page)

    # When paging is exhausted we get an instance of Orders, not a list
    if isinstance(temp_order_list, list):
        order_list.extend(temp_order_list)
        page += 1
        get_all_customer_orders(data, config, page=page, order_list=order_list)

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