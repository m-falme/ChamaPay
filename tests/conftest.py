import pytest

from chamapay import create_app, at
from chamapay.models import db
from chamapay.seed import seed


@pytest.fixture
def app(monkeypatch):
    monkeypatch.delenv("AT_API_KEY", raising=False)
    at._client.clear()
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                      "DASHBOARD_PASSWORD": "pw", "SECRET_KEY": "t"})
    with app.app_context():
        seed()
        yield app
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def ussd(client):
    def call(phone, text=""):
        r = client.post("/ussd", data={"sessionId": "s1", "serviceCode": "*384*123#",
                                       "phoneNumber": phone, "text": text})
        assert r.status_code == 200 and r.mimetype == "text/plain"
        return r.get_data(as_text=True)
    return call


class FakeSMS:
    def __init__(self):
        self.sent = []

    def send(self, message, recipients, sender_id=None):
        self.sent.append((message, list(recipients)))
        return {"SMSMessageData": {"Recipients": [
            {"number": r, "status": "Success", "messageId": f"ATX{len(self.sent)}{i}"}
            for i, r in enumerate(recipients)]}}


@pytest.fixture
def fake_at(monkeypatch):
    fake = type("SDK", (), {})()
    fake.SMS = FakeSMS()
    monkeypatch.setenv("AT_API_KEY", "test")
    at._client["sdk"] = fake
    yield fake
    at._client.clear()
