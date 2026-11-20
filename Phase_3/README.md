# Landscaping AI Estimator: setup and operations guide

This guide covers running the final application, which is CS 4604 Group 6's Phase 3 work. For the project overview, user roles, reports and team, see the [main README](../README.md).

The application is a Python web server, [`app/server.py`](app/server.py), that runs on your computer at http://localhost:8080. It stores data in the `landscaping_db` MariaDB database on the CS Launch **discovery** cluster (namespace `ai-landscaping-db`, service `mariadb`). The database isn't exposed to the internet, so the app reaches it through a `kubectl port-forward` tunnel on `localhost:3307`.

## Requirements

- Python 3.10 or newer (`py` on Windows, `python3` on macOS and Linux)
- kubectl
- Your own Discovery KubeConfig from [CS Launch](https://launch.cs.vt.edu)
- The MariaDB username and password for `landscaping_db`. These are separate from your VT login; ask the team.

## Run on Windows

1. Install kubectl, then open a new terminal so it's on your PATH:
   ```bash
   winget install -e --id Kubernetes.kubectl
   ```
2. Sign in to CS Launch, open the **discovery** cluster, and click **Download KubeConfig**. Save the file as `%USERPROFILE%\.kube\config`. It contains your personal access token, so keep it out of Git.
3. Check that you can reach the database namespace:
   ```bash
   kubectl -n ai-landscaping-db get pods
   ```
4. From the repository root, create the virtual environment once:
   ```bash
   py -m venv Phase_3\app\.venv
   ```
   ```bash
   Phase_3\app\.venv\Scripts\python.exe -m pip install -r Phase_3\app\requirements.txt
   ```
5. Start the tunnel and the server together. The script asks for the MariaDB username and password.
   ```bash
   powershell -ExecutionPolicy Bypass -File Phase_3\app\start_mariadb.ps1
   ```
6. Open http://localhost:8080.

To skip the username prompt, copy `app/db_config.local.example.json` to `app/db_config.local.json` and fill in `DB_USER`. That file is git-ignored. Add `DB_PASS` only on a private machine.

`py Phase_3\app\server.py` on its own also works: if `localhost:3307` isn't open, it starts the port-forward itself.

## Run on macOS or Linux

Set up kubectl and the KubeConfig as in steps 1–3 above, saving the KubeConfig as `~/.kube/config`. Then:

```bash
python3 -m venv Phase_3/app/.venv
Phase_3/app/.venv/bin/python -m pip install -r Phase_3/app/requirements.txt
kubectl -n ai-landscaping-db port-forward svc/mariadb 3307:3306 &
Phase_3/app/.venv/bin/python Phase_3/app/server.py
```

The server asks for the MariaDB username and password. You can also set `DB_USER` and `DB_PASS` in the environment.

## Accounts

| Task | How |
|------|-----|
| Create the **first** administrator | `py Phase_3/app/server.py create-admin <username>`. This works only while the `ADMIN` table is empty. |
| Add more administrators | Log in as an admin and use **Add admin** in the app |
| Sign up as a customer or contractor | Use **Sign up** on the login page |
| Change your password | Use **Change password** in the top bar after logging in. This also logs out your other sessions. |
| Log in as a sample customer or contractor | Sample passwords are hashes of random values. Give one a known password with `py Phase_3/app/server.py reset-password customer john.smith@gmail.com`. Contractor e-mails work the same way. |

Customers and contractors log in with their e-mail address, and administrators with their username. Sessions last 8 hours, and restarting the server logs everyone out.

## Role pages

After logging in, each account type lands on its own page.

| Role | Page | What it can do |
|------|------|----------------|
| Administrator | `/` | Manage customers, properties and the full project workflow. The **Contractors & More** tab manages contractors, site visits, photos and subscription plans. Reports and **Add admin** are here too. |
| Customer | `/customer` | Manage properties. Submit project requests, which create an AI estimate. Accept or reject quotes, book site visits, pay invoices, view reports and edit the profile. |
| Contractor | `/contractor` | Quote open requests. Edit or withdraw pending quotes. Schedule jobs from accepted quotes, update job status, send invoices, confirm visits, view reports and edit the profile. |

The server takes the account from the login session, never from the request. Each write checks that the record belongs to that account. Pages show names instead of record IDs. **Show SQL** in the top bar reveals the statement each action ran, which is useful for report screenshots. The app has no free-form SQL console; all database access goes through these screens.

## Offline demo (SQLite)

```bash
py Phase_3/app/server.py --demo
```

This builds `app/landscaping.db` from the seed SQL file on first run and needs no tunnel or MariaDB login. Changes stay in that file and don't appear in phpMyAdmin. Delete `landscaping.db` to start over, then create an admin with `py Phase_3/app/server.py --demo create-admin <username>`.

## Database files

| File | Use |
|------|-----|
| [`sql/landscaping_phase2_schema_and_data.sql`](sql/landscaping_phase2_schema_and_data.sql) | Complete schema (13 tables), 30 sample rows per entity table, 2 views, 2 triggers and 6 indexes. It **drops and recreates every table**, so import it into phpMyAdmin only for a fresh database. |
| [`sql/add_admin_table.sql`](sql/add_admin_table.sql) | Adds the `ADMIN` table to an older database. The server normally creates this table itself; run the file only if the app's database account can't create tables. |
| [`sql/hash_existing_sample_passwords.sql`](sql/hash_existing_sample_passwords.sql) | One-time migration that replaced the old placeholder sample passwords with hashes. It's already applied to the live database. |

The live CS Launch database already has the full schema, views, triggers and 30+ rows per table. Use it as is.

## Troubleshooting

| Message | Fix |
|---------|-----|
| `kubectl is not installed` | Run `winget install -e --id Kubernetes.kubectl`, then open a new terminal. |
| `The port-forward failed` / `Unauthorized` | Your KubeConfig is missing or expired. Download a new one from CS Launch to `%USERPROFILE%\.kube\config`. |
| `Cannot reach MariaDB at 127.0.0.1:3307` | The tunnel isn't running. Start it with `kubectl -n ai-landscaping-db port-forward svc/mariadb 3307:3306`. |
| `Access denied for user` | Wrong MariaDB username or password. |
| `No administrator exists yet` | Create one with `create-admin`; see **Accounts**. |
| phpMyAdmin returns 403 | Connect to the VT network or VPN. |

## Earlier prototypes

`php/` is the Phase 2 PHP portal, and `report.html`, `CS4604_Group6_Phase2_Report.pdf` and `screenshots/` are Phase 2 and 3 report material. The final application doesn't use them; they're kept for the course record.
