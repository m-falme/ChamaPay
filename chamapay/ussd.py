"""Africa's Talking USSD callback. AT POSTs sessionId, serviceCode, phoneNumber, text.
Reply with plain text starting with CON (continue) or END (finish). Inputs accumulate in `text`
separated by '*'. '0' goes back one step, '00' returns to the main menu."""
import logging

from flask import Blueprint, request, Response

from .models import db, Member, Loan, Contribution, Vote, current_period
from . import services as s

bp = Blueprint("ussd", __name__)
log = logging.getLogger(__name__)

MAX_SCREEN = 160
MAX_CONTRIBUTION = 100_000
NAV = "\n0 Back 00 Menu"


def _fit(t):
    return t if len(t) <= MAX_SCREEN else t[:MAX_SCREEN - 1] + "…"


def con(t, nav=True):
    body = t + NAV if nav else t
    if len(body) > MAX_SCREEN and nav:
        body = _fit(t[:MAX_SCREEN - len(NAV)]) + NAV
    return Response("CON " + _fit(body), mimetype="text/plain")


def end(t):
    return Response("END " + _fit(t), mimetype="text/plain")


def normalize_phone(raw):
    p = (raw or "").replace(" ", "").replace("-", "")
    if p.startswith("254"):
        p = "+" + p
    elif p.startswith("0") and len(p) == 10:
        p = "+254" + p[1:]
    return p


def resolve_steps(text):
    """Apply back (0) / home (00) navigation to the cumulative USSD input."""
    steps = []
    for part in (text or "").split("*"):
        part = part.strip()
        if part == "":
            continue
        if part == "00":
            steps = []
        elif part == "0":
            if steps:
                steps.pop()
        else:
            steps.append(part)
    return steps


def parse_amount(v, maximum):
    """Returns (amount, error_message)."""
    v = (v or "").strip().replace(",", "")
    if v.startswith("-"):
        return None, "Amount cannot be negative."
    if not v.isdigit():
        return None, "Enter numbers only, e.g. 1000."
    n = int(v)
    if n == 0:
        return None, "Amount must be more than 0."
    if n > maximum:
        return None, f"Amount too large. Max {s.fmt(maximum)}."
    return n, None


def first(name):
    return name.split()[0]


def main_menu(member):
    menu = (f"{member.chama.name}\nHi {first(member.name)}\n1 My balance\n2 Who paid\n"
            "3 Pay contribution\n4 Request loan\n5 Vote on loans")
    if member.is_treasurer:
        menu += "\n6 Confirm payments"
    return con(menu, nav=False)


def _pending_loans(member):
    ids = [m.id for m in member.chama.members]
    return Loan.query.filter(Loan.member_id.in_(ids), Loan.status == "pending",
                             Loan.member_id != member.id).order_by(Loan.id).all()


def _votable(member):
    voted = {v.loan_id for v in Vote.query.filter_by(member_id=member.id)}
    return [l for l in _pending_loans(member) if l.id not in voted]


def _pending_contribs(member):
    ids = [m.id for m in member.chama.members]
    return Contribution.query.filter(Contribution.member_id.in_(ids),
                                     Contribution.status == "pending").order_by(Contribution.id).limit(5).all()


def _pick(choice, items):
    if choice.isdigit() and 1 <= int(choice) <= len(items):
        return items[int(choice) - 1]
    return None


def handle(member, steps):
    chama = member.chama
    period = current_period()
    month = s.month_label(period)
    if not steps:
        return main_menu(member)
    choice, rest = steps[0], steps[1:]

    if choice == "1":
        saved, lent = s.group_savings(chama)
        status = "PAID" if member.paid_for(period) else (
            "PENDING" if member.recorded_for(period) else "NOT PAID")
        return end(f"Savings: {s.fmt(member.balance())}\n{month}: {status}\nGroup pool: {s.fmt(saved - lent)}")

    if choice == "2":
        paid = [first(m.name) for m in chama.members if m.paid_for(period)]
        unpaid = [first(m.name) for m in chama.members if not m.paid_for(period)]
        return end(f"{month}: {len(paid)}/{len(chama.members)} paid\n"
                   f"Paid: {', '.join(paid) or 'none'}\nNot yet: {', '.join(unpaid) or 'none'}")

    if choice == "3":
        if not rest:
            due = "PAID already" if member.paid_for(period) else f"due {s.fmt(chama.contribution_amount)}"
            return con(f"{month} ({due})\nEnter amount in KES:")
        amt, err = parse_amount(rest[0], MAX_CONTRIBUTION)
        if err:
            return con(f"{err}\nTry again: 0 then amount")
        if len(rest) == 1:
            return con(f"Pay {s.fmt(amt)} for {month}?\n1 Confirm\n2 Cancel")
        if rest[1] == "1":
            c = s.record_contribution(member, amt, period)
            return end(f"Recorded {s.fmt(amt)} for {month}. Ref C{c.id}. "
                       "Treasurer will confirm. SMS receipt sent.")
        if rest[1] == "2":
            return end("Cancelled. Nothing was recorded.")
        return con("Invalid choice. Reply 1 to confirm or 2 to cancel.")

    if choice == "4":
        if any(l.member_id == member.id for l in Loan.query.filter_by(member_id=member.id, status="pending")):
            return end("You already have a loan request waiting for votes.")
        saved, lent = s.group_savings(chama)
        pool = saved - lent
        if pool <= 0:
            return end("The group pool is empty. No loans available right now.")
        if not rest:
            return con(f"Group pool: {s.fmt(pool)}\nEnter loan amount in KES:")
        amt, err = parse_amount(rest[0], pool)
        if err:
            return con(f"{err}\nTry again: 0 then amount")
        if len(rest) == 1:
            return con("Reason:\n" + "\n".join(f"{i} {r}" for i, r in enumerate(s.LOAN_REASONS, 1)))
        reason = _pick(rest[1], s.LOAN_REASONS)
        if not reason:
            return con(f"Invalid choice. Pick 1-{len(s.LOAN_REASONS)}.")
        loan = s.request_loan(member, amt, reason)
        return end(f"Loan request L{loan.id} for {s.fmt(amt)} sent. Members will vote by USSD; "
                   "you'll get an SMS with the result.")

    if choice == "5":
        pending = _pending_loans(member)
        if not pending:
            return end("No pending loans to vote on.")
        loans = _votable(member)[:5]
        if not loans:
            return end("You have already voted on all pending loans. Thank you.")
        if not rest:
            return con("Pick a loan:\n" + "\n".join(
                f"{i} {first(l.member.name)} {s.fmt(l.amount)}" for i, l in enumerate(loans, 1)))
        loan = _pick(rest[0], loans)
        if not loan:
            return con(f"Invalid choice. Pick 1-{len(loans)}.")
        if len(rest) == 1:
            yes, no = loan.tally()
            return con(f"L{loan.id} {first(loan.member.name)} {s.fmt(loan.amount)} ({loan.reason})\n"
                       f"Votes: {yes} yes, {no} no\n1 Approve\n2 Reject")
        if rest[1] not in ("1", "2"):
            return con("Invalid choice. Reply 1 to approve or 2 to reject.")
        outcome = s.cast_vote(loan, member, rest[1] == "1")
        if outcome is None and loan.status != "pending":
            return end(f"Vote recorded. Loan L{loan.id} is {loan.status.upper()}.")
        msg = "Vote recorded. Thank you."
        if outcome:
            msg += f" Loan L{loan.id} is now {outcome.upper()}; the group has been notified by SMS."
        return end(msg)

    if choice == "6" and member.is_treasurer:
        pend = _pending_contribs(member)
        if not pend:
            return end("No payments waiting for confirmation.")
        if not rest:
            return con("Confirm payment:\n" + "\n".join(
                f"{i} {first(c.member.name)} {s.fmt(c.amount)} {s.month_label(c.period)}"
                for i, c in enumerate(pend, 1)))
        c = _pick(rest[0], pend)
        if not c:
            return con(f"Invalid choice. Pick 1-{len(pend)}.")
        s.confirm_contribution(c)
        return end(f"Confirmed {s.fmt(c.amount)} from {first(c.member.name)}. Receipt SMS sent.")

    return con("Invalid choice. Reply 00 for the main menu.", nav=False)


@bp.post("/ussd")
def ussd():
    try:
        phone = normalize_phone(request.values.get("phoneNumber", ""))
        if not phone:
            return end("Could not read your phone number. Please dial again.")
        member = Member.query.filter_by(phone=phone).first()
        if not member:
            return end("This number is not registered in any ChamaPay group. Ask your treasurer to add you.")
        return handle(member, resolve_steps(request.values.get("text", "")))
    except Exception:
        log.exception("USSD error (session %s)", request.values.get("sessionId"))
        db.session.rollback()
        return end("Sorry, something went wrong. Please dial again in a moment.")


@bp.post("/ussd/end")
def ussd_end():
    """Optional AT 'end of session' notification (timeouts etc.): just acknowledge."""
    log.info("USSD session ended %s status=%s", request.values.get("sessionId"), request.values.get("status"))
    return "", 200
