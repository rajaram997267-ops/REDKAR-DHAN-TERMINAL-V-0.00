# Chartink Alerts Web App (Python / Flask)

Receives Chartink webhook alerts, stores them in SQLite, and shows them as
cards on a dashboard that auto-refreshes every 5 seconds.

## What's inside
- `main.py` — Flask server: webhook receiver + dashboard + JSON API
- `templates/index.html` — the dashboard page
- `requirements.txt` — just Flask

## 1. Install and run
```
pip install -r requirements.txt
python main.py
```
Open **http://localhost:5000** in your browser.

## 2. Test it without Chartink
While the server is running, open a second terminal and send a fake alert:
```
curl -X POST http://localhost:5000/webhook/chartink -H "Content-Type: application/json" -d "{\"stocks\":\"RELIANCE,TCS,INFY\",\"trigger_prices\":\"2950.50,4120.00,1875.25\",\"triggered_at\":\"2:30 pm\",\"scan_name\":\"Short term breakout\"}"
```
Three cards should appear within 5 seconds (it polls automatically — no need
to refresh the page).

## 3. What format Chartink actually sends
Chartink's webhook alert payload looks like this:
```json
{
  "stocks": "RELIANCE,TCS,INFY",
  "trigger_prices": "2950.50,4120.00,1875.25",
  "triggered_at": "2:30 pm",
  "scan_name": "Short term breakout",
  "scan_url": "short-term-breakout",
  "alert_name": "Breakout alert"
}
```
One alert can list several stocks at once — `main.py` splits these into one
card per stock automatically.

## 4. Deploy it (Render.com, free tier)

Chartink's servers need a public URL to send alerts to — `localhost` only
works on your own PC. Render is free and straightforward:

1. **Put this folder on GitHub.**
   - Go to github.com -> sign in (or create a free account) -> New
     repository -> name it e.g. `chartink-alerts-app` -> Create repository.
   - On the new repo's page, click "uploading an existing file" and drag
     in `main.py`, `requirements.txt`, `README.md`, and the whole
     `templates` folder. Commit.

2. **Create the Render service.**
   - Go to render.com -> sign up (you can sign in with your GitHub
     account) -> New + -> Web Service.
   - Connect your GitHub account if asked, then pick the
     `chartink-alerts-app` repo.

3. **Settings, when Render asks:**
   - Runtime: Python 3
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn main:app`
   - Instance type: Free

4. Click Create Web Service. Render will build and deploy — this takes a
   couple of minutes. Watch the log; when it says the service is live,
   you're done.

5. Your app's address will be shown at the top, something like:
   ```
   https://chartink-alerts-app.onrender.com
   ```

6. **Test it exactly like you did locally**, just with the new address:
   ```
   curl -X POST https://chartink-alerts-app.onrender.com/webhook/chartink -H "Content-Type: application/json" -d "{\"stocks\":\"RELIANCE,TCS,INFY\",\"trigger_prices\":\"2950.50,4120.00,1875.25\",\"triggered_at\":\"2:30 pm\",\"scan_name\":\"Short term breakout\"}"
   ```
   Then open the same URL in your browser — the three cards should appear.

7. **Point Chartink at it.** In Chartink: open your scan -> Create Alert ->
   set the Webhook URL to:
   ```
   https://chartink-alerts-app.onrender.com/webhook/chartink
   ```

### A note on the free tier
Render's free web services "sleep" after 15 minutes of no traffic, and wake
up again (takes roughly 30-50 seconds) on the next request, including a
Chartink alert. Your first alert after a quiet spell might be slightly
delayed while it wakes up, but nothing is lost. Also, the free tier's disk
isn't permanent across redeploys, so `alerts.db` (your history) can reset
if you redeploy the code. If you want alerts to survive redeploys
long-term, add a small Render Persistent Disk later, or ask me and I'll
help set that up.

## Notes
- `alerts.db` is created automatically on first run — it's your alert
  history, stored right next to `main.py`.
- Use the **Clear All** button on the dashboard to wipe history.
- `debug=True` in `main.py` is fine for testing on your own PC; turn it off
  before deploying anywhere public.
