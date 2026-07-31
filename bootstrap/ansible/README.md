# Deployment

Ansible playbooks for deploying to production and staging servers. All playbooks run on the server itself (`ansible_connection: local`).

## Prerequisites

Install Ansible collections before running any playbook for the first time:

```bash
ansible-galaxy collection install -r requirements.yml
```

## Deploy workflow

All commands run from `bootstrap/ansible/` on the target server. `ansible.cfg` sets `inventory = inventory/` so no `-i` flag is needed. The vault ID matches the host name.

**lrc-staging:**
```bash
git pull
ansible-playbook playbook-deploy.yml --limit lrc-staging --vault-id lrc-staging@prompt
```

**lrc-prod:**
```bash
git pull
ansible-playbook playbook-deploy.yml --limit lrc-prod --vault-id lrc-prod@prompt
```

**brc-prod:**
```bash
git pull
ansible-playbook playbook-deploy.yml --limit brc-prod --vault-id brc-prod@prompt
```

## Vault management

Secrets are stored in encrypted `vault.yml` files committed to the repository. Each environment has its own vault password. Vault variables use the `vault_` prefix and are referenced directly in templates and tasks — for example, `vault_django_secret_key`, `vault_db_admin_passwd`, `vault_redis_passwd`.

**View secrets:**
```bash
ansible-vault view inventory/host_vars/lrc-prod/vault.yml --vault-id lrc-prod@prompt
```

**Edit secrets:**
```bash
ansible-vault edit inventory/host_vars/lrc-prod/vault.yml --vault-id lrc-prod@prompt
```

## Inspecting resolved variables

To see every variable that would apply to a host — merging `group_vars/all`, `group_vars/lrc|brc`, and `host_vars` — without running the playbook:

```bash
# From bootstrap/ansible/
ansible-inventory --host lrc-prod --yaml
```

Note: role defaults (`roles/<role>/defaults/main.yml`) are not included here; they are only loaded at play runtime.

## Provisioning

Provisioning is not yet covered — the provisioning roles have not been updated for the new inventory structure.

> [!WARNING]
> Do not run `playbook.yml`. It is the legacy monolithic playbook and is disabled with a fail guard.

## Dynamic settings

Some configuration can be updated without a server restart (e.g., links to external resources). This is managed by `django-constance` and stored in Redis. To update, navigate to `/admin/constance/config/` in the portal and set the correct values.
