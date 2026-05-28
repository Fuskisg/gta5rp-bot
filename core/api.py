from flask import Blueprint, Response, jsonify, render_template, request, send_from_directory
import os
import queue
import logging
import requests
from core.common import hotkey_manager, state, clients, _clients_lock, add_log
import core.common as common

logger = logging.getLogger(__name__)

api = Blueprint('api', __name__)

@api.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(api.root_path, 'static'),'favicon.ico', mimetype='image/vnd.microsoft.icon')

@api.route('/index')
def index():
    return render_template('index.html', version=common.version, online=common.cached_online, update_info=common.cached_update)

@api.route('/api/set_active_tab/<name>', methods=['POST'])
def set_active_tab(name):
    state["current_page"] = name
    logger.info(f"Активная вкладка изменена на: {name}")
    try:
        hotkey_manager.clear()
        try:
            page_module = __import__(f"pages.{name}", fromlist=['register_hotkeys'])
            if hasattr(page_module, 'register_hotkeys'):
                page_module.register_hotkeys(hotkey_manager)
        except Exception as e:
            add_log(f"Нет модуля {name}", "WARNING")
    except Exception as e:
        add_log(f"Ошибка при регистрации хоткеев для страницы {name}: {e}", "ERROR")
    return jsonify({"status": "ok"})

@api.route('/api/events')
def events():
    def stream():
        q = queue.Queue()
        with _clients_lock:
            clients.append(q)
        for log in state["logs"]: 
            yield f"data: {log}\n\n"
        try:
            while True:
                try:
                    msg = q.get(timeout=15)
                    yield f"data: {msg}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            with _clients_lock:
                if q in clients:
                    clients.remove(q)
    return Response(stream(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

@api.route('/api/get_logs')
def get_logs():
    return jsonify({"logs": state["logs"]})

@api.route('/api/get_online')
def get_online():
    return jsonify({"online": common.cached_online})

def check_update_once():
    try:
        response = requests.get("https://codeberg.org/dornode/bot/raw/branch/v2-rewrite/version.json", timeout=5)
        if response.status_code == 200:
            data = response.json()
            remote_version = str(data.get("version", "")).strip()
            download_link = str(data.get("link", "")).strip()
            local_version = common.version.strip()
            try:
                needs_update = float(remote_version) > float(local_version)
            except ValueError:
                needs_update = False
            common.cached_update = {"needs_update": needs_update, "remote_version": remote_version, "local_version": local_version, "download_link": download_link}
        else:
            common.cached_update = {"needs_update": False, "error": "server_error", "remote_version": "", "local_version": common.version, "download_link": ""}
    except Exception:
        common.cached_update = {"needs_update": False, "error": "network_error", "remote_version": "", "local_version": common.version, "download_link": ""}

def fetch_online_once():
    try:
        response = requests.get("https://purls.ru/online.php", timeout=5)
        if response.status_code == 200:
            common.cached_online = response.text.strip()
        else:
            common.cached_online = "ошибка сервера"
    except Exception:
        common.cached_online = "ошибка сети"