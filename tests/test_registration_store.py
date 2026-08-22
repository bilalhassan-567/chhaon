from app.storage.registration_store import LocalJSONRegistrationStore


def make_store(tmp_path):
    return LocalJSONRegistrationStore(path=tmp_path / "registrations.json")


def test_register_and_list_for_zone(tmp_path):
    store = make_store(tmp_path)
    store.register("whatsapp:+923000000001", "model_town")
    assert store.list_for_zone("model_town") == ["whatsapp:+923000000001"]
    assert store.list_for_zone("gulberg") == []


def test_register_is_idempotent(tmp_path):
    store = make_store(tmp_path)
    store.register("whatsapp:+923000000001", "model_town")
    store.register("whatsapp:+923000000001", "model_town")
    assert store.list_for_zone("model_town") == ["whatsapp:+923000000001"]


def test_same_phone_can_register_multiple_zones(tmp_path):
    store = make_store(tmp_path)
    store.register("whatsapp:+923000000001", "model_town")
    store.register("whatsapp:+923000000001", "gulberg")
    assert store.zones_with_registrations() == {"model_town", "gulberg"}


def test_unregister_all_removes_every_zone_for_that_phone_only(tmp_path):
    store = make_store(tmp_path)
    store.register("whatsapp:+923000000001", "model_town")
    store.register("whatsapp:+923000000001", "gulberg")
    store.register("whatsapp:+923000000002", "model_town")

    store.unregister_all("whatsapp:+923000000001")

    assert store.list_for_zone("model_town") == ["whatsapp:+923000000002"]
    assert store.list_for_zone("gulberg") == []


def test_zones_with_registrations_empty_initially(tmp_path):
    store = make_store(tmp_path)
    assert store.zones_with_registrations() == set()
