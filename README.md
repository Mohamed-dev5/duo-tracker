# Gojo vs Sukuna tracker

Flask + MongoDB site with two sides, each with a 30-day calendar and a timer,
plus a shared Sources box in the middle.

## Run

```bash
pip install -r requirements.txt
# MongoDB must be running (default mongodb://localhost:27017)
python app.py
```

Open http://127.0.0.1:5000 and log in.

## Logins

Each side has its own login page:

- http://127.0.0.1:5000/login/gojo     (default password: `gojo123`)
- http://127.0.0.1:5000/login/sukuna   (default password: `sukuna123`)

Change them before first run with environment variables
(passwords are only seeded into MongoDB the first time):

```bash
export GOJO_PASSWORD="your-password"
export SUKUNA_PASSWORD="your-other-password"
export SECRET_KEY="a-long-random-string"
export MONGO_URI="mongodb://localhost:27017"   # or your Atlas URI
```

## Images

Put your two pictures here (any size, jpg):

- `static/img/gojo.jpg`
- `static/img/sukuna.jpg`

Until you add them, a coloured name placeholder is shown.

## How it works

- Click a day on **your** calendar to select it, then press **Start**. Press **Stop**
  and the time is added to that day (the day turns filled) and the timer resets.
  You can repeat this many times on the same day; the time accumulates.
- Click any day (yours or the other side's) to see the time spent.
- The other side's calendar and timer are view-only. The server also enforces this (HTTP 403).
- Sources: both sides can add links and open all links. You can only delete your own.
