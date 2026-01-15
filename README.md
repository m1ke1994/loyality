# Loyalty SaaS (Vue 3 PWA + Django DRF)

Production-ready Loyalty SaaS with multi-tenant portals: client, cashier, and admin.

## Milestones
- **A**: Portals, roles, org settings, staff/locations, seed data
- **B**: Full loyalty operations (earn/redeem/refund), rules/tier, offers/coupons
- **C**: Email verification via SMTP, OTP hashing + rate limits, audit logs, widget modal

## Quick Start (Docker)

### 1) Backend + DB
```bash
docker compose up --build
```
Backend: http://localhost:8000

### 2) Seed demo data
```bash
docker compose exec backend python manage.py seed_demo
```
Creates:
- tenant `demo`
- location `Main`
- admin `admin@demo.local` / `12345678`
- cashier `cashier@demo.local` / `12345678`
- client `client@demo.local` / `12345678`
- rule 3%, offer, coupon

### 3) Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend: http://localhost:5173

## SMTP Setup (Email Verification)
By default, email codes are printed to the backend console (console backend). To use SMTP, set envs:
```
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_user
SMTP_PASSWORD=your_password
SMTP_USE_TLS=1
EMAIL_FROM=no-reply@yourdomain.com
```
In Docker, update these in `docker-compose.yml` or export them before start.

## Telegram Phone Login (Clients Only)
Telegram login is an optional second auth method for clients. The bot sends a 6-digit code after the user shares their phone.

Required envs:
```
TELEGRAM_BOT_TOKEN=<bot token>
TELEGRAM_BOT_USERNAME=<bot username>
TELEGRAM_MODE=polling|webhook
TELEGRAM_WEBHOOK_SECRET=<secret token>
TELEGRAM_WEBHOOK_URL=<https://your-domain/api/v1/integrations/telegram/webhook>
VITE_TELEGRAM_BOT_USERNAME=<bot username for frontend>
```

### Local (polling)
1) Set `TELEGRAM_MODE=polling` and `TELEGRAM_BOT_TOKEN`.
2) Run the bot:
```
docker compose --profile telegram up --build
```
3) Open client login and use the Telegram flow.

### Production (webhook)
1) Set `TELEGRAM_MODE=webhook`, `TELEGRAM_WEBHOOK_URL`, `TELEGRAM_WEBHOOK_SECRET`.
2) Configure the bot webhook to point to the URL above and pass the same secret.

## Portals
- Client: `http://localhost:5173/t/demo/login`
- Cashier: `http://localhost:5173/t/demo/cashier/login`
- Admin: `http://localhost:5173/t/demo/admin/login`

## Demo ????????
1. ??????? ?????????? ?????? ? ??????????????????.
2. ??????????? email (??? ???????? ?? SMTP ??? ? ?????).
3. ????? ??? ??????, ? ??????? ????????? ??????? (OTP dev-mock).
4. ??????? QR, ? ?????????? ??????? ????????????? ? ????????? ?? ?????.
5. ????????? ???????? ? refund ?? `receipt_id`.
6. ????????? ??????? ? ?????? ???????.

## POS endpoint
Endpoint:
```
POST /api/v1/{tenant}/pos/loyalty/earn
```
Header:
```
X-POS-API-KEY: <tenant.pos_api_key>
```
Example:
```bash
curl -X POST "http://localhost:8000/api/v1/demo/pos/loyalty/earn" \
  -H "Content-Type: application/json" \
  -H "X-POS-API-KEY: <YOUR_POS_KEY>" \
  -d '{
    "qr_payload": "<TOKEN_FROM_QR>",
    "amount": 1000,
    "receipt_id": "r-10001",
    "location_id": 1
  }'
```
????????? ?????? ? ??? ?? `receipt_id` ?? ????????? ??????????.

## Widget
Loader script:
- `http://localhost:5173/widget/loader.js`

Iframe mode:
```html
<script
  src="http://localhost:5173/widget/loader.js"
  data-tenant="demo"
  data-host="http://localhost:5173"
  data-mode="iframe">
</script>
```

Modal mode:
```html
<script
  src="http://localhost:5173/widget/loader.js"
  data-tenant="demo"
  data-host="http://localhost:5173"
  data-mode="modal">
</script>
```

Demo site: `demo-site/index.html`

## API endpoints
Auth:
- POST `/api/v1/{tenant}/auth/register`
- POST `/api/v1/{tenant}/auth/login`
- POST `/api/v1/auth/refresh`

Email verify:
- POST `/api/v1/{tenant}/auth/email/request-code`
- POST `/api/v1/{tenant}/auth/email/confirm`

Phone:
- POST `/api/v1/{tenant}/auth/phone/request`
- POST `/api/v1/{tenant}/auth/phone/confirm`

Client:
- GET  `/api/v1/{tenant}/client/me`
- GET  `/api/v1/{tenant}/client/operations`
- GET  `/api/v1/{tenant}/client/offers`
- GET  `/api/v1/{tenant}/client/coupons`
- POST `/api/v1/{tenant}/client/qr/issue`
- POST `/api/v1/{tenant}/client/profile/password`

Cashier:
- POST `/api/v1/{tenant}/loyalty/qr/validate`
- POST `/api/v1/{tenant}/loyalty/points/earn`
- POST `/api/v1/{tenant}/loyalty/points/redeem`
- POST `/api/v1/{tenant}/loyalty/points/refund`

POS:
- POST `/api/v1/{tenant}/pos/loyalty/earn`

Admin:
- GET `/api/v1/{tenant}/admin/dashboard`
- GET `/api/v1/{tenant}/admin/customers`
- GET/POST `/api/v1/{tenant}/admin/staff`
- GET/POST `/api/v1/{tenant}/admin/locations`
- GET/POST `/api/v1/{tenant}/admin/rules`
- GET `/api/v1/{tenant}/admin/operations`
- GET/POST `/api/v1/{tenant}/admin/offers`
- GET/POST `/api/v1/{tenant}/admin/settings`
