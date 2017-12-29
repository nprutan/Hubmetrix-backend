from dynamodb_utils import *
from datetime import datetime
import requests
import json


def metrics_to_hubspot_payload(metrics, customer, customer_address):
    data = json.dumps([
        dict(
            email=customer.email,
            properties=[
                dict(property="firstname", value=customer.first_name),
                dict(property="lastname", value=customer.last_name),
                dict(property="company", value=customer.company),
                dict(property="phone", value=customer.phone),
                dict(property="address", value=customer_address.street_1),
                dict(property="city", value=customer_address.city),
                dict(property="state", value=customer_address.state),
                dict(property="zip", value=customer_address.zip)
            ]
         )
    ])

    data_json = json.loads(data)
    data_json[0]['properties'].extend([*_expand_metrics_properties(metrics)])

    return data_json


def _expand_metrics_properties(metrics):
    for p in metrics.__dir__():
        yield dict(property=p, value=str(metrics[p]))


def post_batch_to_hubspot(payload, app_user):
    url = 'https://api.hubapi.com/contacts/v1/contact/batch'
    headers = {'Authorization': 'Bearer {}'.format(app_user.hs_access_token)}
    r = requests.post(url, json=payload, headers=headers)
    return r.text


def check_token_expiration(app_user, config):
    delta = datetime.now() - app_user.hs_access_token_timestamp
    if delta.seconds > app_user.hs_expires_in:
        tokens = get_new_tokens(app_user, config)
        cache_tokens(tokens, app_user)


def get_new_tokens(app_user, config):
    url = 'https://api.hubapi.com/oauth/v1/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'}
    payload = 'grant_type=refresh_token&client_id={}&client_secret={}&redirect_uri={}&refresh_token={}'.format(
        config['HS_CLIENT_ID'],
        config['HS_CLIENT_SECRET'],
        config['HS_REDIRECT_URI'],
        app_user.hs_refresh_token
        )
    return requests.post(url, data=payload, headers=headers).json()


def cache_tokens(token_json, app_user):
    access_token = token_json['access_token']
    refresh_token = token_json['refresh_token']
    expires_in = str(token_json['expires_in'])
    if access_token and refresh_token and expires_in:
        app_user.update(actions=[
            AppUser.hs_access_token.set(access_token),
            AppUser.hs_refresh_token.set(refresh_token),
            AppUser.hs_expires_in.set(expires_in)]
        )


def _expand_properties_for_hs_creation(metrics):
    numeric_field_flags = ['total', 'count']
    datetime_field_flags = ['datetime']
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
                data_type = 'datetime'
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


def _ensure_property_group(app_user):
    url = 'https://api.hubapi.com/properties/v1/contacts/groups'
    headers = {'Authorization': 'Bearer {}'.format(app_user.hs_access_token),
               'Content Type': 'application/json'}
    payload = {'name': 'sales_metrics', 'displayName': 'Sales Metrics'}
    return requests.post(url, json=payload, headers=headers)


def _ensure_properties(metrics, app_user):
    url = 'https://api.hubapi.com/properties/v1/contacts/properties'
    headers = {'Authorization': 'Bearer {}'.format(app_user.hs_access_token),
               'Content Type' : 'application/json'}
    props = [*_expand_properties_for_hs_creation(metrics)]
    return_post_val = None
    for payload in props:
        return_post_val = requests.post(url, json=payload, headers=headers).text
    return return_post_val


def check_for_and_ensure_properties(metrics, app_user):
    if not app_user.hs_properties_exist:
        _ensure_property_group(app_user)
        _ensure_properties(metrics, app_user)

