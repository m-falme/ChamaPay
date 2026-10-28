import pytest

from chamapay import ussd as ussd_mod
from chamapay.models import Contribution, Loan, SmsLog, current_period
from chamapay.services import month_label

TREASURER, MARY, FAITH, AGNES, LUCY, ANN = (
    "+254711000001", "+254711000002", "+254711000003", "+254711000005", "+254711000006", "+254711000008")


def body(r):
    return r[4:]


def test_unknown_number(ussd):
    r = ussd("+254700999999")
    assert r.startswith("END") and "not registered" in r


def test_missing_phone(ussd):
    assert "phone number" in ussd("")


def test_main_menu(ussd):
    r = ussd(MARY)
    assert r.startswith("CON") and "1 My balance" in r and "6 " not in r
    assert "6 Confirm" in ussd(TREASURER)


def test_empty_and_star_text_shows_menu(ussd):
    assert "1 My balance" in ussd(MARY, "")
    assert "1 My balance" in ussd(MARY, "**")


def test_balance(ussd):
    r = ussd(MARY, "1")
    assert r.startswith("END") and "KES 4,000" in r and "PAID" in r
    assert "NOT PAID" in ussd(ANN, "1")
    assert "PENDING" in ussd(AGNES, "1")


def test_who_paid(ussd):
    r = ussd(MARY, "2")
    assert "4/8 paid" in r and "Ann" in r.split("Not yet:")[1]


def test_record_contribution_flow(ussd):
    assert ussd(ANN, "3").startswith("CON")
    assert "1 Confirm" in ussd(ANN, "3*1000")
    r = ussd(ANN, "3*1000*1")
    assert r.startswith("END") and "Recorded" in r and "Ref C" in r
    c = Contribution.query.order_by(Contribution.id.desc()).first()
    assert c.status == "pending" and c.period == current_period() and c.amount == 1000
    sms = SmsLog.query.filter_by(to=ANN, kind="receipt").first()
    assert sms.status == "not sent (no key)"
    for part in ("KES 1,000", "Umoja Women Group", month_label(current_period()), "KES 2,000", f"Ref C{c.id}"):
        assert part in sms.message
    assert len(sms.message) <= 160


@pytest.mark.parametrize("amt,msg", [("abc", "numbers only"), ("000", "more than 0"),
                                     ("-50", "negative"), ("1000000", "too large")])
def test_bad_amounts(ussd, amt, msg):
    r = ussd(ANN, f"3*{amt}")
    assert r.startswith("CON") and msg in r


def test_cancel_and_bad_confirm(ussd):
    assert "Cancelled" in ussd(ANN, "3*500*2")
    assert "Invalid choice" in ussd(ANN, "3*500*9")
    assert Contribution.query.filter_by(amount=500).count() == 0


def test_back_and_home_navigation(ussd):
    # bad amount, back, then good amount
    assert "1 Confirm" in ussd(ANN, "3*abc*0*1000")
    # back from contribution screen to main menu
    assert "1 My balance" in ussd(ANN, "3*0")
    # 00 resets to main menu, then option 1
    assert "Savings" in ussd(ANN, "3*1000*00*1")
    # extra back on empty stack is harmless
    assert "1 My balance" in ussd(ANN, "0*0")


def test_invalid_top_level(ussd):
    assert "Invalid choice" in ussd(MARY, "9")
    assert "Invalid choice" in ussd(MARY, "6")  # not treasurer


def test_treasurer_confirms(ussd):
    assert "Agnes" in ussd(TREASURER, "6")
    assert "Invalid choice" in ussd(TREASURER, "6*9")
    assert "Confirmed" in ussd(TREASURER, "6*1")
    assert "5/8 paid" in ussd(MARY, "2")
    assert "No payments" in ussd(TREASURER, "6")


def test_request_loan(ussd):
    assert "Group pool" in ussd(ANN, "4")
    assert "School fees" in ussd(ANN, "4*2000")
    assert "Invalid choice" in ussd(ANN, "4*2000*7")
    r = ussd(ANN, "4*2000*3")
    assert "sent" in r
    loan = Loan.query.order_by(Loan.id.desc()).first()
    assert loan.reason == "Business" and loan.status == "pending"
    assert SmsLog.query.filter_by(kind="loan_alert").count() == 7
    assert "already have a loan" in ussd(ANN, "4")


def test_loan_larger_than_pool(ussd):
    assert "too large" in ussd(ANN, "4*999999")


def test_vote_approves_loan(ussd):
    assert "Faith" in ussd(ANN, "5")
    assert "Invalid choice" in ussd(ANN, "5*4")
    assert "1 Approve" in ussd(ANN, "5*1")
    assert "Invalid choice" in ussd(ANN, "5*1*3")
    r = ussd(ANN, "5*1*1")
    assert "Vote recorded" in r and "APPROVED" not in r
    assert "APPROVED" in ussd(LUCY, "5*1*1")
    assert Loan.query.filter_by(reason="School fees").first().status == "approved"
    assert SmsLog.query.filter_by(kind="loan_outcome").count() == 8
    assert "No pending loans" in ussd(ANN, "5")


def test_already_voted_and_own_loan(ussd):
    assert "already voted" in ussd(MARY, "5")
    assert "No pending loans" in ussd(FAITH, "5")


def test_vote_rejects_loan(ussd):
    for p in ["+254711000005", LUCY, "+254711000007"]:
        ussd(p, "5*1*2")
    assert Loan.query.filter_by(reason="School fees").first().status == "rejected"


@pytest.mark.parametrize("phone,text", [(TREASURER, ""), (TREASURER, "6"), (MARY, "1"), (MARY, "2"),
                                        (ANN, "3"), (ANN, "3*1000"), (ANN, "4"), (ANN, "4*100"),
                                        (ANN, "5"), (ANN, "5*1"), (ANN, "3*abc")])
def test_screens_fit_160(ussd, phone, text):
    assert len(body(ussd(phone, text))) <= 160


def test_exceptions_end_gracefully(ussd, monkeypatch):
    def boom(*a):
        raise RuntimeError("db down")
    monkeypatch.setattr(ussd_mod, "handle", boom)
    r = ussd(MARY, "1")
    assert r.startswith("END") and "went wrong" in r


def test_session_end_callback(client):
    assert client.post("/ussd/end", data={"sessionId": "x", "status": "Failed"}).status_code == 200


def test_phone_normalisation(ussd):
    assert ussd("0711000002").startswith("CON")
    assert ussd(" 254711000002").startswith("CON")
