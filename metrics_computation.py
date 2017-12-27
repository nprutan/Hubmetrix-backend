import pandas as pd

def _extract_dates(itrable, date_column):
    date_list = []
    for item in itrable:
        date_list.append(item[date_column])
    return date_list


def _get_date_index(itrable):
    return pd.to_datetime(itrable)


def _get_dataframe(itrable):
    dates = _extract_dates(itrable, 'date_created')
    idx = _get_date_index(dates)
    cols = ['date_created', 'status', 'total_inc_tax']

    return pd.DataFrame(data=itrable, index=idx, columns=cols)

def compute_metrics(order_iter):
    df = _get_dataframe(order_iter)



    return df


class Metrics(object):
    """
    Metrics object for computation
    """

    def __init__(self, **kwargs):
        self.all_time_total_revenue = 0.0
        self.all_time_count = 0
        self.monthly = 0.0
        self.montly_change = 0.0
        self.yearly = 0.0
        self.yearly_change = 0.0
        self.monthly_count = 0
        self.monthly_count_change = 0.0
        self.yearly_count = 0
        self.yearly_count_change = 0.0
        self.latest_order_id = None
        self.latest_order_status = None


    def __iter__(self):
        return iter(self)

    def __repr__(self):
        return 'Metrics({!r})'.format(self.__dict__)