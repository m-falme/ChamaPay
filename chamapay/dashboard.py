import hmac
from functools import wraps

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from .models import Chama, Contribution, Loan, SmsLog, db, current_period
from . import services as s
from .at import voice_enabled

bp = Blueprint("dashboard", __name__)


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not session.get("auth"):
            return redirect(url_for("dashboard.login", next=request.path))
        return f(*a, **kw)
    return wrapper


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if hmac.compare_digest(request.form.get("password", ""), current_app.config["DASHBOARD_PASSWORD"]):
            session["auth"] = True
            return redirect(url_for("dashboard.index"))
        flash("Wrong password", "error")
    return render_template("login.html")


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard.login"))


@bp.get("/")
@login_required
def index():
    chama = Chama.query.first()
    if not chama:
        return render_template("empty.html")
    period = current_period()
    ids = [m.id for m in chama.members]
    saved, lent = s.group_savings(chama)
    return render_template(
        "dashboard.html", chama=chama, period=period, saved=saved, lent=lent,
        late=s.late_members(chama, period), fmt=s.fmt,
        contributions=Contribution.query.filter(Contribution.member_id.in_(ids))
        .order_by(Contribution.period.desc(), Contribution.id.desc()).limit(40).all(),
        loans=Loan.query.filter(Loan.member_id.in_(ids)).order_by(Loan.id.desc()).all(),
        sms=SmsLog.query.order_by(SmsLog.id.desc()).limit(50).all(),
        voice=voice_enabled())


@bp.post("/remind")
@login_required
def remind():
    chama = Chama.query.first()
    sent = s.send_reminders(chama) if chama else []
    flash(f"Reminder SMS queued for {len(sent)} member(s).", "ok")
    return redirect(url_for("dashboard.index"))


@bp.post("/voice-remind")
@login_required
def voice_remind():
    chama = Chama.query.first()
    res = s.voice_reminders(chama) if chama else {}
    flash(f"Voice: {len(res)} call(s): " + ", ".join(sorted(set(res.values())) or ["none"]), "ok")
    return redirect(url_for("dashboard.index"))


@bp.post("/contributions/<int:cid>/confirm")
@login_required
def confirm(cid):
    s.confirm_contribution(db.get_or_404(Contribution, cid))
    flash("Contribution confirmed and receipt sent.", "ok")
    return redirect(url_for("dashboard.index"))
