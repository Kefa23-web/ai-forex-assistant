from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for
)

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

import requests
import os

from database import db, User

# =========================
# APP CONFIG
# =========================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "fallback-secret-key"
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///users.db"
)

db.init_app(app)

# =========================
# LOGIN MANAGER
# =========================

login_manager = LoginManager()

login_manager.login_view = "login"

login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))

# =========================
# ENVIRONMENT VARIABLES
# =========================

API_KEY = os.environ.get("API_KEY")

BOT_TOKEN = os.environ.get("BOT_TOKEN")

CHAT_ID = os.environ.get("CHAT_ID")

# =========================
# TELEGRAM FUNCTION
# =========================

def send_telegram_message(message):

    try:

        if not BOT_TOKEN or not CHAT_ID:
            return

        telegram_url = (
            f"https://api.telegram.org/"
            f"bot{BOT_TOKEN}/sendMessage"
        )

        requests.get(
            telegram_url,
            params={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=10
        )

    except Exception as e:

        print("Telegram Error:", e)

# =========================
# CREATE DATABASE
# =========================

with app.app_context():
    db.create_all()

# =========================
# HEALTH CHECK
# =========================

@app.route("/health")
def health():

    return "OK"

# =========================
# HOME
# =========================

@app.route("/")
def home():

    return render_template("index.html")

# =========================
# ABOUT PAGE
# =========================

@app.route("/about")
def about():

    return render_template("about.html")

# =========================
# CONTACT PAGE
# =========================

@app.route("/contact")
def contact():

    return render_template("contact.html")

# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:

            return "Username already exists"

        hashed_password = generate_password_hash(
            password
        )

        new_user = User(
            username=username,
            password=hashed_password
        )

        db.session.add(new_user)

        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")

# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        user = User.query.filter_by(
            username=username
        ).first()

        if (
            user and
            check_password_hash(
                user.password,
                password
            )
        ):

            login_user(user)

            return redirect(
                url_for("dashboard")
            )

        return "Invalid username or password"

    return render_template("login.html")

# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
@login_required
def dashboard():

    return render_template(
        "dashboard.html",
        username=current_user.username
    )

# =========================
# PAYMENT PAGE
# =========================

@app.route("/payment")
@login_required
def payment():

    return render_template(
        "payment.html"
    )

# =========================
# LOGOUT
# =========================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(
        url_for("login")
    )

# =========================
# SIGNAL API
# =========================

@app.route("/signal", methods=["POST"])
@login_required
def signal():

    try:

        data = request.json

        full_pair = data["pair"]

        pair = full_pair.replace(
            "OANDA:",
            ""
        )

        symbol_map = {
            "EURUSD": "EUR/USD",
            "GBPUSD": "GBP/USD",
            "USDJPY": "USD/JPY",
            "XAUUSD": "XAU/USD"
        }

        api_pair = symbol_map.get(pair)

        if not api_pair:

            return jsonify({
                "signal": "ERROR",
                "price": "N/A",
                "explanation":
                "Invalid pair selected."
            })

        url = (
            f"https://api.twelvedata.com/"
            f"time_series?"
            f"symbol={api_pair}"
            f"&interval=5min"
            f"&outputsize=20"
            f"&apikey={API_KEY}"
        )

        response = requests.get(
            url,
            timeout=15
        )

        market_data = response.json()

        if "values" not in market_data:

            return jsonify({
                "signal": "ERROR",
                "price": "N/A",
                "explanation":
                "Market data unavailable."
            })

        candles = market_data["values"]

        prices = []

        for candle in candles:

            prices.append(
                float(candle["close"])
            )

        current_price = prices[0]

        average_price = (
            sum(prices) / len(prices)
        )

        gains = []

        losses = []

        for i in range(1, len(prices)):

            change = (
                prices[i - 1] -
                prices[i]
            )

            if change > 0:

                gains.append(change)

            else:

                losses.append(
                    abs(change)
                )

        avg_gain = (
            sum(gains) / len(gains)
            if gains else 1
        )

        avg_loss = (
            sum(losses) / len(losses)
            if losses else 1
        )

        rs = avg_gain / avg_loss

        rsi = (
            100 -
            (100 / (1 + rs))
        )

        if (
            current_price >
            average_price
            and rsi < 70
        ):

            signal = "BUY"

            explanation = (
                f"{pair} bullish. "
                f"RSI: {round(rsi,2)}"
            )

        elif (
            current_price <
            average_price
            and rsi > 30
        ):

            signal = "SELL"

            explanation = (
                f"{pair} bearish. "
                f"RSI: {round(rsi,2)}"
            )

        else:

            signal = "WAIT"

            explanation = (
                f"Neutral market. "
                f"RSI: {round(rsi,2)}"
            )

        send_telegram_message(
            f"""
🚀 {signal} SIGNAL

Pair: {pair}

Price: {current_price}

RSI: {round(rsi,2)}

{explanation}
"""
        )

        return jsonify({

            "signal": signal,

            "price": current_price,

            "rsi": round(rsi, 2),

            "explanation":
            explanation

        })

    except Exception as e:

        print("Signal Error:", e)

        return jsonify({

            "signal": "ERROR",

            "price": "N/A",

            "explanation":
            "Could not fetch data."

        })

# =========================
# RUN APP
# =========================

if __name__ == "__main__":

    app.run(debug=True)