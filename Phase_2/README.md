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

### 🚀 How to Run the GUI Locally (Zero Setup)
You can run and interact with the full GUI portal directly on your computer:
1. Open Terminal and navigate to the `app/` directory:
   ```bash
   cd ~/Desktop/CS4604_Group6_Phase2/app
   python3 server.py
   ```
2. Open your web browser (Chrome / Safari / Firefox) and visit:
   ```text
   http://localhost:8080
   ```
3. You can click **"+ Insert New Customer"** to add records, click **"Delete"** on any row to delete records, and use the **"Database Query Inspector"** to execute live SQL queries!

---

### 🌐 How to Deploy to VT Discovery Server (`landscapingtool.discovery.cs.vt.edu`)
1. Import `sql/landscaping_phase2_schema_and_data.sql` into phpMyAdmin (`https://landscapingtool.discovery.cs.vt.edu`).
2. Upload the contents of the `php/` folder into your web root (`/var/www/html/` or your discovery project directory).
3. Update `config.php` credentials if your MariaDB user/password differs from default.

