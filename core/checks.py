from django.conf import settings
from django.core.checks import Error, Tags, register

from core.security import admins_with_default_password, default_password_message


@register(Tags.security)
def admin_password_check(app_configs, **kwargs) -> list[Error]:
    """runserver и другие команды не стартуют при DEBUG=False и пароле админа «admin»."""
    if settings.DEBUG:
        return []
    weak = admins_with_default_password()
    if not weak:
        return []
    return [Error(default_password_message(weak), id="core.E001")]
