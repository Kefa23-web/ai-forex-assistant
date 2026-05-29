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

from database import db, User

# =========================
# APP CONFIG
# =========================

app = Flask(__name__)

app.config["SECRET_KEY"] = "secret123"

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
# API KEYS
# =========================

API_KEY = "c5275832b53746aaa91c73e81ebc8029"

BOT_TOKEN = "8732156110:AAFO7w_fYgjEwXp_UGeYEOPI0U0q3v-kA0k"

CHAT_ID = "8526786741"

# =========================
# TELEGRAM FUNCTION
# =========================

def send_telegram_message(message):

    telegram_url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    requests.get(
        telegram_url,
        params={
            "chat_id": CHAT_ID,
            "text": message
        }
    )

# =========================
# CREATE DATABASE
# =========================

with app.app_context():
    db.create_all()

# =========================
# HOME
# =========================

@app.route("/")
def home():

    return render_template("index.html")

# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        hashed_password = (
            generate_password_hash(password)
        )

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:

            return "Username already exists"

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

        if user and check_password_hash(
            user.password,
            password
        ):

            login_user(user)

            return redirect(url_for("dashboard"))

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

    return render_template("payment.html")

# =========================
# LOGOUT
# =========================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(url_for("login"))

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

        api_pair = symbol_map[pair]

        url = (
            f"https://api.twelvedata.com/"
            f"time_series?"
            f"symbol={api_pair}"
            f"&interval=5min"
            f"&outputsize=20"
            f"&apikey={API_KEY}"
        )

        response = requests.get(url)

        market_data = response.json()

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
                prices[i - 1] - prices[i]
            )

            if change > 0:

                gains.append(change)

            else:

                losses.append(abs(change))

        avg_gain = (
            sum(gains) / len(gains)
            if gains else 1
        )

        avg_loss = (
            sum(losses) / len(losses)
            if losses else 1
        )

        rs = avg_gain / avg_loss

        rsi = 100 - (100 / (1 + rs))

        if (
            current_price > average_price
            and rsi < 70
        ):

            signal = "BUY"

            explanation = (
                f"{pair} bullish. "
                f"RSI: {round(rsi,2)}"
            )

        elif (
            current_price < average_price
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

        telegram_message = f"""
🚀 {signal} SIGNAL

Pair: {pair}

Price: {current_price}

RSI: {round(rsi,2)}

{explanation}
"""

        send_telegram_message(
            telegram_message
        )

        return jsonify({
            "signal": signal,
            "price": current_price,
            "rsi": round(rsi,2),
            "explanation": explanation
        })

    except Exception as e:

        print(e)

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