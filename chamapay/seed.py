from datetime import date, datetime

from .models import utcnow, db, Chama, Member, Contribution, Loan, Vote, SmsLog

MEMBERS = [
    ("Grace Wanjiku", "+254711000001", True),
    ("Mary Akinyi", "+254711000002", False),
    ("Faith Njeri", "+254711000003", False),
    ("Esther Muthoni", "+254711000004", False),
    ("Agnes Chebet", "+254711000005", False),
    ("Lucy Wambui", "+254711000006", False),
    ("Joyce Atieno", "+254711000007", False),
    ("Ann Nduta", "+254711000008", False),
]


def _periods(n, today):
    y, m = today.year, today.month
    out = []
    for _ in range(n):
        out.append(f"{y}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


def seed(reset=False, today=None):
    today = today or date.today()
    if reset:
        db.session.rollback()
        db.session.expunge_all()
        db.drop_all()
        db.create_all()
    if Chama.query.filter_by(name="Umoja Women Group").first():
        return "Demo data already present (use --reset to reload)."
    chama = Chama(name="Umoja Women Group", contribution_amount=1000, contribution_day=5)
    db.session.add(chama)
    db.session.flush()
    members = []
    for name, phone, tr in MEMBERS:
        m = Member(chama_id=chama.id, name=name, phone=phone, is_treasurer=tr)
        db.session.add(m)
        members.append(m)
    db.session.flush()
    *past, now = _periods(4, today)
    for p in past:
        for i, m in enumerate(members):
            if p == past[-1] and i == 7:  # Ann missed last month
                continue
            db.session.add(Contribution(member_id=m.id, amount=1000, period=p, status="confirmed",
                                        confirmed_at=utcnow()))
    # this month: 4 confirmed, 1 pending, 3 late
    for m in members[:4]:
        db.session.add(Contribution(member_id=m.id, amount=1000, period=now, status="confirmed",
                                    confirmed_at=utcnow()))
    db.session.add(Contribution(member_id=members[4].id, amount=1000, period=now, status="pending"))
    loan = Loan(member_id=members[2].id, amount=5000, reason="School fees")
    db.session.add(loan)
    db.session.flush()
    db.session.add(Vote(loan_id=loan.id, member_id=members[0].id, approve=True))
    db.session.add(Vote(loan_id=loan.id, member_id=members[1].id, approve=True))
    db.session.add(Vote(loan_id=loan.id, member_id=members[3].id, approve=False))
    old = Loan(member_id=members[5].id, amount=3000, reason="Medical", status="approved")
    db.session.add(old)
    db.session.flush()
    for m in members[:4]:  # the earlier loan was approved by majority
        db.session.add(Vote(loan_id=old.id, member_id=m.id, approve=True))
    db.session.commit()
    return f"Seeded '{chama.name}' with {len(members)} members (periods {past[0]}..{now})."
