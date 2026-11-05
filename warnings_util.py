"""Warnings that point at the caller's code, not at library internals."""

import os
import sys
import warnings

_PACKAGE = os.path.dirname(os.path.abspath(__file__))
_TESTS = os.path.join(_PACKAGE, 'tests')


def _internal(filename: str) -> bool:
    path = os.path.abspath(filename)
    return path.startswith(_PACKAGE + os.sep) and not path.startswith(_TESTS + os.sep)


def warn_caller(message: str, category=UserWarning):
    """warnings.warn with the stack level of the first frame outside the library."""
    level, frame = 2, sys._getframe(1)          # level 1 is this function, 2 its caller, ...
    while frame is not None and _internal(frame.f_code.co_filename):
        frame, level = frame.f_back, level + 1
    warnings.warn(message, category, stacklevel=level)
