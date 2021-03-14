import sys
from io import StringIO
from contextlib import contextmanager


@contextmanager
def output_catcher():
    out, err = StringIO(), StringIO()
    try:
        sys.stdout = out
        sys.stderr = err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
