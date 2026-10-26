import os
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import urlparse

from bson import ObjectId
from bson.errors import InvalidId
from flask import (Flask, jsonify, redirect, render_template, request,
                   session, url_for, abort)
from pymongo import ASCENDING, MongoClient
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

client = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017"))
db = client[os.environ.get("MONGO_DB", "duo_tracker")]

SIDES = ("gojo", "sukuna")
DAYS = 30


# ---------- setup ----------
def setup():
    db.days.create_index([("side", ASCENDING), ("day", ASCENDING)], unique=True)
    db.users.create_index("side", unique=True)
    defaults = {
        "gojo": os.environ.get("GOJO_PASSWORD", "gojo123"),
        "sukuna": os.environ.get("SUKUNA_PASSWORD", "sukuna123"),
    }
    for side, pwd in defaults.items():
        if not db.users.find_one({"side": side}):
            db.users.insert_one({"side": side, "password_hash": generate_password_hash(pwd)})


# ---------- helpers ----------
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("side") not in SIDES:
            if request.path.startswith("/api/"):
                return jsonify(error="login required"), 401
            return redirect(url_for("login", side="gojo"))
        return fn(*args, **kwargs)
    return wrapper


def days_for(side):
    return {str(d["day"]): d["seconds"] for d in db.days.find({"side": side})}


def clean_url(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = "https://" + raw
    p = urlparse(raw)
    if p.scheme not in ("http", "https") or not p.netloc:
        return None
    return raw


def link_json(l):
    return {"id": str(l["_id"]), "title": l["title"], "url": l["url"],
            "side": l["side"], "created_at": l["created_at"].isoformat()}


# ---------- pages ----------
@app.route("/")
@login_required
def index():
    return render_template(
        "index.html",
        me=session["side"],
        sides=SIDES,
        days=range(1, DAYS + 1),
        data={s: days_for(s) for s in SIDES},
    )


@app.route("/login/<side>", methods=["GET", "POST"])
def login(side):
    if side not in SIDES:
        abort(404)
    error = None
    if request.method == "POST":
        user = db.users.find_one({"side": side})
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["side"] = side
            return redirect(url_for("index"))
        error = "Wrong password."
    return render_template("login.html", side=side, error=error)


@app.route("/logout")
def logout():
    side = session.get("side", "gojo")
    session.clear()
    return redirect(url_for("login", side=side))


# ---------- API: days ----------
@app.get("/api/days/<side>")
@login_required
def get_days(side):
    if side not in SIDES:
        abort(404)
    return jsonify(days_for(side))


@app.post("/api/days/<side>/<int:day>/add")
@login_required
def add_time(side, day):
    # you can only change YOUR OWN calendar
    if side not in SIDES:
        abort(404)
    if side != session["side"]:
        return jsonify(error="you can't control the other side"), 403
    if not 1 <= day <= DAYS:
        return jsonify(error="bad day"), 400
    seconds = (request.get_json(silent=True) or {}).get("seconds")
    if not isinstance(seconds, int) or not 1 <= seconds <= 86400:
        return jsonify(error="bad seconds"), 400
    db.days.update_one({"side": side, "day": day},
                       {"$inc": {"seconds": seconds}}, upsert=True)
    doc = db.days.find_one({"side": side, "day": day})
    return jsonify(day=day, seconds=doc["seconds"])


# ---------- API: shared links (both sides can add / view) ----------
@app.get("/api/links")
@login_required
def get_links():
    return jsonify([link_json(l) for l in db.links.find().sort("created_at", -1)])


@app.post("/api/links")
@login_required
def add_link():
    body = request.get_json(silent=True) or {}
    url = clean_url(body.get("url"))
    if not url:
        return jsonify(error="invalid url"), 400
    title = (body.get("title") or "").strip()[:80] or urlparse(url).netloc
    doc = {"title": title, "url": url, "side": session["side"],
           "created_at": datetime.now(timezone.utc)}
    doc["_id"] = db.links.insert_one(doc).inserted_id
    return jsonify(link_json(doc)), 201


@app.delete("/api/links/<link_id>")
@login_required
def delete_link(link_id):
    try:
        oid = ObjectId(link_id)
    except InvalidId:
        abort(404)
    res = db.links.delete_one({"_id": oid, "side": session["side"]})
    if not res.deleted_count:
        return jsonify(error="not found or not yours"), 404
    return jsonify(ok=True)


setup()

if __name__ == "__main__":
    app.run(debug=True)
