from unittest.mock import patch, MagicMock
from apps.tracking.smoothing import smooth

def test_smoothing():
    prev = (10.0, 10.0)
    curr = (20.0, 20.0)
    # Alpha 0.4. (From smoothing.py)
    # New = prev * 0.6 + curr * 0.4
    # 10*0.6 + 20*0.4 = 6 + 8 = 14
    
    res = smooth(prev, curr)
    
    # Check within float precision
    assert 13.9 < res[0] < 14.1
    assert 13.9 < res[1] < 14.1

def test_smoothing_first_point():
    assert smooth(None, (10, 10)) == (10, 10)
    assert smooth([], (10, 10)) == (10, 10)
