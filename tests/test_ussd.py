from chamapay.models import Contribution, Loan, SmsLog, current_period

TREASURER, MARY, FAITH, ANN = "+254711000001", "+254711000002", "+254711000003", "+254711000008"


def test_unknown_number(ussd):
    assert ussd("+254700999999").startswith("END")


def test_main_menu(ussd):
    r = ussd(MARY)
    assert r.startswith("CON") and "1. My balance" in r and "6." not in r
    assert "6. Confirm" in ussd(TREASURER)


def test_balance(ussd):
    r = ussd(MARY, "1")
    assert r.startswith("END") and "KES 4,000" in r and "PAID" in r


def test_who_paid(ussd):
    r = ussd(MARY, "2")
    assert "(4/8)" in r and "Ann" in r.split("Not yet:")[1]


def test_record_contribution_flow(ussd, app):
    assert ussd(ANN, "3").startswith("CON")
    assert "Confirm" in ussd(ANN, "3*1000")
    r = ussd(ANN, "3*1000*1")
    assert r.startswith("END") and "Recorded" in r
    c = Contribution.query.order_by(Contribution.id.desc()).first()
    assert c.status == "pending" and c.period == current_period() and c.amount == 1000
    assert SmsLog.query.filter_by(to=ANN, kind="receipt").first().status == "not sent (no key)"


def test_invalid_amount_and_cancel(ussd):
    assert "Invalid" in ussd(ANN, "3*abc")
    assert "Cancelled" in ussd(ANN, "3*500*2")


def test_treasurer_confirms(ussd):
    r = ussd(TREASURER, "6")
    assert "Agnes" in r
    r = ussd(TREASURER, "6*1")
    assert "Confirmed" in r
    assert "(5/8)" in ussd(MARY, "2")


def test_non_treasurer_cannot_confirm(ussd):
    assert "Invalid option" in ussd(MARY, "6")


def test_request_loan(ussd):
    assert ussd(ANN, "4").startswith("CON")
    assert "School fees" in ussd(ANN, "4*2000")
    r = ussd(ANN, "4*2000*3")
    assert "sent" in r
    loan = Loan.query.order_by(Loan.id.desc()).first()
    assert loan.reason == "Business" and loan.status == "pending"
    assert SmsLog.query.filter_by(kind="loan_alert").count() >= 7


def test_vote_approves_loan(ussd):
    # seeded loan: Faith 5000, votes 2 yes 1 no; 7 voters so 4 needed
    assert "Faith" in ussd(ANN, "5")
    assert "Approve" in ussd(ANN, "5*1")
    r = ussd(ANN, "5*1*1")
    assert "Vote recorded" in r and "APPROVED" not in r
    r = ussd("+254711000006", "5*1*1")
    assert "APPROVED" in r
    assert Loan.query.filter_by(reason="School fees").first().status == "approved"
    assert SmsLog.query.filter_by(kind="loan_outcome").count() == 8


def test_cannot_vote_twice_or_on_own_loan(ussd):
    assert "No loans" in ussd(MARY, "5")  # already voted
    assert "No loans" in ussd(FAITH, "5")  # own loan


def test_vote_rejects_loan(ussd):
    for p in ["+254711000005", "+254711000006", "+254711000007"]:
        ussd(p, "5*1*2")
    assert Loan.query.filter_by(reason="School fees").first().status == "rejected"
