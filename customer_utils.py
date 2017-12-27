from bigcommerce.api import BigcommerceApi
from dynamodb_utils import *

bc_client = None
hm_app_user = None
bc_store_hash = None


def get_bc_client(data):
    global bc_client
    global bc_store_hash
    if not bc_client:
        bc_store_hash = data['producer'].split('/')[1]
        user = get_query_first_result(AppUser, bc_store_hash)
        bc_client = BigcommerceApi(client_id=get_bc_client_id(),
                                store_hash=user.bc_store_hash,
                                access_token=user.bc_access_token)
        return bc_client
    return bc_client


def get_customer_id_from_webhook(data):
    client = get_bc_client(data)

    order_id = data['data']['id']
    order = client.Orders.get(order_id)
    return order.customer_id


def get_all_customer_orders(data, page=1, order_list=None):
    customer_id = get_customer_id_from_webhook(data)

    client = get_bc_client(data)

    temp_order_list = client.Orders.all(customer_id=customer_id, is_deleted=False, limit=250, page=page)

    # When paging is exhausted we get an instance of Orders, not a list
    if isinstance(temp_order_list, list):
        order_list.extend(temp_order_list)
        page += 1
        get_all_customer_orders(data, page=page, order_list=order_list)

    return order_list