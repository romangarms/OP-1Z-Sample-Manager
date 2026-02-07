"""Integrations blueprint package.

Keep this module lightweight: define the blueprint and import route modules
so their decorators register endpoints.
"""

from flask import Blueprint

integrations_bp = Blueprint("integrations", __name__)

# Import route modules so their decorators register endpoints
from . import op1fun  # noqa: F401,E402