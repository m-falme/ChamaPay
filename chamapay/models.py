from datetime import datetime, date, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def current_period(today=None):
    today = today or date.today()
    return today.strftime("%Y-%m")


class Chama(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    contribution_amount = db.Column(db.Integer, nullable=False, default=1000)
    contribution_day = db.Column(db.Integer, nullable=False, default=5)  # day of month
    members = db.relationship("Member", backref="chama", lazy=True)


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chama_id = db.Column(db.Integer, db.ForeignKey("chama.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    is_treasurer = db.Column(db.Boolean, default=False)
    contributions = db.relationship("Contribution", backref="member", lazy=True)

    def balance(self):
        total = db.session.query(func.coalesce(func.sum(Contribution.amount), 0)).filter(
            Contribution.member_id == self.id, Contribution.status == "confirmed").scalar()
        return int(total)

    def paid_for(self, period):
        return any(c.period == period and c.status == "confirmed" for c in self.contributions)

    def recorded_for(self, period):
        return any(c.period == period for c in self.contributions)


class Contribution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    period = db.Column(db.String(7), nullable=False)  # YYYY-MM
    status = db.Column(db.String(12), nullable=False, default="pending")  # pending|confirmed
    created_at = db.Column(db.DateTime, default=utcnow)
    confirmed_at = db.Column(db.DateTime)


class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(60), nullable=False)
    status = db.Column(db.String(12), nullable=False, default="pending")  # pending|approved|rejected
    created_at = db.Column(db.DateTime, default=utcnow)
    member = db.relationship("Member")
    votes = db.relationship("Vote", backref="loan", lazy=True)

    def tally(self):
        yes = sum(1 for v in self.votes if v.approve)
        return yes, len(self.votes) - yes


class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey("loan.id"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    approve = db.Column(db.Boolean, nullable=False)
    member = db.relationship("Member")
    __table_args__ = (db.UniqueConstraint("loan_id", "member_id"),)


class SmsLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    to = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    kind = db.Column(db.String(20), default="general")
    status = db.Column(db.String(60), nullable=False)
    message_id = db.Column(db.String(80))
    delivery_status = db.Column(db.String(40))
    created_at = db.Column(db.DateTime, default=utcnow)
