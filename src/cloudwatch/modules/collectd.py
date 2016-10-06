"""
The collectd stub is used to allow testing every part of this module without the need of installing and running collectd.
"""

def register_config(*args):
    pass

def register_init(*args):
    pass

def register_write(*args, **kwargs):
    pass

def debug(msg):
    pass

def info(msg):
    pass

def warning(msg):
    pass

def error(msg):
    pass