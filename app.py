from flask import Flask
from routes.main import main_bp
from routes.settings import settings_bp
from routes.api import api_bp

app = Flask(__name__)
app.register_blueprint(main_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(api_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
