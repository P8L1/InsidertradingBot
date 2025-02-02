import threading
from flask import Flask, render_template, request, jsonify
from trading_bot import TradingBot, scrape_openinsider, trade_history, lock
import logging

# Initialize the Flask app
app = Flask(__name__)

# Initialize the trading bot
bot = TradingBot()


@app.route("/")
def index():
    """
    Displays the main dashboard of the trading bot.
    Shows current positions and the available budget.
    """
    positions_with_prices = {}
    with lock:
        for ticker, data in bot.positions.items():
            current_price = bot.get_current_price(ticker)
            gain_loss = ((current_price - data["buy_price"]) / data["buy_price"]) * 100
            positions_with_prices[ticker] = {
                "quantity": data["quantity"],
                "buy_price": data["buy_price"],
                "current_price": current_price,
                "gain_loss": round(gain_loss, 2),
            }

    with lock:
        return render_template(
            "index.html",
            budget=bot.budget,
            positions=positions_with_prices,
            trade_history=trade_history,
        )


def run_bot(insider_data, gain_threshold, drop_threshold):
    """
    Run the bot in a separate thread.
    """
    try:
        bot.run_trading_cycle(
            insider_data, gain_threshold=gain_threshold, drop_threshold=drop_threshold
        )
    except Exception as e:
        logging.error(f"Error while running the bot: {e}")


@app.route("/start", methods=["POST"])
def start_trading():
    """
    Start the trading bot with the provided OpenInsider URL and thresholds.
    Runs the bot in a separate thread to prevent blocking the Flask server.
    """
    custom_url = request.form["url"]  # Get the custom OpenInsider URL from the form
    gain_threshold = float(
        request.form["gain_threshold"]
    )  # Gain threshold (percentage)
    drop_threshold = float(
        request.form["drop_threshold"]
    )  # Drop threshold (percentage)

    # Scrape insider data from the provided URL
    insider_data = scrape_openinsider(custom_url)

    # Start the bot trading cycle in a background thread
    thread = threading.Thread(
        target=run_bot, args=(insider_data, gain_threshold, drop_threshold)
    )
    thread.start()

    return jsonify(
        {"status": "success", "message": "Trading bot started in background"}
    )


@app.route("/stop", methods=["POST"])
def stop_trading():
    """
    Stop the trading bot.
    """
    bot.stop()  # Set the flag to stop the bot
    return jsonify({"status": "success", "message": "Trading bot stopped"})


if __name__ == "__main__":
    # Run the Flask app
    app.run(debug=True)
