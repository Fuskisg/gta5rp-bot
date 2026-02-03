from flask import Blueprint

from .settings import settings_bp
from .antiafk import antiafk_bp
from .bonuspoint import bonus_bp
from .port import port_bp
from .demorgan import demorgan_bp
from .cooking import cooking_bp
from .gym import gym_bp
from .stroyka import stroyka_bp
from .keybinds import keybinds_bp
from core.api import api

pages_bp = Blueprint('pages', __name__, template_folder='templates', static_folder='static')

pages_bp.register_blueprint(api)
pages_bp.register_blueprint(settings_bp)
pages_bp.register_blueprint(antiafk_bp)
pages_bp.register_blueprint(bonus_bp)
pages_bp.register_blueprint(port_bp)
pages_bp.register_blueprint(demorgan_bp)
pages_bp.register_blueprint(cooking_bp)
pages_bp.register_blueprint(gym_bp)
pages_bp.register_blueprint(stroyka_bp)
pages_bp.register_blueprint(keybinds_bp)
