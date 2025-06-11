from flask import Flask
from routes.main import main_bp
from routes.settings import settings_bp
from routes.api import api_bp
from __version__ import __version__
import json
import os

app = Flask(__name__)
app.register_blueprint(main_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(api_bp)

def load_settings():
    try:
        with open("settings.json") as f:
            return json.load(f)
    except:
        return {}

settings = load_settings()
if settings.get("enable_restapi", False):
    from protocols.restapi import restapi_bp
    app.register_blueprint(restapi_bp)
    print("[SETTINGS] REST API Enabled")
else:
    print("[SETTINGS] REST API Disabled")

@app.context_processor
def inject_version():
    return dict(app_version=__version__)

if __name__ == "__main__":
    from services.cache import refresh_discovery, start_auto_refresh

    refresh_discovery()
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_auto_refresh()

    print(f"[CREDITS] NMOS Web Patcher v{__version__} starting...")
    print(f"[CREDITS] by Arnaud Cresp")
    print(f"[CREDITS] https://github.com/acresp/nmos-web-patcher")
    print(f"[CREDITS] https://coff.ee/acresp")

    app.run(host="0.0.0.0", port=5000, debug=True)
