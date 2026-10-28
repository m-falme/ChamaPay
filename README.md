# ChamaPay

**Run your chama (savings group) from any phone.** Members use a USSD menu on basic phones, everyone gets SMS
receipts and alerts, and the treasurer has a simple web dashboard. Built on Africa's Talking USSD, SMS and (optionally) Voice.

![logo](marketplace/logo.png)

## Features
| Channel | What it does |
|---|---|
| **USSD** `POST /ussd` | 1 My balance · 2 Who paid this month · 3 Record contribution · 4 Request loan · 5 Vote on loans · 6 Confirm contributions (treasurer only) |
| **SMS** | Receipt when a contribution is recorded and when it is confirmed; reminders to unpaid members; group alert on a loan request; group alert when the vote decides the loan. Every SMS is logged. |
| **SMS callbacks** | `POST /sms/delivery` (delivery reports update the log), `POST /sms/inbound` (logged) |
| **Voice** (optional) | `VOICE_ENABLED=1`: calls late members; `POST /voice` returns the spoken message XML |
| **Dashboard** `/` | Members, savings, late this month, contributions (confirm button), loans and votes, SMS log, "Send SMS reminders" button. Password login. |
| **Health** | `GET /health` → `{"status":"ok"}` |

Loans are decided by simple majority of the other members (borrower cannot vote). With no `AT_API_KEY`, SMS are
logged as `not sent (no key)` so the app still works for demos.

Stack: Python 3.12, Flask, SQLAlchemy, SQLite, gunicorn, official `africastalking` SDK.

## Local setup (Windows, PowerShell)
```powershell
git clone https://github.com/<your-user>/chamapay.git
cd chamapay
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements-dev.txt
Copy-Item .env.example .env            # then edit .env: AT_API_KEY, DASHBOARD_PASSWORD, SECRET_KEY
flask --app wsgi seed                  # loads "Umoja Women Group" (use --reset to reload)
flask --app wsgi run --port 8080       # http://localhost:8080  (dashboard login = DASHBOARD_PASSWORD)
pytest                                 # run tests
```
`.env` is loaded automatically by Flask (python-dotenv). macOS/Linux: same steps with `python3 -m venv .venv && source .venv/bin/activate`.

Useful commands:
```powershell
flask --app wsgi send-reminders                      # SMS everyone not yet paid this month (schedule with Task Scheduler/cron)
flask --app wsgi voice-reminders                     # needs VOICE_ENABLED=1 and AT_VOICE_NUMBER
flask --app wsgi add-member "Your Name" 07XXXXXXXX --treasurer   # add your own simulator number
```

### Demo members (seeded)
| Name | Phone | Notes |
|---|---|---|
| Grace Wanjiku | +254711000001 | **Treasurer** (sees option 6) |
| Mary Akinyi | +254711000002 | paid, already voted on the loan |
| Faith Njeri | +254711000003 | has pending loan L1 (KES 5,000, school fees: 2 yes / 1 no) |
| Esther Muthoni | +254711000004 | paid |
| Agnes Chebet | +254711000005 | contribution pending confirmation |
| Lucy Wambui | +254711000006 | late |
| Joyce Atieno | +254711000007 | late |
| Ann Nduta | +254711000008 | late, also missed last month |

## Expose locally with ngrok
1. Install ngrok (https://ngrok.com/download), sign up and run `ngrok config add-authtoken <token>`.
2. With the app running on 8080: `ngrok http 8080`
3. Copy the `https://xxxx.ngrok-free.app` URL. Callbacks below use it as `<BASE>`.

## Africa's Talking sandbox configuration
1. Sign up / log in at https://account.africastalking.com and open the **Sandbox** app (top bar "Go to sandbox app").
2. **API key:** Sandbox → Settings → API Key → generate. Put it in `.env` as `AT_API_KEY`, keep `AT_USERNAME=sandbox`. Restart the app.
3. **USSD:** Sandbox → USSD → Create Channel → pick a code (e.g. `*384*123#`), set **Callback URL** to `<BASE>/ussd`. Put the code in `USSD_CODE`.
4. **SMS delivery reports:** Sandbox → SMS → SMS Callback URLs → Delivery Reports → `<BASE>/sms/delivery`.
   (Optional) Incoming Messages → `<BASE>/sms/inbound`.
5. **Voice (optional):** Sandbox → Voice → phone numbers → set the callback URL to `<BASE>/voice`; put the number in `AT_VOICE_NUMBER`, set `VOICE_ENABLED=1`.
6. **Simulator:** open https://simulator.africastalking.com, enter a member phone number (e.g. `+254711000002`, or the
   number you added with `add-member`) and press Connect. Use the phone's USSD dialer for your code, and the SMS app to see messages.

> The simulator only shows SMS sent to the number currently connected in it. Switch numbers to see other members' messages.

## Demo script (≈3 minutes)
1. Dashboard at `<BASE>/` → log in. Show 8 members, 4 paid, 3 late, pending loan L1.
2. Simulator as **Ann** `+254711000008`: dial the code → `2` (who paid) → shows Ann not paid.
3. Dial again → `3` → `1000` → `1` → END "Recorded…"; SMS receipt arrives. Dashboard shows the pending contribution.
4. Simulator as **Grace** (treasurer) `+254711000001` → `6` → pick Ann → receipt SMS "confirmed" to Ann; dashboard shows paid.
5. As **Ann** → `5` → `1` → `1` (approve L1); as **Lucy** `+254711000006` → `5` → `1` → `1` → "Loan is now APPROVED"; everyone gets the outcome SMS.
6. As **Lucy** → `4` → `2000` → `3` (Business) → all other members get a vote alert SMS.
7. Dashboard → **Send SMS reminders** → SMS log fills with reminders and delivery statuses.

## curl examples
```bash
B=http://localhost:8080
curl -X POST $B/ussd --data-urlencode "sessionId=1" --data-urlencode "serviceCode=*384*123#" --data-urlencode "phoneNumber=+254711000008" --data-urlencode "text="
curl -X POST $B/ussd --data-urlencode "sessionId=1" --data-urlencode "phoneNumber=+254711000008" --data-urlencode "text=1"
curl -X POST $B/ussd --data-urlencode "sessionId=1" --data-urlencode "phoneNumber=+254711000008" --data-urlencode "text=3*1000*1"
curl -X POST $B/ussd --data-urlencode "sessionId=1" --data-urlencode "phoneNumber=+254711000008" --data-urlencode "text=5*1*1"
curl -X POST $B/sms/delivery -d "id=ATXid_123&status=Success"
curl $B/health
```
(PowerShell: use `curl.exe` with the same arguments.)

## Docker
```bash
docker build -t chamapay .
docker run --rm -p 8080:8080 --env-file .env -e SEED_DEMO=1 -v chamapay_data:/data chamapay
```
The container listens on `$PORT` (default 8080), creates tables on start, seeds the demo chama when `SEED_DEMO=1`
(idempotent), and stores SQLite at `/data/chamapay.db`.

## Africa's Talking Marketplace
Listing copy, features and pricing are in [`marketplace/listing.md`](marketplace/listing.md); logo in `marketplace/logo.svg` / `logo.png`.
To publish at https://marketplace.africastalking.dev:
1. Sign in with your AT account and create a new app listing (name, short/long description, logo, pricing from `listing.md`).
2. Follow the listing's container instructions to log in to AT's registry, then tag and push the image, e.g.
   `docker tag chamapay <registry>/<namespace>/chamapay:1.0.0` and `docker push <registry>/<namespace>/chamapay:1.0.0`.
3. Set environment variables in the listing (`AT_USERNAME`, `AT_API_KEY`, `DASHBOARD_PASSWORD`, `SECRET_KEY`, optional `SEED_DEMO=1`), port 8080, health check `/health`.
4. Point the USSD/SMS callbacks of the AT app to the deployed URL (`/ussd`, `/sms/delivery`).

## Configuration
All configuration is via environment variables; see [`.env.example`](.env.example). Never commit `.env`.

## License
MIT, see [LICENSE](LICENSE).
