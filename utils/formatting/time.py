# Utility to format datetime strings
def datetime_string_converter(raw_datetime):
    if raw_datetime:
        return str(raw_datetime)[:10]
    else:
        return None