# ChamaPay live demo (2-3 minutes)

## Setup checklist (do this 30 minutes before)
- [ ] `git pull`, activate the venv: `.\.venv\Scripts\Activate.ps1`, then `pip install -r requirements-dev.txt`
- [ ] `.env` has `AT_USERNAME=sandbox`, `AT_API_KEY=<sandbox key>`, `DASHBOARD_PASSWORD`, `SECRET_KEY`
- [ ] Fresh data: `flask --app wsgi seed --reset`
- [ ] `pytest` is green
- [ ] Start the app: `flask --app wsgi run --port 8080`
- [ ] Start the tunnel: `ngrok http 8080`, then copy the `https://…ngrok-free.app` URL (`<BASE>`)
- [ ] AT sandbox (https://account.africastalking.com → sandbox app):
      USSD → your channel → callback `<BASE>/ussd`; SMS → SMS Callback URLs → Delivery Reports → `<BASE>/sms/delivery`
- [ ] Check `<BASE>/health` shows `{"status":"ok"}`
- [ ] Browser tab 1: `<BASE>/` logged in to the dashboard (zoom 125% for the projector)
- [ ] Browser tab 2: https://simulator.africastalking.com, connect as **+254711000008** (Ann)

USSD tips: `0` = back, `00` = main menu. The sandbox USSD code is the one on your channel (e.g. `*384*123#`).

## Script

**0:00 Problem (15 s).** "Chamas run on WhatsApp groups and paper notebooks. ChamaPay works on any phone over USSD and SMS,
and gives the treasurer a live dashboard."

**0:15 Dashboard (20 s).** Show the cards: 8 members, 4/8 paid in this month, 4 not yet paid, pool KES 24,000.
Point at the pending loan **L1** (Faith, KES 5,000, 2 yes / 1 no).

**0:35 Ann checks in (simulator as +254711000008).**
| Dial | Input | You see |
|---|---|---|
| code | `2` | Who paid this month: Ann is in "Not yet" |
| code | `3` → `1000` → `1` | "Recorded KES 1,000 … Ref C…" and a receipt SMS in the simulator inbox |

Show the receipt SMS: amount, chama, month, savings balance, reference. On the dashboard (refresh), Ann is **pending**
and the SMS log has the receipt.

**1:05 Treasurer confirms (switch simulator to +254711000001, Grace).**
| Dial | Input | You see |
|---|---|---|
| code | `6` → `2` | "Confirmed KES 1,000 from Ann. Receipt SMS sent." |
Agnes (seeded) is item 1 and Ann is item 2. Pick the line that says Ann.

Dashboard: Ann is now **paid**, savings went up, and a "CONFIRMED" receipt is in the SMS log.

**1:35 Loan vote (simulator as Ann +254711000008, then Lucy +254711000006).**
| Who | Input | You see |
|---|---|---|
| Ann | `5` → `1` → `1` | "Vote recorded" (3 yes / 1 no) |
| Lucy | `5` → `1` → `1` | "Loan L1 is now APPROVED; the group has been notified by SMS" |

Dashboard: L1 is **approved** with each vote listed; 8 outcome SMS are in the log. Optional: as Lucy, `4` → `2000` → `3`
sends a loan request alert to everyone.

**2:15 Reminders.** Click **Send SMS reminders** and show the flash message and the new reminder rows in the SMS log.

**2:30 Close.** "No smartphone, no app, no data: USSD for members, SMS for trust, a dashboard for the treasurer.
Built on Africa's Talking USSD and SMS, and it runs as one Docker container."

Robustness, if asked: type `abc`, `000` or `999999` as an amount (clear message, `0` to go back), or vote twice
("already voted"). An unknown number gets "not registered".

## Fallbacks
- **SMS not arriving:** the dashboard SMS log is the source of truth. Every message is listed with its status
  (`Success`, `failed: …`, or `not sent (no key)`). Show it there. Failed sends never break the USSD flow.
- **Simulator shows only one number's SMS:** that's expected; switch numbers or show the SMS log.
- **ngrok down or URL changed:** restart `ngrok http 8080`, then paste the new URL into the USSD and SMS callbacks.
  If the network is dead, run the same flow locally with curl (PowerShell, use `curl.exe`):
  ```
  curl.exe -X POST http://localhost:8080/ussd --data-urlencode "phoneNumber=+254711000008" --data-urlencode "text=3*1000*1"
  curl.exe -X POST http://localhost:8080/ussd --data-urlencode "phoneNumber=+254711000001" --data-urlencode "text=6"
  curl.exe -X POST http://localhost:8080/ussd --data-urlencode "phoneNumber=+254711000008" --data-urlencode "text=5*1*1"
  ```
  then refresh the dashboard.
- **Data got messy during rehearsal:** `flask --app wsgi seed --reset` (restart not needed).
- **AT key problems:** blank `AT_API_KEY` in `.env` and restart. The app runs in demo mode and logs SMS as "not sent".
