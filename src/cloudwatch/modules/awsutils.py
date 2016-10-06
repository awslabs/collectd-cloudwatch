from datetime import datetime


def get_aws_timestamp():
    """
    Returns timestamp expressed in the format YYYYMMDDThhmmssZ,
    as specified in the ISO 8601 standard.
    """
    return datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')


def get_datestamp():
    return datetime.utcnow().strftime('%Y%m%d') 