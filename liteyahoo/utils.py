import datetime, time


def convert_to_timestamp(x):
    if isinstance(x, datetime.datetime):
        return int(time.mktime(x.timetuple()))
    elif isinstance(x, str):
        return convert_to_timestamp(datetime.datetime.strptime(x, '%Y-%m-%d'))
    else:
        raise ValueError("Please input date in format datetime.datetime or str '%Y-%m-%d'")


def proxy_setter(proxy):
    if isinstance(proxy, dict) and "https" in proxy:
        proxy = proxy["https"]
        return {"https": proxy}
