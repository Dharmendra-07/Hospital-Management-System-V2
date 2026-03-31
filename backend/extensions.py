"""
backend/extensions.py
Shared Flask extension instances.
Import from here everywhere to avoid circular imports.
"""

from flask_mail    import Mail
from flask_caching import Cache
from flask_jwt_extended import JWTManager

mail  = Mail()
cache = Cache()
jwt   = JWTManager()
