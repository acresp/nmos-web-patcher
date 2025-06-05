from flask import Flask
from routes.main import main_bp
from routes.settings import settings_bp
from routes.api import api_bp
from services.cache import refresh_discovery, start_auto_refresh
import os

app = Flask(__name__)
app.register_blueprint(main_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(api_bp)

if __name__ == "__main__":
    from services.cache import refresh_discovery, start_auto_refresh

    refresh_discovery()
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_auto_refresh()

    app.run(host="0.0.0.0", port=5000, debug=True)
