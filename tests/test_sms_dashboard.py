from chamapay import services
from chamapay.models import db, Chama, Contribution, SmsLog


def test_sms_with_mocked_client(app, fake_at):
    services.send_sms(["+254711000001", "+254711000002"], "hello", kind="test")
    assert fake_at.SMS.sent == [("hello", ["+254711000001", "+254711000002"])]
    logs = SmsLog.query.filter_by(kind="test").all()
    assert {l.status for l in logs} == {"Success"} and all(l.message_id for l in logs)


def test_sms_error_does_not_crash(app, fake_at):
    def boom(*a, **k):
        raise RuntimeError("network down")
    fake_at.SMS.send = boom
    services.send_sms("+254711000001", "x", kind="test")
    assert SmsLog.query.filter_by(kind="test").first().status.startswith("failed")


def test_reminders_target_unpaid(app, fake_at):
    sent = services.send_reminders(Chama.query.first())
    assert len(sent) == 4  # 3 late + 1 pending
    assert len(fake_at.SMS.sent) == 4


def test_confirm_sends_receipt(app, fake_at):
    c = Contribution.query.filter_by(status="pending").first()
    services.confirm_contribution(c)
    assert c.status == "confirmed" and "CONFIRMED" in fake_at.SMS.sent[-1][0]


def test_delivery_callback(client, app, fake_at):
    services.send_sms("+254711000001", "x", kind="test")
    mid = SmsLog.query.filter_by(kind="test").first().message_id
    assert client.post("/sms/delivery", data={"id": mid, "status": "Success"}).status_code == 200
    assert SmsLog.query.filter_by(message_id=mid).first().delivery_status == "Success"


def test_health(client):
    assert client.get("/health").json == {"status": "ok"}


def test_dashboard_login_and_actions(client, app):
    assert client.get("/").status_code == 302
    assert b"Wrong" in client.post("/login", data={"password": "no"}, follow_redirects=True).data
    r = client.post("/login", data={"password": "pw"}, follow_redirects=True)
    assert b"Umoja Women Group" in r.data and b"Ann Nduta" in r.data and b"L1" in r.data
    r = client.post("/remind", follow_redirects=True)
    assert b"4 member(s)" in r.data
    c = Contribution.query.filter_by(status="pending").first()
    client.post(f"/contributions/{c.id}/confirm")
    assert db.session.get(Contribution, c.id).status == "confirmed"


def test_voice_disabled_by_default(app, monkeypatch):
    monkeypatch.delenv("VOICE_ENABLED", raising=False)
    res = services.voice_reminders(Chama.query.first())
    assert set(res.values()) == {"voice disabled"}


def test_voice_xml(client):
    r = client.post("/voice")
    assert r.mimetype == "application/xml" and b"<Say" in r.data


def test_dashboard_shows_failed_sms_and_kes(client, app, fake_at):
    fake_at.SMS.send = lambda *a, **k: {"SMSMessageData": {"Message": "x", "Recipients": [
        {"number": "+254711000001", "status": "InvalidPhoneNumber", "messageId": "None"}]}}
    services.send_sms("+254711000001", "x", kind="test")
    assert SmsLog.query.filter_by(kind="test").first().status == "failed: InvalidPhoneNumber"
    client.post("/login", data={"password": "pw"})
    html = client.get("/").get_data(as_text=True)
    assert "failed: InvalidPhoneNumber" in html and "KES 4,000" in html


def test_dashboard_empty_states(client, app):
    from chamapay.models import Loan, Vote
    Vote.query.delete(); Loan.query.delete(); db.session.commit()
    client.post("/login", data={"password": "pw"})
    html = client.get("/").get_data(as_text=True)
    assert "No loan requests yet" in html and "No SMS sent yet" in html and "Demo mode" in html


def test_flash_after_remind(client, app):
    client.post("/login", data={"password": "pw"})
    assert b"Reminder SMS" in client.post("/remind", follow_redirects=True).data
