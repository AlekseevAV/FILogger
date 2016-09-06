import pytest
from viewer import func_to_test


def test_func_to_test():
    assert func_to_test(2) == 4
