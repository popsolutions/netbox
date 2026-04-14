# TurnKey NetBox - Infrastructure Resource Modeling

NetBox appliance for [TurnKey Linux](https://www.turnkeylinux.org), built on Debian 13 (Trixie) with the [TurnKey FAB](https://github.com/turnkeylinux/fab) build system.

[NetBox](https://netboxlabs.com/oss/netbox/) is the leading open-source solution for modeling and documenting network infrastructure. It covers IP address management (IPAM), data center infrastructure management (DCIM), circuits, virtualization, and more.

## What's Included

| Component | Details |
|-----------|---------|
| **NetBox** | 4.5.7 (upstream git) |
| **Python** | 3.13 with isolated venv at `/opt/netbox/venv` |
| **PostgreSQL** | 17 |
| **Redis** | Caching (DB 1) + task queue (DB 0) |
| **Nginx** | Reverse proxy with TLS termination (ports 80/443) |
| **Gunicorn** | WSGI server on `127.0.0.1:8001` |
| **Webmin** | System administration (ports 12320/12321) |
| **OIDC SSO** | Optional, compatible with Zitadel, Keycloak, Authentik |

## Quick Start

### Build the appliance

Requires [TurnKey FAB](https://www.turnkeylinux.org/tkldev) (TKLDev):

```bash
cd /turnkey/fab/products/Netbox
make
```

Output: `build/debian-13-turnkey-netbox_19.0-1_amd64.tar.gz` (LXC template) and ISO.

### Deploy as LXC container

```bash
# Create container from template
mkdir -p /var/lib/lxc/netbox/rootfs
tar xzf debian-13-turnkey-netbox_19.0-1_amd64.tar.gz -C /var/lib/lxc/netbox/rootfs

# Create config (/var/lib/lxc/netbox/config)
cat > /var/lib/lxc/netbox/config << 'EOF'
lxc.rootfs.path = dir:/var/lib/lxc/netbox/rootfs

lxc.net.0.type = veth
lxc.net.0.link = br0
lxc.net.0.flags = up

lxc.apparmor.profile = unconfined
lxc.apparmor.allow_nesting = 1

lxc.uts.name = netbox

lxc.autodev = 1
lxc.tty.max = 4
lxc.pty.max = 1024

lxc.cap.drop = sys_module mac_admin mac_override sys_time

lxc.cgroup2.devices.allow = a
lxc.mount.auto = cgroup:mixed proc:mixed sys:mixed
EOF

# Start and initialize
lxc-start -n netbox
lxc-attach -n netbox
turnkey-init
```

The first boot wizard will prompt for:

1. **Root password**
2. **PostgreSQL password**
3. **NetBox admin email and password** (with option to auto-generate a strong password)
4. **OIDC SSO** (optional) - endpoint, client ID, and secret

### Access

After initialization, access NetBox at `https://<container-ip>`.

## Project Structure

```
Netbox/
├── Makefile                    # Build config (ports, includes)
├── changelog                   # Release history
├── plan/
│   └── main                    # Debian packages to install
├── conf.d/
│   └── main                    # Build-time setup script
├── overlay/                    # Files overlaid onto root filesystem
│   ├── etc/
│   │   ├── confconsole/
│   │   │   └── services.txt    # TKL console service listing
│   │   ├── logrotate.d/
│   │   │   └── netbox          # Log rotation policy
│   │   ├── nginx/
│   │   │   └── sites-available/
│   │   │       └── netbox      # Nginx reverse proxy config
│   │   ├── resolv.conf         # Default DNS resolvers
│   │   └── systemd/system/
│   │       ├── netbox.service   # NetBox WSGI service
│   │       └── netbox-rq.service # Background task worker
│   └── usr/lib/
│       ├── inithooks/
│       │   ├── bin/
│       │   │   └── netbox.py    # First boot config (admin, OIDC)
│       │   └── firstboot.d/
│       │       └── 40netbox     # First boot hook launcher
│       └── python3/dist-packages/
│           └── libinithooks/
│               └── dialog_wrapper.py  # Enhanced dialog with password generator
└── removelist                  # Packages to remove after build
```

## Key Paths (inside the appliance)

| Path | Description |
|------|-------------|
| `/opt/netbox/` | NetBox installation root |
| `/opt/netbox/venv/` | Python virtual environment |
| `/opt/netbox/netbox/netbox/configuration.py` | Main configuration |
| `/opt/netbox/netbox/netbox/oidc_config.py` | OIDC SSO configuration |
| `/opt/netbox/gunicorn.py` | Gunicorn config |
| `/var/log/netbox/netbox.log` | Application log |
| `/etc/nginx/sites-available/netbox` | Nginx config |

## OIDC SSO

SSO can be configured at first boot or later by editing `/opt/netbox/netbox/netbox/oidc_config.py` and appending to `configuration.py`:

```python
exec(open('/opt/netbox/netbox/netbox/oidc_config.py').read())
```

Tested with Zitadel, Keycloak, and Authentik.

## Credits

- [NetBox](https://github.com/netbox-community/netbox) by NetBox Labs
- [TurnKey Linux](https://www.turnkeylinux.org) appliance framework
- Built by [PopSolutions Cooperativa de Tecnologia](https://pop.coop)

## License

This appliance integration code is licensed under the GNU General Public License v3 (GPLv3), consistent with TurnKey Linux. NetBox itself is licensed under the Apache License 2.0.
