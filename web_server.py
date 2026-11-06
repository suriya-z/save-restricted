import threading
from flask import Flask

def create_keep_alive_app() -> Flask:
    """Creates a lightweight Flask application for Render HTTP health probes."""
    app = Flask(__name__)

    @app.route("/")
    def health_check():
        return "Bot is running online!"

    return app

def start_keep_alive(port: int = 8080) -> threading.Thread:
    """Spins up the health-check web server in a daemon thread."""
    app = create_keep_alive_app()
    thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, use_reloader=False),
        daemon=True
    )
    thread.start()
    return thread
