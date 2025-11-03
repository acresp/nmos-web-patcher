# nmos-web-patcher.py
# by Arnaud Cresp - 2025

from flask import Flask
from routes.main import main_bp
from routes.settings import settings_bp
from routes.api import api_bp
from __version__ import __version__
import json
import builtins
import asyncio
from werkzeug.serving import run_simple
import threading
import atexit
import sys

class QuietExit:
    def write(self, *args, **kwargs):
        pass

    def flush(self):
        pass

def silent_thread_shutdown():
    try:
        for t in threading.enumerate():
            if t is not threading.main_thread():
                t.join(timeout=0.2)
    except Exception:
        pass

atexit.register(silent_thread_shutdown)

app = Flask(__name__)
app.register_blueprint(main_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(api_bp)

def load_settings():
    try:
        with open("settings.json") as f:
            return json.load(f)
    except Exception:
        return {}


settings = load_settings()

builtins.videohub_emulator = None
builtins.rosstalk_emulator = None
builtins.main_event_loop = None

@app.context_processor
def inject_version():
    return dict(app_version=__version__)

async def graceful_shutdown(tasks):
    print("\n[EXIT] Stopping, cleaning threads")
    for task in tasks:
        if isinstance(task, asyncio.Task):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    print("[EXIT] nmos-web-patcher has been stopped")

async def run_all():

    from services.cache import refresh_discovery, start_auto_refresh, wait_cache_ready
    from protocols.bmdvideohub import VideohubEmulator
    from protocols.rosstalk import RossTalkEmulator

    print("[INFO] Refreshing NMOS discovery cache (init)...")
    refresh_discovery(timeout=8)

    start_auto_refresh(kickoff=False)

    builtins.main_event_loop = asyncio.get_running_loop()

    print("[INIT] Waiting for NMOS cache to be ready...")
    await asyncio.to_thread(wait_cache_ready, 30)
    print("[INIT] NMOS cache is ready. Starting emulators.")

    def run_flask():
        run_simple("0.0.0.0", 5000, app, use_debugger=True, use_reloader=False)

    flask_task = asyncio.create_task(asyncio.to_thread(run_flask))
    tasks = [flask_task]

    # BMD Emulator
    if settings.get("enable_bmd_emulator", False):
        videohub_emulator = VideohubEmulator()
        builtins.videohub_emulator = videohub_emulator
        bmd_task = asyncio.create_task(videohub_emulator.start())
        tasks.append(bmd_task)
        print("[SETTINGS] Blackmagic Videohub Emulator Enabled")
    else:
        print("[SETTINGS] Blackmagic Videohub Emulator Disabled")

    # RossTalk
    if settings.get("enable_rosstalk_emulator", False):
        rosstalk_emulator = RossTalkEmulator()
        builtins.rosstalk_emulator = rosstalk_emulator
        ross_task = asyncio.create_task(rosstalk_emulator.start())
        tasks.append(ross_task)
        print("[SETTINGS] RossTalk Emulator Enabled")
    else:
        print("[SETTINGS] RossTalk Emulator Disabled")

    # REST API
    if settings.get("enable_restapi", False):
        from protocols.restapi import restapi_bp
        app.register_blueprint(restapi_bp)
        print("[SETTINGS] REST API Enabled")
    else:
        print("[SETTINGS] REST API Disabled")

    print(f"[CREDITS] NMOS Web Patcher v{__version__} starting...")
    print("[CREDITS] by Arnaud Cresp")
    print("[CREDITS] https://github.com/acresp/nmos-web-patcher")
    print("[CREDITS] https://coff.ee/acresp")

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        await graceful_shutdown(tasks)

if __name__ == "__main__":
    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        print("\n[APP QUIT]")
    except Exception as e:
        print(f"[FATAL] Unexpected error: {e}")
    finally:
        sys.stderr = QuietExit()