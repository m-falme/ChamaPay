"""Business logic shared by USSD, dashboard and CLI."""
from datetime import date, datetime

from .models import utcnow, db, Chama, Member, Contribution, Loan, Vote, current_period
from .at import send_sms, voice_call

LOAN_REASONS = ["Emergency", "School fees", "Business", "Medical"]


def fmt(n):
    return f"KES {n:,}"


def group_savings(chama):
    ids = [m.id for m in chama.members]
    saved = sum(c.amount for c in Contribution.query.filter(
        Contribution.member_id.in_(ids), Contribution.status == "confirmed"))
    lent = sum(l.amount for l in Loan.query.filter(Loan.member_id.in_(ids), Loan.status == "approved"))
    return saved, lent


def late_members(chama, period=None, today=None):
    """Members without a confirmed contribution this period, once contribution day has passed."""
    period = period or current_period(today)
    return [m for m in chama.members if not m.paid_for(period)]


def record_contribution(member, amount, period=None):
    period = period or current_period()
    c = Contribution(member_id=member.id, amount=amount, period=period, status="pending")
    db.session.add(c)
    db.session.commit()
    send_sms(member.phone, f"ChamaPay: {fmt(amount)} contribution for {period} recorded for "
             f"{member.chama.name}. Awaiting treasurer confirmation. Ref C{c.id}.", kind="receipt")
    return c


def confirm_contribution(contribution):
    if contribution.status == "confirmed":
        return contribution
    contribution.status = "confirmed"
    contribution.confirmed_at = utcnow()
    db.session.commit()
    m = contribution.member
    send_sms(m.phone, f"ChamaPay receipt: {fmt(contribution.amount)} for {contribution.period} confirmed. "
             f"Your total savings: {fmt(m.balance())}. Ref C{contribution.id}.", kind="receipt")
    return contribution


def request_loan(member, amount, reason):
    loan = Loan(member_id=member.id, amount=amount, reason=reason)
    db.session.add(loan)
    db.session.commit()
    others = [m.phone for m in member.chama.members if m.id != member.id]
    send_sms(others, f"ChamaPay {member.chama.name}: {member.name} requests a loan of {fmt(amount)} "
             f"({reason}). Dial the chama code, option 5, to vote. Loan L{loan.id}.", kind="loan_alert")
    return loan


def eligible_voters(loan):
    return [m for m in loan.member.chama.members if m.id != loan.member_id]


def cast_vote(loan, member, approve):
    """Record a vote; decide the loan when a majority of eligible voters agree. Returns outcome or None."""
    if loan.status != "pending" or member.id == loan.member_id:
        return None
    if Vote.query.filter_by(loan_id=loan.id, member_id=member.id).first():
        return None
    db.session.add(Vote(loan_id=loan.id, member_id=member.id, approve=approve))
    db.session.commit()
    yes, no = loan.tally()
    needed = len(eligible_voters(loan)) // 2 + 1
    outcome = "approved" if yes >= needed else "rejected" if no >= needed else None
    if outcome:
        loan.status = outcome
        db.session.commit()
        phones = [m.phone for m in loan.member.chama.members]
        send_sms(phones, f"ChamaPay {loan.member.chama.name}: loan L{loan.id} of {fmt(loan.amount)} for "
                 f"{loan.member.name} was {outcome.upper()} ({yes} yes, {no} no).", kind="loan_outcome")
    return outcome


def send_reminders(chama, period=None):
    period = period or current_period()
    targets = [m for m in chama.members if not m.paid_for(period)]
    day = chama.contribution_day
    for m in targets:
        send_sms(m.phone, f"ChamaPay reminder: hi {m.name.split()[0]}, your {chama.name} contribution of "
                 f"{fmt(chama.contribution_amount)} for {period} is due on day {day}. "
                 f"Dial the chama code, option 3, to record it.", kind="reminder")
    return targets


def voice_reminders(chama, period=None):
    return {m.phone: voice_call(m.phone) for m in late_members(chama, period)}
