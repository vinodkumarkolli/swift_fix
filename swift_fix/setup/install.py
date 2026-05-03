from swift_fix.setup.roles import create_roles
from swift_fix.setup.permissions import setup_permissions


def after_install():
    create_roles()
    setup_permissions()