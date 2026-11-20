# Landscaping AI Estimator

**CS 4604 Introduction to Database Systems, Virginia Tech, Fall 2026 · Group 6**

Landscaping AI Estimator is a database application that connects homeowners with landscaping contractors. A customer registers a property and describes a project. The system generates an AI price estimate, contractors send quotes, and the accepted quote becomes a job that is invoiced and paid, all in one MariaDB database.

The application runs on your computer and stores its data in the team's MariaDB database on Virginia Tech's CS Launch (Discovery) cluster. Every change made in the app shows up in [phpMyAdmin](https://landscapingtool.discovery.cs.vt.edu/) (VT network or VPN required).

---

## Users and what they can do

Three types of users log in with their own username and password. Customers and contractors can sign up on the login page. Administrators can't sign up: the first one is created from the command line, and only an administrator can create more.

| User | Main tasks |
|------|------------|
| **Customer** | Add and edit properties · request a project and get an instant AI estimate · compare, accept or reject contractor quotes · book site visits · pay invoices · view 5 spending reports · edit profile and change password |
| **Contractor** | Browse open project requests · send, edit or withdraw quotes · schedule jobs from accepted quotes and update their status · send invoices · confirm site visits · view 5 earnings reports · edit profile and change password |
| **Administrator** | Manage customers, properties, contractors, plans, site visits and photos · oversee the request → estimate → quote → job → invoice → payment workflow · view 11 business reports, 5 of them managerial · create other administrators · change password |

Every screen is organized by task, not by table, and shows names, addresses and project descriptions rather than record IDs. Users never type SQL; for the class demo, a **Show SQL** button reveals the statement each action ran.

### Accounts and security

- Accounts are stored in database tables: `CUSTOMER`, `CONTRACTOR` and `ADMIN`. No passwords are hardcoded.
- Passwords are stored as salted PBKDF2-SHA256 hashes (600,000 iterations), never as plain text.
- Every user can sign up (customers and contractors), log in, log out and change their password.
- Five failed logins lock that account for 5 minutes.
- Customers and contractors can only see and change their own records. The server checks ownership on every write.

---

## Reports

| User | Reports | Aggregates used |
|------|---------|-----------------|
| Customer | My Spending by Contractor · Quote Comparison per Request · Projects & Spending by Property · My Invoices by Status · My Payments by Method | COUNT, SUM, AVG, MIN, MAX |
| Contractor | My Monthly Earnings · My Quotes by Outcome · My Pricing vs. Estimate by Lot Size · My Top Customers · My Invoices & Collections by Status | COUNT, SUM, AVG, MIN, MAX |
| Administrator (managerial) | Business Overview · Job Value Statistics by Status · Contractor Performance Leaderboard · Monthly Revenue Trend · Customers & Property Sizes by Plan | COUNT, SUM, AVG, MIN, MAX |
| Administrator (operations) | Revenue & Profit by Plan · Outstanding Invoices · Customers Owing More Than $500 · AI Estimate vs. Contractor Quote · Contractors With No Accepted Quote · Job Summary | COUNT, SUM, views, subqueries |

Customer and contractor reports cover only that user's own data, and each report includes a bar chart.

---

## Database

- **13 tables:** `SUBSCRIPTION_PLAN`, `CUSTOMER`, `CONTRACTOR`, `ADMIN`, `PROPERTY`, `PROJECT_REQUEST`, `PHOTO`, `AI_ESTIMATE`, `CONTRACTOR_QUOTE`, `APPOINTMENT`, `JOB`, `INVOICE`, `PAYMENT`.
- **Sample data:** 30 rows in every entity table, plus 3 subscription plans.
- **Views:**
  - `v_job_summary`: each job with its customer, property, contractor, estimate, quote and profit.
  - `v_invoice_balance`: each invoice with the amount paid and the balance due.
- **Triggers:** `trg_payment_insert_mark_paid` and `trg_payment_update_mark_paid` mark an invoice Paid once completed payments cover the amount due.
- **Indexes** on the columns the app searches and the reports filter on.
- **Foreign keys** use `ON UPDATE CASCADE`. Deletes cascade down the project workflow, and deleting a plan sets its customers' plan to `NULL`.

The ER diagram, relational schema and ER report are in [`ER_Diagram/`](ER_Diagram/).

---

## Quick start (Windows)

1. Install kubectl:
   ```bash
   winget install -e --id Kubernetes.kubectl
   ```
2. Sign in to [CS Launch](https://launch.cs.vt.edu) and open the **discovery** cluster. Click **Download KubeConfig** and save the file as `%USERPROFILE%\.kube\config`.
3. From the repository root, start the database tunnel and the app together. The script asks for the MariaDB username and password.
   ```bash
   powershell -ExecutionPolicy Bypass -File Phase_3\app\start_mariadb.ps1
   ```
4. The first time only, create the first administrator in another terminal:
   ```bash
   py Phase_3\app\server.py create-admin <username>
   ```
5. Open http://localhost:8080 and log in.

To try the app without CS Launch, run `py Phase_3\app\server.py --demo`. It uses a local SQLite copy of the same schema and data, and nothing it changes reaches phpMyAdmin.

See [`Phase_3/README.md`](Phase_3/README.md) for setup on macOS and Linux, resetting passwords, rebuilding the database, and troubleshooting.

---

## Repository layout

```text
├── README.md                     This file
├── ID.txt                        Team information
├── ER_Diagram/                   ER diagram, relational schema, ER report (design phase)
├── CS4604_Group6_Phase3-2_Report.pdf
├── Phase_3/
│   ├── README.md                 Setup and operations guide
│   ├── app/
│   │   ├── server.py             Web server, login, admin portal and reports
│   │   ├── portal.html           Customer and contractor pages
│   │   ├── start_mariadb.ps1     Starts the CS Launch tunnel and the server (Windows)
│   │   └── requirements.txt      Python driver for MariaDB (PyMySQL)
│   ├── sql/
│   │   ├── landscaping_phase2_schema_and_data.sql   Full schema, 30-row sample data, views, triggers, indexes
│   │   ├── add_admin_table.sql   Adds ADMIN to an older database
│   │   └── hash_existing_sample_passwords.sql       One-time migration from placeholder passwords
│   ├── php/                      Phase 2 PHP portal (earlier prototype, not used by the final app)
│   ├── screenshots/              Screenshots used in the phase reports
│   └── CS4604_Group6_Phase2_Report.pdf, report.html
└── index.html, style.css, app.js, assets/
                                  Front-end marketing prototype from the proposal phase
                                  (static page, not connected to the database)
```

---

## Team and roles

| Member | Role | Main contributions |
|--------|------|--------------------|
| **Zachary Brosius** | Database architect | Drew the ER diagram & worked on relational schema diagram. Designed the schema, constraints and foreign-key actions. Moved the database to CS Launch, connected the app to it, and replaced the sample passwords with hashes. Reviewed code and fixed issues. |
| **Saveer Pande** | Backend and database integration | Built the update and search features and the full project workflow screens, with dropdowns filled from parent tables. Delivered Phase 3 part 2. Prepared the final submission: 30-row sample data, views and triggers on the live database, the ADMIN table in the schema, and documentation. Reviewed code and fixed issues.|
| **Benny He** | Application and UI lead | Drew the original ER diagram and relational schema. Built role-based login, sign up and change password, the customer and contractor portals, all role and managerial reports with charts, the task-oriented interface, admin management of contractors, plans, visits and photos, and the CS Launch launcher. Reviewed code and fixed issues. |
| **Ahmad Abu Harb** | Integration and documentation | Built the front-end prototype website. Delivered Phase 2: database connection, insert and delete in the GUI, sample data, the PHP portal, screenshots and the Phase 2 report. Worked on Phase 1 and 3 reports. Reviewed code and fixed issues. |
