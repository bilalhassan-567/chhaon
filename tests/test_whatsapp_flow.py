from app.services.whatsapp_flow import handle_incoming_message


def test_first_message_gets_welcome_and_location_prompt(report_store):
    reply = handle_incoming_message("whatsapp:+9230000001", "hi")
    assert "share your location" in reply
    assert "anonymous" in reply


def test_full_flow_via_location_pin(report_store):
    handle_incoming_message("whatsapp:+9230000002", "hi")
    reply = handle_incoming_message(
        "whatsapp:+9230000002", "", latitude="31.4805", longitude="74.3232"
    )
    assert "Model Town" in reply
    assert "What happened" in reply

    reply = handle_incoming_message("whatsapp:+9230000002", "2")
    assert "Logged: model_town, heatstroke" in reply
    assert "not a verified medical or legal record" in reply

    reports = report_store.list_since()
    assert len(reports) == 1
    assert reports[0].zone_id == "model_town"
    assert reports[0].lat == 31.4805


def test_full_flow_via_typed_zone_name_fallback(report_store):
    handle_incoming_message("whatsapp:+9230000003", "hi")
    reply = handle_incoming_message("whatsapp:+9230000003", "Gulberg")
    assert "Gulberg" in reply

    reply = handle_incoming_message("whatsapp:+9230000003", "3")
    assert "Logged: gulberg, death" in reply

    reports = report_store.list_since()
    assert reports[0].lat is None
    assert reports[0].geo_source.value == "zone_name"


def test_unrecognized_zone_name_reprompts_without_advancing(report_store):
    handle_incoming_message("whatsapp:+9230000004", "hi")
    reply = handle_incoming_message("whatsapp:+9230000004", "Narnia")
    assert "didn't recognize that area" in reply

    # Still awaiting location — a valid zone name now should proceed normally.
    reply = handle_incoming_message("whatsapp:+9230000004", "Model Town")
    assert "Model Town" in reply
    assert "What happened" in reply


def test_invalid_incident_choice_reprompts_without_advancing(report_store):
    handle_incoming_message("whatsapp:+9230000005", "hi")
    handle_incoming_message("whatsapp:+9230000005", "Model Town")
    reply = handle_incoming_message("whatsapp:+9230000005", "9")
    assert "reply with a number 1-4" in reply.lower()

    reply = handle_incoming_message("whatsapp:+9230000005", "1")
    assert "Logged: model_town, heat_exhaustion" in reply


def test_two_different_reporters_do_not_share_conversation_state(report_store):
    handle_incoming_message("whatsapp:+9230000006", "hi")
    handle_incoming_message("whatsapp:+9230000007", "hi")

    # Reporter 7 answers first — must not affect reporter 6's stage.
    handle_incoming_message("whatsapp:+9230000007", "Model Town")
    reply = handle_incoming_message("whatsapp:+9230000006", "Gulberg")
    assert "Gulberg" in reply
    assert "What happened" in reply


def test_alert_on_via_location_pin_registers(report_store, registration_store):
    reply = handle_incoming_message("whatsapp:+9230000010", "ALERT ON")
    assert "Which area" in reply

    reply = handle_incoming_message(
        "whatsapp:+9230000010", "", latitude="31.4805", longitude="74.3232"
    )
    assert "Model Town" in reply
    assert "STOP" in reply
    assert registration_store.list_for_zone("model_town") == ["whatsapp:+9230000010"]


def test_alert_on_via_typed_zone_name(report_store, registration_store):
    handle_incoming_message("whatsapp:+9230000011", "alert on")  # case-insensitive
    handle_incoming_message("whatsapp:+9230000011", "Gulberg")
    assert registration_store.list_for_zone("gulberg") == ["whatsapp:+9230000011"]


def test_stop_unregisters_every_zone_for_that_phone(report_store, registration_store):
    registration_store.register("whatsapp:+9230000012", "model_town")
    registration_store.register("whatsapp:+9230000012", "gulberg")

    reply = handle_incoming_message("whatsapp:+9230000012", "STOP")

    assert "unsubscribed" in reply.lower()
    assert registration_store.zones_with_registrations() == set()


def test_alert_on_interrupts_an_in_progress_report_without_creating_one(report_store, registration_store):
    handle_incoming_message("whatsapp:+9230000013", "hi")  # starts the report flow
    reply = handle_incoming_message("whatsapp:+9230000013", "ALERT ON")  # switches flows mid-way
    assert "Which area" in reply

    reply = handle_incoming_message("whatsapp:+9230000013", "Model Town")
    assert "Model Town" in reply
    assert "STOP" in reply
    assert report_store.list_since() == []  # the abandoned report flow produced nothing


def test_alert_zone_unrecognized_reprompts_without_registering(report_store, registration_store):
    handle_incoming_message("whatsapp:+9230000014", "ALERT ON")
    reply = handle_incoming_message("whatsapp:+9230000014", "Narnia")
    assert "didn't recognize" in reply
    assert registration_store.zones_with_registrations() == set()


def test_stop_with_no_existing_registration_is_still_safe(report_store, registration_store):
    reply = handle_incoming_message("whatsapp:+9230000015", "STOP")
    assert "unsubscribed" in reply.lower()
