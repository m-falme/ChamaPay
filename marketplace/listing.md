# ChamaPay — AT Marketplace listing

## Name
ChamaPay

## Short description (≤ 140 chars)
Run your chama from any phone: USSD contributions, loan voting and SMS receipts, plus a simple treasurer dashboard.

## Long description
ChamaPay helps savings groups (chamas) manage money transparently, on any phone. Members dial a USSD code to check
their savings, see who has paid this month, record a contribution and request or vote on loans. No smartphone,
app or data bundle is needed. Every action triggers an SMS: receipts when a contribution is recorded and confirmed,
reminders before contribution day, and group alerts when a loan is requested and when the vote is decided.

Treasurers get a mobile-friendly web dashboard showing members, contributions, who is late, loans with each vote,
and a full SMS log with delivery reports. They can confirm contributions and send reminders with one tap.
Optional voice-call reminders reach late members who ignore SMS.

## Africa's Talking products used
- USSD (member menu)
- SMS (receipts, reminders, loan alerts, delivery reports)
- Voice (optional reminder calls)

## Features
- USSD menu: balance, who paid this month, record contribution, request loan, vote on loans
- Treasurer confirmation of contributions (USSD option 6 or dashboard)
- Majority-vote loan approval with automatic group SMS of the outcome
- SMS reminders to unpaid members (dashboard button or scheduled CLI job)
- SMS receipts and delivery-status tracking
- Password-protected treasurer dashboard, works on mobile
- Runs as a single Docker container; SQLite by default
- Works without API keys for demos (messages logged as "not sent")

## Pricing
| Plan | Price | Includes |
|------|-------|----------|
| Free trial | KES 0 for 30 days | 1 group, up to 30 members, all features |
| Group | KES 500 / month per group | Up to 50 members, USSD + SMS, dashboard |
| Group Plus | KES 900 / month per group | Up to 150 members, voice reminders |

SMS/voice usage is billed at Africa's Talking rates on the operator's account.

## Category
Fintech / Community savings

## Assets
- logo.svg (vector), logo.png (512×512)
- Container: see README "Docker" and "Africa's Talking Marketplace" sections
