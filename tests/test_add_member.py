import pytest

from chamapay.models import Member

# Fictitious test numbers only.
NEW = "0712345678"
NEW_E164 = "+254712345678"


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


def test_cli_positional(runner):
    r = runner.invoke(args=["add-member", "Test One", NEW])
    assert r.exit_code == 0, r.output
    m = Member.query.filter_by(phone=NEW_E164).one()
    assert m.name == "Test One" and not m.is_treasurer


def test_cli_options_and_treasurer(runner):
    r = runner.invoke(args=["add-member", "--name", "Test Two", "--phone", "254712345679", "--treasurer"])
    assert r.exit_code == 0, r.output
    assert Member.query.filter_by(phone="+254712345679").one().is_treasurer


def test_cli_rejects_duplicate_invalid_missing(runner):
    assert runner.invoke(args=["add-member", "Dup", "+254711000001"]).exit_code != 0
    assert "already exists" in runner.invoke(args=["add-member", "Dup", "+254711000001"]).output
    assert runner.invoke(args=["add-member", "--name", "Bad", "--phone", "12345"]).exit_code != 0
    assert runner.invoke(args=["add-member", "--name", "NoPhone"]).exit_code != 0
    assert Member.query.count() == 8


@pytest.fixture
def authed(client):
    client.post("/login", data={"password": "pw"})
    return client


def test_dashboard_form_present(authed):
    assert b'action="/members"' in authed.get("/").data


def test_dashboard_add_member(authed):
    r = authed.post("/members", data={"name": "Form User", "phone": NEW, "treasurer": "on"}, follow_redirects=True)
    assert b"Added Form User" in r.data
    m = Member.query.filter_by(phone=NEW_E164).one()
    assert m.is_treasurer


def test_dashboard_rejects(authed):
    r = authed.post("/members", data={"name": "X", "phone": "+254711000002"}, follow_redirects=True)
    assert b"already exists" in r.data
    r = authed.post("/members", data={"name": "X", "phone": "abc"}, follow_redirects=True)
    assert b"Kenyan mobile" in r.data
    r = authed.post("/members", data={"name": " ", "phone": NEW}, follow_redirects=True)
    assert b"Name is required" in r.data
    assert Member.query.count() == 8


def test_dashboard_add_requires_login(client):
    assert client.post("/members", data={"name": "X", "phone": NEW}).status_code == 302
    assert Member.query.count() == 8


def test_seed_idempotent_and_reset(app):
    from chamapay.seed import seed
    from chamapay.models import Chama, Contribution
    n = Contribution.query.count()
    assert "already present" in seed()
    assert Chama.query.count() == 1 and Contribution.query.count() == n
    Member.query.filter_by(phone="+254711000008").one().name = "Changed"
    from chamapay.models import db
    db.session.commit()
    assert "Seeded" in seed(reset=True)
    assert Member.query.count() == 8 and Contribution.query.count() == n
    assert Member.query.filter_by(phone="+254711000008").one().name == "Ann Nduta"
