"""Africa's Talking integration (SMS + optional Voice). Never crashes when keys are missing."""
import logging
import os

from .models import db, SmsLog

log = logging.getLogger(__name__)
_client = {}


def _sdk():
    key = os.environ.get("AT_API_KEY", "").strip()
    if not key:
        return None
    if "sdk" not in _client:
        import africastalking
        africastalking.initialize(os.environ.get("AT_USERNAME", "sandbox"), key)
        _client["sdk"] = africastalking
    return _client["sdk"]


def send_sms(recipients, message, kind="general"):
    """Send one message to a list of phone numbers; log every recipient. Returns list of SmsLog."""
    if isinstance(recipients, str):
        recipients = [recipients]
    recipients = [r for r in recipients if r]
    if not recipients:
        return []
    results = {}
    sdk = _sdk()
    if sdk is None:
        results = {r: ("not sent (no key)", None) for r in recipients}
    else:
        try:
            sender = os.environ.get("AT_SENDER_ID", "").strip() or None
            resp = sdk.SMS.send(message, recipients, sender)
            for rec in resp.get("SMSMessageData", {}).get("Recipients", []):
                st = rec.get("status", "unknown")
                if st not in ("Success", "Sent", "Submitted", "Queued"):
                    st = f"failed: {st}"
                    log.warning("SMS to %s failed: %s", rec.get("number"), rec.get("status"))
                results[rec.get("number")] = (st[:60], rec.get("messageId"))
            msg = resp.get("SMSMessageData", {}).get("Message", "no recipients")
            for r in recipients:
                results.setdefault(r, (f"failed: {msg}"[:60], None))
        except Exception as exc:  # network / auth errors must not break USSD
            log.exception("SMS send failed")
            results = {r: (f"failed: {type(exc).__name__}: {exc}"[:60], None) for r in recipients}
    logs = []
    for r in recipients:
        status, mid = results[r]
        entry = SmsLog(to=r, message=message, kind=kind, status=status, message_id=mid)
        db.session.add(entry)
        logs.append(entry)
    db.session.commit()
    return logs


def voice_enabled():
    return os.environ.get("VOICE_ENABLED", "0").lower() in ("1", "true", "yes")


def voice_call(phone):
    """Place a reminder call. Returns a status string."""
    if not voice_enabled():
        return "voice disabled"
    sdk = _sdk()
    caller = os.environ.get("AT_VOICE_NUMBER", "").strip()
    if sdk is None or not caller:
        return "not called (no key/voice number)"
    try:
        sdk.Voice.call(caller, [phone])
        return "queued"
    except Exception as exc:
        log.exception("Voice call failed")
        return f"error: {exc}"[:60]
