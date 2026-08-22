from app.services.zones import find_zone_by_name, nearest_zone


def test_nearest_zone_matches_exact_centroid():
    zone = nearest_zone(31.4805, 74.3232)  # Model Town's own centroid
    assert zone.id == "model_town"


def test_nearest_zone_picks_closest_of_two_neighbours():
    # Slightly closer to Gulberg's centroid (31.5085, 74.3505) than Shadman's (31.5460, 74.3280)
    zone = nearest_zone(31.51, 74.35)
    assert zone.id == "gulberg"


def test_find_zone_by_name_case_insensitive():
    assert find_zone_by_name("model town").id == "model_town"
    assert find_zone_by_name("MODEL TOWN").id == "model_town"


def test_find_zone_by_name_matches_by_id():
    assert find_zone_by_name("walled_city").id == "walled_city"


def test_find_zone_by_name_partial_match():
    assert find_zone_by_name("gulberg").id == "gulberg"


def test_find_zone_by_name_unrecognized_returns_none():
    assert find_zone_by_name("Narnia") is None


def test_find_zone_by_name_empty_string_returns_none():
    assert find_zone_by_name("   ") is None
