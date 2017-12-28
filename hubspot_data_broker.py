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
    for d in _expand_metrics_properties(metrics):
        data_json[0]['properties'].append(d)

    return data_json


def _expand_metrics_properties(metrics):
    for p in metrics.__dir__():
        yield dict(property=p, value=metrics[p])