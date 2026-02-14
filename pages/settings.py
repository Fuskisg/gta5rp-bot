from flask import Blueprint, render_template, jsonify, request
from core.common import add_log, get_settings, update_settings

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
def settings_page():
    settings = get_settings("settings")
    return render_template('settings.html', settings=settings)

@settings_bp.route('/api/settings/save', methods=['POST'])
def save_settings_api():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON data"}), 400

    settings = get_settings("settings")
    
    if 'switch_hover' in data:
        settings['switch_hover'] = data['switch_hover']
    if 'switch_click' in data:
        settings['switch_click'] = data['switch_click']
    if 'volume_hover' in data:
        settings['volume_hover'] = int(data['volume_hover'])
    if 'volume_click' in data:
        settings['volume_click'] = int(data['volume_click'])
    if 'background' in data:
        settings['background'] = data['background']
    
    if update_settings("settings", settings, page="settings"):
        add_log(f"Настройки обновлены: {data}", page="settings")
        return jsonify({"status": "ok"})
    else:
        return jsonify({"status": "error", "message": "Failed to save"}), 500

@settings_bp.route('/api/settings/get', methods=['GET'])
def get_settings_api():
    settings = get_settings("settings")
    return jsonify(settings)
