import pytest

@pytest.mark.django_db
def test_pytest_is_working():
    assert 1 + 1 == 2
