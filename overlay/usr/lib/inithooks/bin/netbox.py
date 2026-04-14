#!/usr/bin/env python3
"""TurnKey NetBox - First Boot Interactive Hook

Prompts for:
  1. NetBox superuser email
  2. NetBox superuser password
  3. (Optional) OIDC SSO endpoint, client ID, and client secret
"""

import sys
import os
import subprocess
import secrets
import re

from libinithooks.dialog_wrapper import Dialog

NETBOX_HOME = '/opt/netbox'
VENV_PYTHON = f'{NETBOX_HOME}/venv/bin/python'
MANAGE_PY = f'{NETBOX_HOME}/netbox/manage.py'
CONFIG_PY = f'{NETBOX_HOME}/netbox/netbox/configuration.py'
OIDC_PY = f'{NETBOX_HOME}/netbox/netbox/oidc_config.py'


def usage(s=None):
    if s:
        print("Error:", s, file=sys.stderr)
    print("Syntax: %s" % sys.argv[0], file=sys.stderr)
    print(__doc__, file=sys.stderr)
    sys.exit(1)


def update_config_value(filepath, key, value):
    """Replace a simple KEY = 'value' line in a Python config file."""
    with open(filepath, 'r') as f:
        content = f.read()
    pattern = rf"^{key}\s*=\s*['\"].*?['\"]"
    replacement = f"{key} = '{value}'"
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    with open(filepath, 'w') as f:
        f.write(content)


def update_config_value_in_dict(filepath, dict_name, key, value):
    """Replace a 'KEY': 'value' inside a dict in a Python config file."""
    with open(filepath, 'r') as f:
        content = f.read()
    pattern = rf"('{key}':\s*')[^']*(')"
    replacement = rf"\g<1>{value}\2"
    content = re.sub(pattern, replacement, content)
    with open(filepath, 'w') as f:
        f.write(content)


def main():
    d = Dialog('TurnKey Linux - First boot configuration')

    # -- Generate new secret key ----------------------------------------------
    secret_key = subprocess.check_output(
        [VENV_PYTHON, f'{NETBOX_HOME}/netbox/generate_secret_key.py'],
        text=True
    ).strip()

    update_config_value(CONFIG_PY, 'SECRET_KEY', secret_key)

    # -- Generate new database password ---------------------------------------
    db_pass = secrets.token_urlsafe(32)

    subprocess.run(
        ['su', '-', 'postgres', '-c',
         f"psql -c \"ALTER USER netbox WITH PASSWORD '{db_pass}';\""],
        check=True
    )
    update_config_value_in_dict(CONFIG_PY, 'DATABASE', 'PASSWORD', db_pass)

    # -- NetBox admin email ---------------------------------------------------
    email = d.get_email(
        "NetBox Admin Email",
        "Enter the email address for the NetBox superuser account.",
        "admin@example.com"
    )

    # -- NetBox admin password (generate or manual) ---------------------------
    password = d.get_password(
        "NetBox Admin Password",
        "Set the password for the NetBox superuser account.",
        pass_req=8,
    )

    # -- Create superuser -----------------------------------------------------
    env = os.environ.copy()
    env['DJANGO_SUPERUSER_PASSWORD'] = password
    env['DJANGO_SUPERUSER_EMAIL'] = email
    env['DJANGO_SUPERUSER_USERNAME'] = 'admin'

    subprocess.run(
        [VENV_PYTHON, MANAGE_PY, 'createsuperuser',
         '--no-input',
         '--username', 'admin',
         '--email', email],
        env=env,
        check=True
    )

    # -- OIDC SSO (optional) --------------------------------------------------
    sso = d.yesno(
        "Enable OIDC SSO?",
        "Do you want to configure OpenID Connect single sign-on?\n\n"
        "This is compatible with Zitadel, Keycloak, Authentik, "
        "and other OIDC providers.\n\n"
        "You can configure this later by editing:\n"
        f"  {OIDC_PY}",
        'n'
    )

    if sso:
        oidc_endpoint = d.get_input(
            "OIDC Endpoint",
            "Enter the OIDC discovery endpoint URL.\n\n"
            "Example: https://sso.pop.coop",
            ""
        )

        oidc_client_id = d.get_input(
            "OIDC Client ID",
            "Enter the OIDC Client ID.",
            ""
        )

        oidc_client_secret = d.get_input(
            "OIDC Client Secret",
            "Enter the OIDC Client Secret.",
            ""
        )

        # Write OIDC config
        with open(OIDC_PY, 'w') as f:
            f.write(f"""
REMOTE_AUTH_ENABLED = True
REMOTE_AUTH_AUTO_CREATE_USER = True

REMOTE_AUTH_BACKEND = 'social_core.backends.open_id_connect.OpenIdConnectAuth'

SOCIAL_AUTH_OIDC_OIDC_ENDPOINT = '{oidc_endpoint}'
SOCIAL_AUTH_OIDC_KEY = '{oidc_client_id}'
SOCIAL_AUTH_OIDC_SECRET = '{oidc_client_secret}'
SOCIAL_AUTH_PROTECTED_USER_FIELDS = ['groups']
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True
""")

        # Enable OIDC in main config by appending exec
        with open(CONFIG_PY, 'a') as f:
            f.write("\n# OIDC SSO - enabled at first boot\n")
            f.write(f"exec(open('{OIDC_PY}').read())\n")


if __name__ == '__main__':
    main()
