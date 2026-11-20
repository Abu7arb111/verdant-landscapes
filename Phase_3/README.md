# CS 4604 Introduction to Database Systems — Phase 2
## Group 6: Landscaping AI Estimator

### 👥 Team Members & Contributions
1. **Zachary Brosius** (`ztbrosuis@vt.edu`) — Database Architect & Integrity Engineer
   - Configured relational schema constraints and foreign key actions (`ON DELETE CASCADE`, `ON UPDATE CASCADE`) in MariaDB.
   - Validated sample data population with at least 20 tuples across all 12 relational tables.
   - Designed SQL mutation statements ensuring ACID transaction safety during concurrent GUI modifications.

2. **Saveer Pande** (`spande@vt.edu`) — Backend & Database Integration Lead
   - Established and verified interface-to-database communication pipeline via PHP PDO / MySQLi.
   - Built server-side data handlers processing HTTP POST payloads for insertion and deletion.
   - Structured database error handling, constraint violation checks, and live query execution logging.

3. **Benny He** (`bennyhe163@vt.edu`) — Frontend UI/UX & Interaction Developer
   - Developed the GUI Management Portal with real-time responsive dashboard and table views.
   - Created interactive modal dialogs for tuple entry with input validation (regex formatting for phone, email, and numeric types).
   - Built the delete confirmation dialogs and dynamic SQL reflection log interface.

4. **Ahmad Abu Harb** (`ahmad@vt.edu`) — Full-Stack Integration & Documentation Lead
   - Coordinated end-to-end integration linking GUI triggers directly to database queries.
   - Tested and validated Insert and Delete operations, ensuring immediate two-way reflection between UI and database tables.
   - Compiled the technical verification report, captured visual proof screenshots, and packaged deliverables.

---

### 📂 Submission Package Structure
```text
CS4604_Group6_Phase2/
├── CS4604_Group6_Phase2_Report.pdf   <-- Complete Professor-Ready Submission PDF with Screenshots
├── README.md                         <-- Project Documentation & Quick Start
├── report.html                       <-- Source HTML for the PDF Report
├── screenshots/                      <-- High-Resolution Verification Screenshots
│   ├── 01_connection_and_initial_table.png
│   ├── 02_insert_modal_form.png
│   ├── 03_insert_success_gui.png
│   ├── 04_insert_reflected_in_database.png
│   ├── 05_delete_confirmation_modal.png
│   ├── 06_delete_success_gui.png
│   ├── 07_delete_reflected_in_database.png
│   └── 08_properties_major_table.png
├── sql/
│   └── landscaping_phase2_schema_and_data.sql  <-- Complete DDL + 20+ Sample Tuples per Table
├── php/                              <-- Production PHP Portal for Apache / Discovery Server
│   ├── config.php
│   ├── header.php
│   ├── footer.php
│   ├── index.php
│   ├── customers.php
│   ├── properties.php
│   └── css/style.css
└── app/                              <-- Zero-Dependency Local Runner (Python 3)
    ├── server.py
    └── landscaping.db
```

---

### Run the GUI against the database in phpMyAdmin

The Python GUI can connect to the existing `landscaping_db` schema on VT Discovery. GUI inserts, updates, and deletes commit directly to that schema. Open [phpMyAdmin](https://landscapingtool.discovery.cs.vt.edu/), select the table, and refresh **Browse** to see the latest rows.

From the repository root, install the driver in a virtual environment:

```bash
python3 -m venv Phase_3/app/.venv
Phase_3/app/.venv/bin/python -m pip install -r Phase_3/app/requirements.txt
```

The HTTPS address opens phpMyAdmin. The Python GUI runs on your computer and connects to the CSLaunch service `mariadb` in namespace `ai-landscaping-db`. On the Discovery cluster dashboard, use **Copy KubeConfig** and save it privately as `~/.kube/config`. See the [VT CSLaunch terminal guide](https://wiki.cs.vt.edu/index.php/HowTo%3ACS_Launch_Terminal) for kubectl setup. Forward the database service in a separate terminal:

```bash
kubectl -n ai-landscaping-db port-forward svc/mariadb 3307:3306
```

Leave the port-forward running while you use the GUI.

In another terminal, start the GUI through the tunnel:

```bash
export DB_HOST=127.0.0.1 DB_PORT=3307 DB_NAME=landscaping_db
read -rp "MariaDB user: " DB_USER
read -rsp "MariaDB password: " DB_PASS
echo
export DB_USER DB_PASS
Phase_3/app/.venv/bin/python Phase_3/app/server.py
```

Open `http://localhost:8080` and check for **MariaDB** in the database banner. The GUI uses the existing schema and does not import or reset it. Use phpMyAdmin for custom SQL.

**On Windows, one command does both steps.** It starts the port-forward and then the server, and asks for the MariaDB user and password:

```powershell
powershell -ExecutionPolicy Bypass -File Phase_3\app\start_mariadb.ps1
```

To skip the user prompt, copy `Phase_3/app/db_config.local.example.json` to `db_config.local.json` and fill in `DB_USER`. That file is git-ignored. Add `DB_PASS` only on a private machine.

If the server has no MariaDB settings, it refuses to start, so website changes can't silently miss phpMyAdmin.

### Run the local SQLite demo

Run `python3 Phase_3/app/server.py --demo` and open `http://localhost:8080`. Demo edits stay in `Phase_3/app/landscaping.db` and do **not** appear in phpMyAdmin.

### Role pages

After logging in, each account type lands on its own page. Every action writes to the database, and the page shows the SQL that ran.

| Role | Page | What it can do |
|------|------|----------------|
| Administrator | `/` | Full management portal: all tables, workflow, reports |
| Customer | `/customer` | Add, edit, and delete properties. Submit project requests, which create an `AI_ESTIMATE` row. Accept or reject quotes, book site visits, pay invoices, and edit the profile. |
| Contractor | `/contractor` | Quote open requests. Edit or withdraw pending quotes. Schedule jobs from accepted quotes, update job status, send invoices, confirm visits, and edit the profile. |

The server takes the account ID from the login session. Each write checks ownership, so customers and contractors can change only their own records.

---

### Configure the PHP portal on CSLaunch

For a PHP portal already running on CSLaunch, set `DB_HOST` to the internal MariaDB service name, `DB_PORT=3306`, and `DB_NAME` to the schema shown in phpMyAdmin. Set `DB_USER` and `DB_PASS` from a CSLaunch Secret. The PHP runtime needs PDO MySQL.

For a fresh database only, import `sql/landscaping_phase2_schema_and_data.sql` into phpMyAdmin.

