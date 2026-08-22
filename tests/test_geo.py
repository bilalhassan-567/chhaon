import pytest

from app.services.geo import haversine_meters


def test_same_point_is_zero_distance():
    assert haversine_meters(31.55, 74.34, 31.55, 74.34) == 0


def test_symmetric():
    a = haversine_meters(31.55, 74.34, 31.48, 74.32)
    b = haversine_meters(31.48, 74.32, 31.55, 74.34)
    assert a == pytest.approx(b)


def test_one_degree_latitude_is_about_111km():
    distance = haversine_meters(0, 0, 1, 0)
    assert 110_000 < distance < 112_000
