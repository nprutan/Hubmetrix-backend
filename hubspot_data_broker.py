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
    return r.json()


# TODO: Change redirect uri /hsauth to accept tokens
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


