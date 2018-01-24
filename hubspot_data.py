import json
from contextlib import contextmanager
from datetime import datetime
from hashlib import sha256
from uuid import uuid4
from enum import Enum
from time import sleep

import pendulum
import requests

from dynamodb_utils import *
from hubmetrix_backend_utils import hubmetrix_last_sync_timestamp


@contextmanager
def hubspot_housekeeping_manager(user, config, metrics):
    check_token_expiration(user, config)
    check_for_and_ensure_properties(metrics, user)
    yield


def create_base_hubspot_payload(metrics, customer, customer_address):
    data = json.dumps([
        dict(
            email=customer.email,
            properties=[
                dict(property="firstname", value=customer.first_name),
                dict(property="lastname", value=customer.last_name),
                dict(property="company", value=customer.company),
                dict(property="phone", value=customer.phone),
                dict(property="address", value=customer_address.street_1 if customer_address else ''),
                dict(property="city", value=customer_address.city if customer_address else ''),
                dict(property="state", value=customer_address.state if customer_address else ''),
                dict(property="zip", value=customer_address.zip if customer_address else ''),
                dict(property="lifecyclestage", value=_compute_lifecyclestage(metrics))
            ]
        )
    ])
    return json.loads(data)


def metrics_to_hubspot_payload(metrics, customer, customer_address):
    data_json = create_base_hubspot_payload(metrics, customer, customer_address)
    data_json[0]['properties'].extend([*_expand_metrics_properties(metrics)])
    return data_json


def _expand_metrics_properties(metrics):
    for p in metrics.__dir__():
        yield dict(property=p, value=str(metrics[p]))


def _compute_lifecyclestage(metrics):
    return 'customer' if metrics.all_time_total_revenue else 'lead'


class TimelineEventType(Enum):
    OrderCreated = 23271
    OrderStatusChanged = 23272


def base_timeline_event(func):
    def wrapper(**kwargs):
        payload = {
            'id': uuid4().hex,
            'eventTypeId': str(kwargs['event_type'].value),
            'email': kwargs['email']
        }
        del kwargs['event_type']
        payload.update(func(**kwargs))
        return payload
    return wrapper


@base_timeline_event
def create_timeline_event_payload(**template_vars):
    return dict(template_vars)


def filter_allowed_webhook(status):
    def filter_deco(func):
        def wrapper(orders, webhook_data):
            if status in str.lower(webhook_data['scope']):
                return func(orders=orders, webhook_data=webhook_data)
        return wrapper
    return filter_deco


@filter_allowed_webhook('created')
def make_order_created_timeline_event(**kwargs):
    sorted_orders = sorted(kwargs.get('orders'), key=lambda x: x.id)
    customer_email = sorted_orders[-1].billing_address['email']
    latest_order_source = sorted_orders[-1].order_source
    latest_order_id = sorted_orders[-1].id
    latest_order_date = pendulum.parse(str(sorted_orders[-1].date_created)).to_cookie_string()
    latest_order_date_timestamp = (pendulum.parse(str(sorted_orders[-1].date_created)).int_timestamp * 1000)
    return create_timeline_event_payload(
        orderDate=str(latest_order_date),
        orderSource=latest_order_source,
        orderId=str(latest_order_id),
        email=customer_email,
        timestamp=latest_order_date_timestamp,
        event_type=TimelineEventType.OrderCreated,
        id=sha256(bytes(str(latest_order_id)+latest_order_source+str(latest_order_date_timestamp), 'utf-8')).hexdigest()
    )


@filter_allowed_webhook('updated')
def make_order_status_timeline_event(**kwargs):
    sorted_orders = sorted(kwargs.get('orders'), key=lambda x: x.id)
    customer_email = sorted_orders[-1].billing_address['email']
    latest_order_status = sorted_orders[-1].status
    latest_order_id = sorted_orders[-1].id
    latest_status_timestamp = pendulum.fromtimestamp(kwargs.get('webhook_data')['created_at']).int_timestamp * 1000
    latest_order_date_timestamp = (pendulum.parse(str(sorted_orders[-1].date_created)).int_timestamp * 1000)
    return create_timeline_event_payload(
        orderStatus=latest_order_status,
        orderId=latest_order_id,
        email=customer_email,
        timestamp=latest_status_timestamp,
        event_type=TimelineEventType.OrderStatusChanged,
        id=sha256(bytes(str(latest_order_id)+latest_order_status+str(latest_order_date_timestamp), 'utf-8')).hexdigest()
    )


def hubspot_api_delay(delay_in_ms):
    def deco(func):
        def wrapper(*args, **kwargs):
            sleep(delay_in_ms)
            return func(*args, **kwargs)
        return wrapper
    return deco


@hubmetrix_last_sync_timestamp
@hubspot_api_delay(0.250)
def post_batch_to_hubspot(payload, user):
    url = 'https://api.hubapi.com/contacts/v1/contact/batch'
    headers = {'Authorization': 'Bearer {}'.format(user.hs_access_token)}
    return requests.post(url, json=payload, headers=headers)


@hubspot_api_delay(0.250)
def put_timeline_event_to_hubspot(payload, user):
    if payload:
        url = 'https://api.hubapi.com/integrations/v1/{}/timeline/event'.format(user.hs_app_id)
        headers = {'Authorization': 'Bearer {}'.format(user.hs_access_token),
                   'Content Type': 'application/json'}
        return requests.put(url, json=payload, headers=headers)


def put_timeline_events_to_hubspot(payload_iterable, user):
    if payload_iterable:
        for payload in payload_iterable:
            put_timeline_event_to_hubspot(payload, user)


def _expand_properties_for_hs_creation(metrics):
    numeric_field_flags = ['total', 'count']
    datetime_field_flags = ['date']
    count = 0
    data_type = 'string'
    field_type = 'text'
    for p in dir(metrics):
        count += 1
        label = ''.join([val.capitalize() + ' ' for val in p.split('_')])
        for l in p.split('_'):
            if l in numeric_field_flags:
                data_type = 'number'
                field_type = 'number'
                break
            if l in datetime_field_flags:
                data_type = 'date'
                field_type = 'date'
                break
            data_type = 'string'
            field_type = 'text'
        yield {
            'name': p,
            'label': label,
            'description': 'Hubmetrix data field for {}'.format(label),
            'groupName': 'sales_metrics',
            'type': data_type,
            'fieldType': field_type,
            'formField': False,
            'displayOrder': count,
            'options': []
        }


def _ensure_property_group(user):
    url = 'https://api.hubapi.com/properties/v1/contacts/groups'
    headers = {'Authorization': 'Bearer {}'.format(user.hs_access_token),
               'Content Type': 'application/json'}
    payload = {'name': 'sales_metrics', 'displayName': 'Sales Metrics'}
    return requests.post(url, json=payload, headers=headers)


def _ensure_properties(metrics, user):
    url = 'https://api.hubapi.com/properties/v1/contacts/properties'
    headers = {'Authorization': 'Bearer {}'.format(user.hs_access_token),
               'Content Type': 'application/json'}
    props = [*_expand_properties_for_hs_creation(metrics)]
    return_post_val = None
    for payload in props:
        return_post_val = requests.post(url, json=payload, headers=headers)
        if return_post_val.status_code == 409:
            break
    return return_post_val


def check_for_and_ensure_properties(metrics, user):
    if not user.hs_properties_exist:
        group = _ensure_property_group(user)
        props = _ensure_properties(metrics, user)
        allowed_codes = [200, 409]
        if group.status_code in allowed_codes and props.status_code in allowed_codes:
            user.update(actions=[
                AppUser.hs_properties_exist.set(True)]
            )


def check_token_expiration(user, config):
    delta = datetime.now() - pendulum.parse(user.hs_access_token_timestamp)
    if delta.in_seconds() > int(user.hs_expires_in):
        tokens = get_new_tokens(user, config)
        cache_tokens(tokens, user)


def get_new_tokens(user, config):
    url = 'https://api.hubapi.com/oauth/v1/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'}
    payload = 'grant_type=refresh_token&client_id={}&client_secret={}&redirect_uri={}&refresh_token={}'.format(
        config['HS_CLIENT_ID'],
        config['HS_CLIENT_SECRET'],
        config['HS_REDIRECT_URI'],
        user.hs_refresh_token
    )
    return requests.post(url, data=payload, headers=headers).json()


def cache_tokens(token_json, user):
    access_token = token_json['access_token']
    refresh_token = token_json['refresh_token']
    expires_in = str(token_json['expires_in'])
    if access_token and refresh_token and expires_in:
        user.update(actions=[
            AppUser.hs_access_token.set(access_token),
            AppUser.hs_refresh_token.set(refresh_token),
            AppUser.hs_expires_in.set(expires_in),
            AppUser.hs_access_token_timestamp.set(str(datetime.now()))]
        )
