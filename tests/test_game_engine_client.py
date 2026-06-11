from app.integrations.game_engine_client import is_already_processed_payload


def test_already_processed_message() -> None:
    assert is_already_processed_payload({"ok": False, "message": "This bot action has already been processed."})


def test_already_processed_error_code() -> None:
    assert is_already_processed_payload({"ok": False, "errorCode": "BOT_ACTION_ALREADY_PROCESSED"})


def test_other_application_error_is_not_idempotent() -> None:
    assert not is_already_processed_payload({"ok": False, "message": "Illegal raise size"})
