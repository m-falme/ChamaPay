"""Africa's Talking USSD callback. AT POSTs sessionId, serviceCode, phoneNumber, text.
Reply with plain text starting with CON (continue) or END (finish)."""
from flask import Blueprint, request, Response

from .models import Member, Loan, Contribution, Vote, current_period
from . import services as s

bp = Blueprint("ussd", __name__)

MAX_AMOUNT = 1_000_000


def con(t):
    return Response("CON " + t, mimetype="text/plain")


def end(t):
    return Response("END " + t, mimetype="text/plain")


def _amount(v):
    return int(v) if v.isdigit() and 0 < int(v) <= MAX_AMOUNT else None


def _votable(member):
    ids = [m.id for m in member.chama.members]
    voted = {v.loan_id for v in Vote.query.filter_by(member_id=member.id)}
    return [l for l in Loan.query.filter(Loan.member_id.in_(ids), Loan.status == "pending",
                                         Loan.member_id != member.id).order_by(Loan.id)
            if l.id not in voted]


def _pending_contribs(member):
    ids = [m.id for m in member.chama.members]
    return Contribution.query.filter(Contribution.member_id.in_(ids),
                                     Contribution.status == "pending").order_by(Contribution.id).limit(5).all()


def normalize_phone(raw):
    p = raw.replace(" ", "").replace("-", "")
    if p.startswith("254"):
        p = "+" + p
    elif p.startswith("0") and len(p) == 10:
        p = "+254" + p[1:]
    return p


@bp.post("/ussd")
def ussd():
    phone = normalize_phone(request.values.get("phoneNumber", ""))
    text = request.values.get("text", "").strip()
    member = Member.query.filter_by(phone=phone).first()
    if not member:
        return end("This number is not registered with any ChamaPay group. Ask your treasurer to add you.")
    parts = text.split("*") if text else []
    chama = member.chama
    period = current_period()

    if not parts:
        menu = (f"{chama.name}\nHi {member.name.split()[0]}\n1. My balance\n2. Who paid this month\n"
                "3. Record contribution\n4. Request loan\n5. Vote on loans")
        if member.is_treasurer:
            menu += "\n6. Confirm contributions"
        return con(menu)

    choice, rest = parts[0], parts[1:]

    if choice == "1":
        saved, lent = s.group_savings(chama)
        status = "PAID" if member.paid_for(period) else "NOT PAID"
        return end(f"Your savings: {s.fmt(member.balance())}\n{period}: {status}\n"
                   f"Group pool: {s.fmt(saved - lent)}")

    if choice == "2":
        paid = [m.name.split()[0] for m in chama.members if m.paid_for(period)]
        unpaid = [m.name.split()[0] for m in chama.members if not m.paid_for(period)]
        return end(f"{period} paid ({len(paid)}/{len(chama.members)}): {', '.join(paid) or 'none'}\n"
                   f"Not yet: {', '.join(unpaid) or 'none'}")

    if choice == "3":
        if not rest:
            return con(f"Enter amount (KES). Monthly amount is {chama.contribution_amount}:")
        amt = _amount(rest[0])
        if amt is None:
            return end("Invalid amount. Please try again.")
        if len(rest) == 1:
            return con(f"Record {s.fmt(amt)} for {period}?\n1. Confirm\n2. Cancel")
        if rest[1] == "1":
            c = s.record_contribution(member, amt, period)
            return end(f"Recorded {s.fmt(amt)} (ref C{c.id}). The treasurer will confirm it. SMS receipt sent.")
        return end("Cancelled.")

    if choice == "4":
        if not rest:
            return con("Enter loan amount (KES):")
        amt = _amount(rest[0])
        if amt is None:
            return end("Invalid amount. Please try again.")
        if len(rest) == 1:
            return con("Reason:\n" + "\n".join(f"{i}. {r}" for i, r in enumerate(s.LOAN_REASONS, 1)))
        idx = rest[1]
        if not (idx.isdigit() and 1 <= int(idx) <= len(s.LOAN_REASONS)):
            return end("Invalid choice.")
        loan = s.request_loan(member, amt, s.LOAN_REASONS[int(idx) - 1])
        return end(f"Loan request L{loan.id} for {s.fmt(amt)} sent. Members have been notified by SMS to vote.")

    if choice == "5":
        loans = _votable(member)
        if not loans:
            return end("No loans waiting for your vote.")
        if not rest:
            return con("Pending loans:\n" + "\n".join(
                f"{i}. {l.member.name.split()[0]} {s.fmt(l.amount)}" for i, l in enumerate(loans[:5], 1)))
        idx = rest[0]
        if not (idx.isdigit() and 1 <= int(idx) <= min(5, len(loans))):
            return end("Invalid choice.")
        loan = loans[int(idx) - 1]
        if len(rest) == 1:
            yes, no = loan.tally()
            return con(f"L{loan.id}: {loan.member.name} {s.fmt(loan.amount)} ({loan.reason})\n"
                       f"Votes: {yes} yes, {no} no\n1. Approve\n2. Reject")
        if rest[1] not in ("1", "2"):
            return end("Invalid choice.")
        outcome = s.cast_vote(loan, member, rest[1] == "1")
        msg = "Vote recorded. Thank you."
        if outcome:
            msg += f" Loan is now {outcome.upper()}; the group has been notified."
        return end(msg)

    if choice == "6" and member.is_treasurer:
        pend = _pending_contribs(member)
        if not pend:
            return end("No contributions waiting for confirmation.")
        if not rest:
            return con("Confirm:\n" + "\n".join(
                f"{i}. {c.member.name.split()[0]} {s.fmt(c.amount)} {c.period}" for i, c in enumerate(pend, 1)))
        idx = rest[0]
        if not (idx.isdigit() and 1 <= int(idx) <= len(pend)):
            return end("Invalid choice.")
        c = pend[int(idx) - 1]
        s.confirm_contribution(c)
        return end(f"Confirmed {s.fmt(c.amount)} from {c.member.name}. Receipt SMS sent.")

    return end("Invalid option.")
