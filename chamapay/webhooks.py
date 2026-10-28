"""Other Africa's Talking callbacks: SMS delivery reports, inbound SMS, voice."""
from flask import Blueprint, request, Response

from .models import db, SmsLog

bp = Blueprint("hooks", __name__)


@bp.post("/sms/delivery")
def sms_delivery():
    mid = request.values.get("id")
    status = request.values.get("status", "")
    reason = request.values.get("failureReason", "")
    entry = SmsLog.query.filter_by(message_id=mid).first() if mid else None
    if entry:
        entry.delivery_status = f"{status} {reason}".strip()[:40]
        db.session.commit()
    return "", 200


@bp.post("/sms/inbound")
def sms_inbound():
    # Logged for visibility; replies could be added later.
    db.session.add(SmsLog(to=request.values.get("to", "inbound"),
                          message=f"FROM {request.values.get('from', '?')}: {request.values.get('text', '')}",
                          kind="inbound", status="received"))
    db.session.commit()
    return "", 200


@bp.post("/voice")
def voice():
    xml = ('<?xml version="1.0" encoding="UTF-8"?><Response><Say voice="en-US-Standard-C">'
           "Hello, this is ChamaPay. Your chama contribution for this month is late. "
           "Please dial your chama code and choose option three to record it. Thank you."
           "</Say></Response>")
    return Response(xml, mimetype="application/xml")
