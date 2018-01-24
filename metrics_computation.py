import pandas as pd
import pendulum
import math


def _extract_dates(itrable, date_column):
    return [item[date_column] for item in itrable]


def _get_date_index(itrable):
    return pd.to_datetime(itrable)


def _get_dataframe(itrable):
    dates = _extract_dates(itrable, 'date_created')
    idx = _get_date_index(dates)
    cols = ['date_created', 'status', 'total_inc_tax', 'id']

    df = pd.DataFrame(data=itrable, index=idx, columns=cols)
    del df['date_created']
    df['total_inc_tax'] = pd.to_numeric(df['total_inc_tax'])

    return df


def compute_metrics(order_iter, app_user, customer):
    df = _get_dataframe(order_iter)
    sum_col = 'total_inc_tax'
    metrics = Metrics(app_user.hs_hub_id, customer.email, dataframe=df, sum_column=sum_col)

    return metrics


class Metrics(object):
    """
    Ecommerce metrics for pushing to HubSpot.
    """

    def __init__(self, hub_id, email, dataframe, sum_column=None):
        self.hub_id = hub_id
        self.email = email
        self.now = pendulum.now()
        self.dataframe = dataframe
        self.sum_column = sum_column
        self.this_month = '{}-{}'.format(self.now.year, self.now.month)
        self.last_month = '{}-{}'.format(self.now.subtract(months=1).year, self.now.subtract(months=1).month)
        self.this_year = '{}'.format(self.now.year)
        self.last_year = '{}'.format(self.now.subtract(years=1).year)
        self.monthly_df_sum = self.dataframe.resample('M')[sum_column].sum()
        self.monthly_df_sum_change = self.monthly_df_sum.pct_change()
        self.monthly_df_count = self.dataframe.resample('M')[sum_column].count()
        self.monthly_df_count_change = self.monthly_df_count.pct_change()
        self.yearly_df_sum = self.dataframe.resample('Y')[sum_column].sum()
        self.yearly_df_sum_change = self.yearly_df_sum.pct_change()
        self.yearly_df_count = self.dataframe.resample('Y')[sum_column].count()
        self.yearly_df_count_change = self.yearly_df_count.pct_change()
        self.all_time_df_total = self.dataframe[sum_column].sum()
        self.all_time_df_count = self.dataframe[sum_column].count()

    @property
    def latest_order_date(self):
        return pendulum.parse(str(self.dataframe.index[-1])).with_time_from_string('0').int_timestamp * 1000

    @property
    def latest_order_timestamp(self):
        return pendulum.parse(str(self.dataframe.index[-1])).to_cookie_string()

    @property
    def latest_order_id(self):
        return self.dataframe.id[-1]

    @property
    def latest_order_status(self):
        return self.dataframe.status[-1]

    @property
    def monthly_total(self):
        monthly = self.monthly_df_sum.get(self.this_month)
        if hasattr(monthly, 'item'):
            return monthly.item()
        return 0.0

    @property
    def last_month_total(self):
        monthly_previous = self.monthly_df_sum.get(self.last_month)
        if hasattr(monthly_previous, 'item'):
            return monthly_previous.item()
        return 0.0

    @property
    def monthly_total_percent_change(self):
        monthly_change = self.monthly_df_sum_change.get(self.this_month)
        if hasattr(monthly_change, 'item'):
            change = monthly_change.item()
            if not math.isnan(change):
                return round(change * 100, 2)
        return 0

    @property
    def monthly_order_count(self):
        count_monthly = self.monthly_df_count.get(self.this_month)
        if hasattr(count_monthly, 'item'):
            return count_monthly.item()
        return 0

    @property
    def last_month_order_count(self):
        count_monthly_previous = self.monthly_df_count.get(self.last_month)
        if hasattr(count_monthly_previous, 'item'):
            return count_monthly_previous.item()
        return 0

    @property
    def last_month_order_count_percent_change(self):
        monthly_count_change = self.monthly_df_count_change.get(self.this_month)
        if hasattr(monthly_count_change, 'item'):
            change = monthly_count_change.item()
            if not math.isnan(change):
                return round(change * 100, 2)
        return 0

    @property
    def yearly_total(self):
        yearly = self.yearly_df_sum.get(self.this_year)
        if hasattr(yearly, 'item'):
            return yearly.item()
        return 0.0

    @property
    def last_year_total(self):
        yearly_previous = self.yearly_df_sum.get(self.last_year)
        if hasattr(yearly_previous, 'item'):
            return yearly_previous.item()
        return 0.0

    @property
    def yearly_percent_change(self):
        yearly_change = self.yearly_df_sum_change.get(self.this_year)
        if hasattr(yearly_change, 'item'):
            change = yearly_change.item()
            if not math.isnan(change):
                return round(change * 100, 2)
        return 0

    @property
    def yearly_order_count(self):
        count_yearly = self.yearly_df_count.get(self.this_year)
        if hasattr(count_yearly, 'item'):
            return count_yearly.item()
        return 0

    @property
    def last_year_order_count(self):
        count_yearly_previous = self.yearly_df_count.get(self.last_year)
        if hasattr(count_yearly_previous, 'item'):
            return count_yearly_previous.item()
        return 0

    @property
    def yearly_order_count_percent_change(self):
        yearly_count_change = self.yearly_df_count_change.get(self.this_year)
        if hasattr(yearly_count_change, 'item'):
            change = yearly_count_change.item()
            if not math.isnan(change):
                return round(change * 100, 2)
        return 0

    @property
    def all_time_total_revenue(self):
        total = self.all_time_df_total
        if hasattr(total, 'item'):
            return round(total.item(), 2)
        return 0.0

    @property
    def all_time_order_count(self):
        total_count = self.all_time_df_count
        if hasattr(total_count, 'item'):
            return total_count.item()
        return 0

    def __iter__(self):
        return iter([{value: self[value]} for value in self.__dir__()])

    def __dir__(self):
        return ['all_time_order_count', 'all_time_total_revenue', 'last_month_order_count',
                'last_month_order_count_percent_change', 'last_month_total', 'last_year_order_count',
                'last_year_total', 'latest_order_date', 'latest_order_timestamp', 'latest_order_id',
                'latest_order_status', 'monthly_order_count', 'monthly_total', 'monthly_total_percent_change',
                'yearly_order_count', 'yearly_order_count_percent_change', 'yearly_percent_change',
                'yearly_total']

    def __getitem__(self, item):
        return self.__getattribute__(item)

    def __repr__(self):
        return ('Metrics({!r}, {!r}, dataframe_id: {}, {!r})'.format(self.hub_id, self.email, id(self.dataframe),
                                                                     self.sum_column))
