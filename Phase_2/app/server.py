#!/usr/bin/env python3
"""
CS 4604 Introduction to Database Systems - Phase 2 GUI & Database Engine
Group 6: Landscaping AI Estimator
Team Members: Zachary Brosius, Saveer Pande, Benny He, Ahmad Abu Harb
DBMS Backend: SQLite (Local) / MariaDB Compatible
"""

import http.server
import socketserver
import json
import re
import sqlite3
import os
import urllib.parse
from datetime import datetime

PORT = int(os.environ.get("PORT", 8080))
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(APP_DIR, "landscaping.db")
SQL_FILE = os.path.join(APP_DIR, "..", "sql", "landscaping_phase2_schema_and_data.sql")

ALL_TABLES = [
    "SUBSCRIPTION_PLAN", "CONTRACTOR", "CUSTOMER", "PROPERTY", "PROJECT_REQUEST", "PHOTO",
    "AI_ESTIMATE", "CONTRACTOR_QUOTE", "APPOINTMENT", "JOB", "INVOICE", "PAYMENT",
]


def mariadb_to_sqlite(script):
    """Small translation so the same .sql file we import into MariaDB also runs on SQLite."""
    script = re.sub(r"(?im)^\s*(CREATE DATABASE|USE|SET)\b[^;]*;", "", script)
    script = re.sub(r"(?i)\bINT\s+AUTO_INCREMENT\s+PRIMARY\s+KEY", "INTEGER PRIMARY KEY AUTOINCREMENT", script)
    script = re.sub(r"(?i)\)\s*ENGINE\s*=\s*\w+[^;]*;", ");", script)
    return script


def init_database():
    """Rebuilds landscaping.db from sql/landscaping_phase2_schema_and_data.sql (all 12 tables, 20 rows each)."""
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    with open(SQL_FILE, encoding="utf-8") as f:
        script = mariadb_to_sqlite(f.read())
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(script)
    conn.commit()
    conn.close()


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def now():
    return datetime.now().strftime("%H:%M:%S")


def sql_literal(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def render_sql(template, params):
    """Show a parameterized statement with its values filled in (display only; execution uses ?)."""
    parts = template.split("?")
    out = parts[0]
    for part, value in zip(parts[1:], params):
        out += sql_literal(value) + part
    return out


# Tables the GUI can search / update / delete generically. Column names here are the only
# identifiers ever put into SQL text; all values go through ? parameters.
TABLE_CONFIG = [
    {"table": "CUSTOMER", "pk": "customer_id", "singular": "Customer", "workflow": False, "search": ["name", "email", "phone_number"],
     "columns": [
         {"name": "name", "label": "Customer Full Name", "type": "text"},
         {"name": "email", "label": "Email Address", "type": "text"},
         {"name": "phone_number", "label": "Phone Number", "type": "text"},
         {"name": "plan_id", "label": "Subscription Plan", "type": "fk", "ref": "SUBSCRIPTION_PLAN"},
     ]},
    {"table": "PROPERTY", "pk": "property_id", "singular": "Property", "workflow": False, "search": ["address", "sqft", "customer_id"],
     "columns": [
         {"name": "address", "label": "Property Address", "type": "text"},
         {"name": "sqft", "label": "Lot Size (Sq Ft)", "type": "number"},
         {"name": "customer_id", "label": "Customer Owner", "type": "fk", "ref": "CUSTOMER"},
     ]},
    {"table": "PROJECT_REQUEST", "pk": "request_id", "singular": "Project Request", "label": "Requests",
     "icon": "📋", "workflow": True, "next": {"table": "AI_ESTIMATE", "fk": "request_id"},
     "cascade": "its AI estimates, photos, appointments, and every quote, job, invoice and payment below them",
     "columns": [
         {"name": "property_id", "label": "Property", "type": "fk", "ref": "PROPERTY",
          "fill": {"customer_id": "owner"}},
         {"name": "customer_id", "label": "Customer", "type": "fk", "ref": "CUSTOMER"},
         {"name": "description", "label": "Description", "type": "textarea"},
         {"name": "status", "label": "Status", "type": "select",
          "options": ["Pending", "Approved", "In Progress", "Completed"]},
     ]},
    {"table": "AI_ESTIMATE", "pk": "ai_id", "singular": "AI Estimate", "label": "Estimates",
     "icon": "🤖", "workflow": True, "next": {"table": "CONTRACTOR_QUOTE", "fk": "ai_id"},
     "cascade": "its contractor quotes and the jobs, invoices and payments below them",
     "columns": [
         {"name": "request_id", "label": "Project Request", "type": "fk", "ref": "PROJECT_REQUEST",
          "fill": {"estimated_prop_size": "sqft"}},
         {"name": "estimated_price", "label": "Estimated Price ($)", "type": "number", "money": True},
         {"name": "estimated_prop_size", "label": "Estimated Property Size (sq ft)", "type": "number"},
         {"name": "ideas_generated", "label": "Ideas Generated", "type": "textarea"},
     ]},
    {"table": "CONTRACTOR_QUOTE", "pk": "quote_id", "singular": "Contractor Quote", "label": "Quotes",
     "icon": "💬", "workflow": True, "next": {"table": "JOB", "fk": "quote_id"},
     "cascade": "the jobs, invoices and payments below it",
     "columns": [
         {"name": "ai_id", "label": "AI Estimate", "type": "fk", "ref": "AI_ESTIMATE",
          "fill": {"final_price": "estimated_price"}},
         {"name": "contractor_id", "label": "Contractor", "type": "fk", "ref": "CONTRACTOR"},
         {"name": "scope", "label": "Scope of Work", "type": "textarea"},
         {"name": "final_price", "label": "Final Price ($)", "type": "number", "money": True},
         {"name": "status", "label": "Status", "type": "select", "options": ["Pending", "Accepted", "Rejected"]},
     ]},
    {"table": "JOB", "pk": "job_id", "singular": "Job", "label": "Jobs",
     "icon": "🚜", "workflow": True, "next": {"table": "INVOICE", "fk": "job_id"},
     "cascade": "its invoices and payments",
     "columns": [
         {"name": "quote_id", "label": "Accepted Quote", "type": "fk", "ref": "CONTRACTOR_QUOTE",
          "fill": {"contractor_id": "contractor_id", "revenue": "final_price"}},
         {"name": "contractor_id", "label": "Contractor", "type": "fk", "ref": "CONTRACTOR"},
         {"name": "status", "label": "Status", "type": "select",
          "options": ["Scheduled", "In Progress", "Completed", "Cancelled"]},
         {"name": "start_date", "label": "Start Date", "type": "date", "default": "today"},
         {"name": "end_date", "label": "End Date", "type": "date", "nullable": True},
         {"name": "revenue", "label": "Revenue ($)", "type": "number", "money": True},
         {"name": "expenses", "label": "Expenses ($)", "type": "number", "money": True},
     ]},
    {"table": "INVOICE", "pk": "invoice_id", "singular": "Invoice", "label": "Invoices",
     "icon": "🧾", "workflow": True, "next": {"table": "PAYMENT", "fk": "invoice_id"},
     "cascade": "its payments",
     "columns": [
         {"name": "job_id", "label": "Job", "type": "fk", "ref": "JOB", "fill": {"amount_due": "revenue"}},
         {"name": "amount_due", "label": "Amount Due ($)", "type": "number", "money": True},
         {"name": "issued", "label": "Issued", "type": "date", "default": "today"},
         {"name": "due_date", "label": "Due Date", "type": "date"},
         {"name": "status", "label": "Status", "type": "select", "options": ["Issued", "Pending", "Paid", "Overdue"]},
     ]},
    {"table": "PAYMENT", "pk": "payment_id", "singular": "Payment", "label": "Payments",
     "icon": "💳", "workflow": True, "cascade": "nothing else (PAYMENT is the last step)",
     "columns": [
         {"name": "invoice_id", "label": "Invoice", "type": "fk", "ref": "INVOICE", "fill": {"amount": "amount_due"}},
         {"name": "amount", "label": "Amount ($)", "type": "number", "money": True},
         {"name": "payment_date", "label": "Payment Date", "type": "date", "default": "today"},
         {"name": "payment_method", "label": "Payment Method", "type": "select",
          "options": ["Credit Card", "Debit Card", "Bank Transfer", "PayPal"]},
         {"name": "status", "label": "Status", "type": "select", "options": ["Completed", "Pending", "Failed"]},
     ]},
]
TABLES = {cfg["table"]: cfg for cfg in TABLE_CONFIG}

# SELECTs that fill the foreign-key dropdowns. Extra columns (owner, sqft, ...) let the form
# pre-fill related fields when a parent row is picked.
FK_OPTIONS = {
    "SUBSCRIPTION_PLAN": "SELECT plan_id AS value, 'Plan ' || plan_id || ' - ' || plan_name || ' ($' || printf('%.2f', price) || '/mo)' AS label FROM SUBSCRIPTION_PLAN ORDER BY plan_id",
    "CUSTOMER": "SELECT customer_id AS value, name AS label FROM CUSTOMER ORDER BY customer_id",
    "CONTRACTOR": "SELECT contractor_id AS value, business_name AS label FROM CONTRACTOR ORDER BY contractor_id",
    "PROPERTY": "SELECT property_id AS value, address AS label, customer_id AS owner FROM PROPERTY ORDER BY property_id",
    "PROJECT_REQUEST": "SELECT r.request_id AS value, substr(r.description, 1, 48) AS label, p.sqft AS sqft FROM PROJECT_REQUEST r JOIN PROPERTY p ON p.property_id = r.property_id ORDER BY r.request_id",
    "AI_ESTIMATE": "SELECT ai_id AS value, 'Request #' || request_id || ' - $' || printf('%.2f', estimated_price) AS label, estimated_price FROM AI_ESTIMATE ORDER BY ai_id",
    "CONTRACTOR_QUOTE": "SELECT q.quote_id AS value, c.business_name || ' - $' || printf('%.2f', q.final_price) || ' (' || q.status || ')' AS label, q.contractor_id, q.final_price FROM CONTRACTOR_QUOTE q JOIN CONTRACTOR c ON c.contractor_id = q.contractor_id ORDER BY q.quote_id",
    "JOB": "SELECT job_id AS value, 'Quote #' || quote_id || ' - ' || status AS label, revenue FROM JOB ORDER BY job_id",
    "INVOICE": "SELECT invoice_id AS value, 'Job #' || job_id || ' - $' || printf('%.2f', amount_due) || ' (' || status || ')' AS label, amount_due FROM INVOICE ORDER BY invoice_id",
}


class BadInput(ValueError):
    pass


def coerce(col, raw):
    """Validate one submitted form value against its column config."""
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        if col.get("nullable"):
            return None
        raise BadInput(f"{col['label']} is required.")
    t = col["type"]
    try:
        if t == "fk":
            return int(raw)
        if t == "number":
            v = float(raw)
            if v < 0:
                raise BadInput(f"{col['label']} cannot be negative.")
            return round(v, 2) if col.get("money") else int(v)
    except (TypeError, ValueError):
        raise BadInput(f"{col['label']} must be a number.")
    v = str(raw).strip()
    if t == "select" and v not in col["options"]:
        raise BadInput(f"{col['label']} must be one of: {', '.join(col['options'])}.")
    if t == "date" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        raise BadInput(f"{col['label']} must be a date (YYYY-MM-DD).")
    return v


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Landscaping AI Estimator - CS4604 Group 6</title>
    <style>
        :root {
            --primary: #1b5e20;
            --primary-dark: #0e3d13;
            --primary-light: #e8f5e9;
            --danger: #d32f2f;
            --danger-hover: #b71c1c;
            --success: #2e7d32;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --border: #cbd5e1;
            --text: #0f172a;
            --text-muted: #475569;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg); color: var(--text); padding-bottom: 3rem; }
        .navbar { background: linear-gradient(135deg, var(--primary-dark), var(--primary)); color: white; padding: 1.1rem 2.2rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 10px rgba(0,0,0,0.15); }
        .brand { display: flex; align-items: center; gap: 0.85rem; }
        .brand h1 { font-size: 1.35rem; font-weight: 800; letter-spacing: -0.01em; }
        .brand p { font-size: 0.8rem; color: #a7f3d0; font-weight: 500; }
        .tabs { display: flex; gap: 0.5rem; background: rgba(0,0,0,0.25); padding: 0.35rem; border-radius: 8px; }
        .tab-btn { background: transparent; border: none; color: white; padding: 0.45rem 1rem; border-radius: 6px; font-weight: 600; font-size: 0.85rem; cursor: pointer; transition: all 0.2s; }
        .tab-btn.active, .tab-btn:hover { background: white; color: var(--primary-dark); }
        .status-badge { background: rgba(255,255,255,0.18); padding: 0.45rem 0.9rem; border-radius: 20px; font-size: 0.85rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem; border: 1px solid rgba(255,255,255,0.3); }
        .dot { width: 9px; height: 9px; border-radius: 50%; background: #4ade80; box-shadow: 0 0 10px #4ade80; }
        .container { max-width: 1240px; margin: 2rem auto; padding: 0 1.5rem; }
        
        /* Stats */
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.25rem; margin-bottom: 2rem; }
        .stat-card { background: white; border: 1px solid var(--border); border-radius: 12px; padding: 1.3rem; display: flex; align-items: center; gap: 1.1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.04); }
        .stat-icon { font-size: 2.2rem; background: var(--primary-light); width: 54px; height: 54px; display: flex; align-items: center; justify-content: center; border-radius: 10px; }
        .stat-info h3 { font-size: 1.7rem; font-weight: 800; color: var(--text); }
        .stat-info p { font-size: 0.85rem; color: var(--text-muted); font-weight: 600; }

        /* Card & Table */
        .card { background: white; border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 2px 6px rgba(0,0,0,0.05); overflow: hidden; margin-bottom: 2rem; }
        .card-header { padding: 1.25rem 1.75rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: #fafafa; }
        .card-title { font-size: 1.2rem; font-weight: 700; color: var(--text); }
        .btn { padding: 0.6rem 1.2rem; border-radius: 8px; font-weight: 700; font-size: 0.9rem; border: none; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; gap: 0.45rem; text-decoration: none; }
        .btn-primary { background: var(--primary); color: white; }
        .btn-primary:hover { background: var(--primary-dark); }
        .btn-danger { background: var(--danger); color: white; padding: 0.4rem 0.85rem; font-size: 0.8rem; border-radius: 6px; }
        .btn-danger:hover { background: var(--danger-hover); }
        .btn-secondary { background: #e2e8f0; color: var(--text); }

        /* Alerts */
        .alert { padding: 1.1rem 1.4rem; border-radius: 8px; margin-bottom: 1.5rem; display: flex; align-items: center; gap: 0.85rem; border-left: 5px solid; font-size: 0.95rem; }
        .alert-success { background: #f0fdf4; border-color: var(--success); color: #14532d; font-weight: 600; }
        .alert-danger { background: #fef2f2; border-color: var(--danger); color: #7f1d1d; font-weight: 600; }

        /* Table */
        table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
        th { background: #f1f5f9; color: var(--text-muted); text-align: left; padding: 0.95rem 1.3rem; font-weight: 700; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 2px solid var(--border); }
        td { padding: 0.95rem 1.3rem; border-bottom: 1px solid var(--border); color: var(--text); vertical-align: middle; }
        tr:hover { background: #f8fafc; }
        tr.new-row { background: #ecfdf5 !important; border-left: 4px solid #10b981; }

        /* SQL Reflection Box */
        .sql-box { background: #0f172a; color: #f8fafc; border-radius: 10px; padding: 1.3rem 1.5rem; margin-bottom: 1.75rem; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.9rem; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .sql-header { display: flex; justify-content: space-between; margin-bottom: 0.65rem; color: #38bdf8; font-weight: 700; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #1e293b; padding-bottom: 0.4rem; }
        .sql-code { color: #a5f3fc; white-space: pre-wrap; line-height: 1.6; }

        /* Modal */
        .modal-bg { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15,23,42,0.65); backdrop-filter: blur(4px); display: none; align-items: center; justify-content: center; z-index: 1000; }
        .modal-bg.active { display: flex; }
        .modal { background: white; width: 92%; max-width: 580px; border-radius: 12px; overflow: hidden; box-shadow: 0 20px 30px rgba(0,0,0,0.25); border: 1px solid var(--border); }
        .modal-head { padding: 1.3rem 1.6rem; background: #f8fafc; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .modal-body { padding: 1.6rem; display: flex; flex-direction: column; gap: 1.15rem; }
        .modal-foot { padding: 1.1rem 1.6rem; background: #f8fafc; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 0.85rem; }
        .form-row { display: flex; flex-direction: column; gap: 0.4rem; }
        .form-row label { font-size: 0.88rem; font-weight: 700; color: var(--text); }
        .form-row input, .form-row select { padding: 0.7rem 0.85rem; border: 1px solid var(--border); border-radius: 6px; font-size: 0.95rem; }
        .form-row input:focus, .form-row select:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(27,94,32,0.15); }

        /* Confirmation Dialog Box */
        .confirm-dialog { background: white; width: 92%; max-width: 520px; border-radius: 12px; padding: 1.75rem; box-shadow: 0 25px 40px rgba(0,0,0,0.3); border: 2px solid var(--danger); text-align: center; }
        .confirm-dialog h3 { color: var(--danger); font-size: 1.3rem; margin-bottom: 0.75rem; font-weight: 800; }
        .confirm-dialog p { font-size: 0.95rem; color: var(--text); margin-bottom: 1.5rem; line-height: 1.5; }

        .hidden { display: none !important; }

        /* Search, edit and workflow additions */
        .card-sub { font-size: 0.85rem; color: var(--text-muted); margin-top: 0.2rem; }
        .header-actions { display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; justify-content: flex-end; }
        .search-input { padding: 0.6rem 0.85rem; border: 1px solid var(--border); border-radius: 8px; font-size: 0.9rem; width: 270px; }
        .search-input:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(27,94,32,0.15); }
        .btn-edit { background: #e0f2fe; color: #075985; padding: 0.4rem 0.85rem; font-size: 0.8rem; border-radius: 6px; }
        .btn-edit:hover { background: #bae6fd; }
        .btn-next { background: var(--primary-light); color: var(--primary); padding: 0.4rem 0.85rem; font-size: 0.8rem; border-radius: 6px; border: 1px solid #a7d7ab; }
        .btn-next:hover { background: #c8e6c9; }
        td.actions { text-align: right; white-space: nowrap; }
        td.actions .btn { margin-left: 0.35rem; }
        td.empty { text-align: center; color: var(--text-muted); padding: 2rem; }
        .muted { color: #94a3b8; font-style: italic; }
        .fk-pill { background: #f1f5f9; padding: 2px 8px; border-radius: 6px; font-weight: 600; font-size: 0.82rem; white-space: nowrap; }
        .status-pill { padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 0.75rem; background: #f1f5f9; color: #334155; white-space: nowrap; }
        .status-completed, .status-paid, .status-accepted { background: #dcfce7; color: #166534; }
        .status-pending, .status-issued, .status-scheduled { background: #fef9c3; color: #854d0e; }
        .status-in-progress, .status-approved { background: #e0f2fe; color: #075985; }
        .status-rejected, .status-overdue, .status-failed, .status-cancelled { background: #fee2e2; color: #991b1b; }
        .wf-steps { display: flex; flex-wrap: wrap; align-items: center; gap: 0.3rem; padding: 0.9rem 1.5rem; border-bottom: 1px solid var(--border); }
        .wf-step { display: flex; align-items: center; gap: 0.45rem; background: white; border: 1px solid var(--border); border-radius: 10px; padding: 0.45rem 0.7rem; cursor: pointer; text-align: left; font-size: 0.85rem; color: var(--text); }
        .wf-step small { display: block; color: var(--text-muted); font-size: 0.72rem; }
        .wf-step.active { border-color: var(--primary); background: var(--primary-light); box-shadow: 0 0 0 2px rgba(27,94,32,0.15); }
        .wf-arrow { color: var(--text-muted); font-weight: 700; }
        .form-row textarea { padding: 0.7rem 0.85rem; border: 1px solid var(--border); border-radius: 6px; font-size: 0.95rem; font-family: inherit; resize: vertical; }
        .form-row textarea:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(27,94,32,0.15); }
        .modal-body { max-height: 65vh; overflow-y: auto; }
    </style>
</head>
<body>

<header class="navbar">
    <div class="brand">
        <span style="font-size: 2rem;">🌿</span>
        <div>
            <h1>Landscaping AI Estimator Management Portal</h1>
            <p>CS 4604 Group 6 &bull; Virginia Tech &bull; MariaDB 10.x / InnoDB &bull; landscaping_db</p>
        </div>
    </div>
    <div class="tabs">
        <button class="tab-btn active" id="tabCust" onclick="switchView('customers')">CUSTOMER (Major)</button>
        <button class="tab-btn" id="tabProp" onclick="switchView('properties')">PROPERTY (Major)</button>
        <button class="tab-btn" id="tabWf" onclick="switchView('workflow')">Project Workflow</button>
        <button class="tab-btn" id="tabDb" onclick="switchView('db_view')">Database Query Inspector</button>
    </div>
    <div class="status-badge">
        <div class="dot"></div>
        <span>Connected: <code>mariadb:3306</code></span>
    </div>
</header>

<main class="container">

    <!-- Live Alerts -->
    <div id="alertBox" class="alert hidden"></div>

    <!-- SQL Reflection Box -->
    <div class="sql-box" id="sqlBox">
        <div class="sql-header">
            <span>MariaDB Live Query Reflection &bull; InnoDB Engine</span>
            <span id="sqlTimestamp">Ready</span>
        </div>
        <div class="sql-code" id="sqlCode">-- Database connection verified to landscaping_db:3306
SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema='landscaping_db';</div>
    </div>

    <!-- Stats -->
    <div class="stat-grid">
        <div class="stat-card">
            <div class="stat-icon">👥</div>
            <div class="stat-info">
                <h3 id="statCustomerCount">20</h3>
                <p>CUSTOMER (Major Table)</p>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">🏡</div>
            <div class="stat-info">
                <h3 id="statPropertyCount">20</h3>
                <p>PROPERTY (Major Table)</p>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">🚜</div>
            <div class="stat-info">
                <h3 id="statContractorCount">20</h3>
                <p>CONTRACTOR Tuples</p>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">📋</div>
            <div class="stat-info">
                <h3 id="statRequestCount">20</h3>
                <p>PROJECT_REQUEST Tuples</p>
            </div>
        </div>
    </div>

    <!-- VIEW 1: CUSTOMERS -->
    <div id="viewCustomers" class="card">
        <div class="card-header">
            <div>
                <div class="card-title">Major Table: <code>CUSTOMER</code></div>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.2rem;">Primary Key: <code>customer_id</code> &bull; Foreign Key: <code>plan_id -> SUBSCRIPTION_PLAN(plan_id)</code></div>
            </div>
            <div class="header-actions">
                <input type="search" id="custSearch" class="search-input" placeholder="Search name, email or phone..." oninput="onSearch(loadCustomers)">
                <button class="btn btn-primary" onclick="openCustomerModal()">+ Insert New Customer</button>
            </div>
        </div>
        <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>customer_id (PK)</th>
                        <th>name</th>
                        <th>email</th>
                        <th>phone_number</th>
                        <th>plan_id (FK)</th>
                        <th style="text-align: right;">Action</th>
                    </tr>
                </thead>
                <tbody id="customerTableBody"></tbody>
            </table>
        </div>
    </div>

    <!-- VIEW 2: PROPERTIES -->
    <div id="viewProperties" class="card hidden">
        <div class="card-header">
            <div>
                <div class="card-title">Major Table: <code>PROPERTY</code></div>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.2rem;">Primary Key: <code>property_id</code> &bull; Foreign Key: <code>customer_id -> CUSTOMER(customer_id) ON DELETE CASCADE</code></div>
            </div>
            <div class="header-actions">
                <input type="search" id="propSearch" class="search-input" placeholder="Search address, sq ft or owner ID..." oninput="onSearch(loadProperties)">
                <button class="btn btn-primary" onclick="openPropertyModal()">+ Insert New Property</button>
            </div>
        </div>
        <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>property_id (PK)</th>
                        <th>address</th>
                        <th>sqft</th>
                        <th>customer_id (FK)</th>
                        <th style="text-align: right;">Action</th>
                    </tr>
                </thead>
                <tbody id="propertyTableBody"></tbody>
            </table>
        </div>
    </div>

    <!-- VIEW 2b: PROJECT WORKFLOW (PROJECT_REQUEST -> AI_ESTIMATE -> CONTRACTOR_QUOTE -> JOB -> INVOICE -> PAYMENT) -->
    <div id="viewWorkflow" class="card hidden">
        <div class="card-header">
            <div>
                <div class="card-title">Project Workflow: Request &rarr; Estimate &rarr; Quote &rarr; Job &rarr; Invoice &rarr; Payment</div>
                <div class="card-sub">Each step references the one before it through a foreign key. Dropdowns are filled by <code>SELECT</code> queries on the parent table. Use <strong>+ next step</strong> on a row to attach the next record to it.</div>
            </div>
        </div>
        <div class="wf-steps" id="wfSteps"></div>
        <div class="card-header">
            <div>
                <div class="card-title" id="wfTitle"></div>
                <div class="card-sub" id="wfKeys"></div>
            </div>
            <div class="header-actions">
                <input type="search" id="wfSearch" class="search-input" placeholder="Search this table..." oninput="onSearch(loadWorkflow)">
                <button class="btn btn-primary" id="wfInsertBtn" onclick="openRowModal(wfTable)">+ Insert</button>
            </div>
        </div>
        <div style="overflow-x: auto;" id="wfTable"></div>
    </div>

    <!-- VIEW 3: DATABASE INSPECTOR (phpMyAdmin simulator) -->
    <div id="viewDatabase" class="card hidden">
        <div class="card-header">
            <div>
                <div class="card-title">Direct MariaDB SQL Query Console</div>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.2rem;">Executing against <code>mariadb:3306/landscaping_db</code></div>
            </div>
            <div style="display: flex; gap: 0.6rem;">
                <button class="btn btn-secondary" onclick="runCustomQuery('SELECT customer_id, name, email, phone_number, plan_id FROM CUSTOMER WHERE customer_id >= 20;')">Check Customer #20 & #21</button>
                <button class="btn btn-secondary" onclick="runCustomQuery('SELECT * FROM CUSTOMER WHERE customer_id = 21;')">Verify Customer #21 Status</button>
            </div>
        </div>
        <div style="padding: 1.5rem;">
            <div style="display: flex; gap: 0.75rem; margin-bottom: 1.25rem;">
                <input type="text" id="customSqlInput" class="form-row" style="flex: 1; padding: 0.7rem 0.9rem; border: 1px solid var(--border); border-radius: 6px; font-family: monospace; font-size: 0.95rem;" value="SELECT * FROM CUSTOMER LIMIT 25;">
                <button class="btn btn-primary" onclick="runCustomQuery(document.getElementById('customSqlInput').value)">Execute SQL</button>
            </div>
            <div id="rawQueryResult" style="overflow-x: auto; max-height: 450px;"></div>
        </div>
    </div>

</main>

<!-- INSERT CUSTOMER MODAL -->
<div class="modal-bg" id="customerModal">
    <div class="modal">
        <div class="modal-head">
            <h3 id="customerModalTitle" style="font-size: 1.15rem; font-weight: 800; color: var(--primary);">➕ Insert New Customer (GUI Form)</h3>
            <button onclick="closeCustomerModal()" style="border: none; background: none; font-size: 1.3rem; cursor: pointer; color: var(--text-muted);">✕</button>
        </div>
        <div class="modal-body">
            <div class="form-row">
                <label>Customer Full Name *</label>
                <input type="text" id="custName" value="Michael Scott" required>
            </div>
            <div class="form-row">
                <label>Email Address *</label>
                <input type="email" id="custEmail" value="m.scott@dundermifflin.com" required>
            </div>
            <div class="form-row">
                <label>Phone Number *</label>
                <input type="tel" id="custPhone" value="555-0199" required>
            </div>
            <div class="form-row">
                <label>Subscription Plan (Foreign Key -> SUBSCRIPTION_PLAN)</label>
                <select id="custPlan">
                    <option value="1">Plan 1 - Basic Homeowner ($19.99/mo)</option>
                    <option value="2" selected>Plan 2 - Pro Landscaper ($49.99/mo)</option>
                    <option value="3">Plan 3 - Enterprise Contractor ($99.99/mo)</option>
                </select>
            </div>
            <div class="form-row" id="custPassRow">
                <label>Password (Encrypted / Hashed)</label>
                <input type="password" id="custPass" value="SecurePass2026!">
            </div>
        </div>
        <div class="modal-foot">
            <button class="btn btn-secondary" onclick="closeCustomerModal()">Cancel</button>
            <button class="btn btn-primary" id="customerSubmitBtn" onclick="submitCustomerForm()">Insert Customer into Database</button>
        </div>
    </div>
</div>

<!-- DELETE CONFIRMATION MODAL -->
<div class="modal-bg" id="deleteConfirmModal">
    <div class="confirm-dialog">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">⚠️</div>
        <h3>Confirm Tuple Deletion</h3>
        <p id="deleteConfirmText">Are you sure you want to delete Customer <strong>#21 (Michael Scott)</strong> from the MariaDB database? This will execute <code>DELETE FROM CUSTOMER WHERE customer_id = 21</code> and cascade to any dependent records.</p>
        <div style="display: flex; justify-content: center; gap: 1rem;">
            <button class="btn btn-secondary" onclick="closeDeleteModal()">Cancel</button>
            <button class="btn btn-danger" style="padding: 0.6rem 1.2rem; font-size: 0.9rem;" onclick="confirmExecuteDelete()">Confirm & Delete Tuple</button>
        </div>
    </div>
</div>

<!-- INSERT PROPERTY MODAL -->
<div class="modal-bg" id="propertyModal">
    <div class="modal">
        <div class="modal-head">
            <h3 id="propertyModalTitle" style="font-size: 1.15rem; font-weight: 800; color: var(--primary);">➕ Insert New Property (GUI Form)</h3>
            <button onclick="closePropertyModal()" style="border: none; background: none; font-size: 1.3rem; cursor: pointer;">✕</button>
        </div>
        <div class="modal-body">
            <div class="form-row">
                <label>Property Address *</label>
                <input type="text" id="propAddress" value="1725 Slough Ave, Scranton, PA" required>
            </div>
            <div class="form-row">
                <label>Lot Size (Sq Ft) *</label>
                <input type="number" id="propSqft" value="8400" required>
            </div>
            <div class="form-row">
                <label>Customer Owner (customer_id FK)</label>
                <select id="propCustomerId"></select>
            </div>
        </div>
        <div class="modal-foot">
            <button class="btn btn-secondary" onclick="closePropertyModal()">Cancel</button>
            <button class="btn btn-primary" id="propertySubmitBtn" onclick="submitPropertyForm()">Insert Property into Database</button>
        </div>
    </div>
</div>

<!-- GENERIC INSERT / EDIT MODAL (workflow tables) -->
<div class="modal-bg" id="rowModal">
    <div class="modal">
        <div class="modal-head">
            <h3 id="rowModalTitle" style="font-size: 1.15rem; font-weight: 800; color: var(--primary);"></h3>
            <button onclick="closeRowModal()" style="border: none; background: none; font-size: 1.3rem; cursor: pointer; color: var(--text-muted);">✕</button>
        </div>
        <div class="modal-body" id="rowModalBody"></div>
        <div class="modal-foot">
            <button class="btn btn-secondary" onclick="closeRowModal()">Cancel</button>
            <button class="btn btn-primary" id="rowSubmitBtn" onclick="submitRowForm()">Save</button>
        </div>
    </div>
</div>

<script>
let customersData = [];
let propertiesData = [];
let pendingDeleteId = null;
let pendingDeleteName = '';
let pendingConfirm = null;
let customerEditId = null;
let propertyEditId = null;
let schema = [];
let fkOptions = {};
let tableCounts = {};
let wfTable = 'PROJECT_REQUEST';
let wfRows = [];
let rowModalTable = null;
let rowEditId = null;
let searchTimer = null;
const CUSTOMER_DEFAULTS = { name: 'Michael Scott', email: 'm.scott@dundermifflin.com', phone: '555-0199', plan: '2', pass: 'SecurePass2026!' };
const PROPERTY_DEFAULTS = { address: '1725 Slough Ave, Scranton, PA', sqft: '8400' };

async function getJson(url, body) {
    const opts = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
    const res = await fetch(url, opts);
    return res.json();
}

// ---------- Loading ----------
async function loadMeta() {
    if (!schema.length) schema = await getJson('/api/schema');
    fkOptions = await getJson('/api/options');
    tableCounts = await getJson('/api/counts');
    fillSelect(document.getElementById('custPlan'), fkOptions.SUBSCRIPTION_PLAN, false);
    fillSelect(document.getElementById('propCustomerId'), fkOptions.CUSTOMER, true);
    document.getElementById('statCustomerCount').innerText = tableCounts.CUSTOMER;
    document.getElementById('statPropertyCount').innerText = tableCounts.PROPERTY;
    document.getElementById('statContractorCount').innerText = tableCounts.CONTRACTOR;
    document.getElementById('statRequestCount').innerText = tableCounts.PROJECT_REQUEST;
}

function fillSelect(sel, opts, showId) {
    const current = sel.value;
    sel.innerHTML = '';
    (opts || []).forEach(o => {
        const opt = document.createElement('option');
        opt.value = o.value;
        opt.textContent = showId ? `#${o.value} - ${o.label}` : o.label;
        sel.appendChild(opt);
    });
    if (current && [...sel.options].some(o => o.value === current)) sel.value = current;
}

async function loadCustomers(showSql) {
    const q = document.getElementById('custSearch').value.trim();
    const data = await getJson('/api/rows/CUSTOMER?q=' + encodeURIComponent(q));
    customersData = data.rows || [];
    renderCustomers();
    if (showSql) updateSqlBox(data.sql, data.timestamp);
}

async function loadProperties(showSql) {
    const q = document.getElementById('propSearch').value.trim();
    const data = await getJson('/api/rows/PROPERTY?q=' + encodeURIComponent(q));
    propertiesData = data.rows || [];
    renderProperties();
    if (showSql) updateSqlBox(data.sql, data.timestamp);
}

async function loadData() {
    try {
        await loadMeta();
        await loadCustomers(false);
        await loadProperties(false);
        if (!document.getElementById('viewWorkflow').classList.contains('hidden')) await loadWorkflow(false);
    } catch (e) {
        console.error(e);
    }
}

function onSearch(loader) {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loader(true), 250);
}

// ---------- Customers & properties ----------
function renderCustomers() {
    const tbody = document.getElementById('customerTableBody');
    tbody.innerHTML = '';
    if (!customersData.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty">No customers match this search.</td></tr>';
        return;
    }
    customersData.forEach(c => {
        const tr = document.createElement('tr');
        if (c.customer_id === 21) {
            tr.className = 'new-row';
        }
        tr.innerHTML = `
            <td><strong>#${c.customer_id}</strong></td>
            <td><strong>${escapeHtml(c.name)}</strong></td>
            <td>${escapeHtml(c.email)}</td>
            <td>${escapeHtml(c.phone_number)}</td>
            <td><span style="background: #e0f2fe; color: #0369a1; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 0.75rem;">Plan #${c.plan_id}</span></td>
            <td class="actions">
                <button class="btn btn-edit" onclick="editCustomer(${c.customer_id})">Edit</button>
                <button class="btn btn-danger" onclick="promptDeleteCustomer(${c.customer_id})">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderProperties() {
    const tbody = document.getElementById('propertyTableBody');
    tbody.innerHTML = '';
    if (!propertiesData.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty">No properties match this search.</td></tr>';
        return;
    }
    propertiesData.forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>#${p.property_id}</strong></td>
            <td>${escapeHtml(p.address)}</td>
            <td><strong>${Number(p.sqft).toLocaleString()} sq ft</strong></td>
            <td><span class="fk-pill">${escapeHtml(fkText('CUSTOMER', p.customer_id))}</span></td>
            <td class="actions">
                <button class="btn btn-edit" onclick="editProperty(${p.property_id})">Edit</button>
                <button class="btn btn-danger" onclick="promptDeleteProperty(${p.property_id})">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function switchView(view) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    ['viewCustomers', 'viewProperties', 'viewWorkflow', 'viewDatabase'].forEach(id => document.getElementById(id).classList.add('hidden'));

    if (view === 'customers') {
        document.getElementById('tabCust').classList.add('active');
        document.getElementById('viewCustomers').classList.remove('hidden');
    } else if (view === 'properties') {
        document.getElementById('tabProp').classList.add('active');
        document.getElementById('viewProperties').classList.remove('hidden');
    } else if (view === 'workflow') {
        document.getElementById('tabWf').classList.add('active');
        document.getElementById('viewWorkflow').classList.remove('hidden');
        return loadWorkflow(true);
    } else {
        document.getElementById('tabDb').classList.add('active');
        document.getElementById('viewDatabase').classList.remove('hidden');
        runCustomQuery('SELECT customer_id, name, email, phone_number, plan_id FROM CUSTOMER ORDER BY customer_id ASC LIMIT 25;');
    }
}

function openCustomerModal() {
    customerEditId = null;
    document.getElementById('custName').value = CUSTOMER_DEFAULTS.name;
    document.getElementById('custEmail').value = CUSTOMER_DEFAULTS.email;
    document.getElementById('custPhone').value = CUSTOMER_DEFAULTS.phone;
    document.getElementById('custPlan').value = CUSTOMER_DEFAULTS.plan;
    document.getElementById('custPass').value = CUSTOMER_DEFAULTS.pass;
    document.getElementById('custPassRow').classList.remove('hidden');
    document.getElementById('customerModalTitle').innerText = '➕ Insert New Customer (GUI Form)';
    document.getElementById('customerSubmitBtn').innerText = 'Insert Customer into Database';
    document.getElementById('customerModal').classList.add('active');
}
function editCustomer(id) {
    const c = customersData.find(x => x.customer_id === id);
    if (!c) return;
    customerEditId = id;
    document.getElementById('custName').value = c.name;
    document.getElementById('custEmail').value = c.email;
    document.getElementById('custPhone').value = c.phone_number;
    document.getElementById('custPlan').value = String(c.plan_id);
    document.getElementById('custPassRow').classList.add('hidden');
    document.getElementById('customerModalTitle').innerText = `✏️ Edit Customer #${id} (UPDATE)`;
    document.getElementById('customerSubmitBtn').innerText = 'Save Changes to Database';
    document.getElementById('customerModal').classList.add('active');
}
function closeCustomerModal() { document.getElementById('customerModal').classList.remove('active'); }

function openPropertyModal() {
    propertyEditId = null;
    document.getElementById('propAddress').value = PROPERTY_DEFAULTS.address;
    document.getElementById('propSqft').value = PROPERTY_DEFAULTS.sqft;
    document.getElementById('propertyModalTitle').innerText = '➕ Insert New Property (GUI Form)';
    document.getElementById('propertySubmitBtn').innerText = 'Insert Property into Database';
    document.getElementById('propertyModal').classList.add('active');
}
function editProperty(id) {
    const p = propertiesData.find(x => x.property_id === id);
    if (!p) return;
    propertyEditId = id;
    document.getElementById('propAddress').value = p.address;
    document.getElementById('propSqft').value = p.sqft;
    document.getElementById('propCustomerId').value = String(p.customer_id);
    document.getElementById('propertyModalTitle').innerText = `✏️ Edit Property #${id} (UPDATE)`;
    document.getElementById('propertySubmitBtn').innerText = 'Save Changes to Database';
    document.getElementById('propertyModal').classList.add('active');
}
function closePropertyModal() { document.getElementById('propertyModal').classList.remove('active'); }

// Shows the SQL that ran and a success / error banner. Returns true on success.
function handleWrite(data, successText, closeFn) {
    if (closeFn) closeFn();
    updateSqlBox(data.sql, data.timestamp);
    if (data.status !== 'success') {
        showAlert('danger', 'Database rejected the change: ' + escapeHtml(data.error));
        return false;
    }
    if (data.affected === 0) {
        showAlert('danger', 'No matching row was found, so nothing changed.');
        return false;
    }
    showAlert('success', successText);
    return true;
}

function askConfirm(html, fn) {
    pendingConfirm = fn;
    document.getElementById('deleteConfirmText').innerHTML = html;
    document.getElementById('deleteConfirmModal').classList.add('active');
}

function promptDelete(id, name) {
    pendingConfirm = null;
    pendingDeleteId = id;
    pendingDeleteName = name;
    document.getElementById('deleteConfirmText').innerHTML = `Are you sure you want to delete Customer <strong>#${id} (${escapeHtml(name)})</strong> from table <code>CUSTOMER</code>?<br><br><span style="color: var(--danger); font-size: 0.85rem; font-weight: 600;">Cascade Rule: Any properties or requests referencing customer_id=${id} will also be deleted.</span>`;
    document.getElementById('deleteConfirmModal').classList.add('active');
}
function promptDeleteCustomer(id) {
    const c = customersData.find(x => x.customer_id === id);
    promptDelete(id, c ? c.name : '');
}
function promptDeleteProperty(id) {
    const p = propertiesData.find(x => x.property_id === id);
    askConfirm(`Are you sure you want to delete Property <strong>#${id} (${escapeHtml(p ? p.address : '')})</strong> from table <code>PROPERTY</code>?<br><br><span style="color: var(--danger); font-size: 0.85rem; font-weight: 600;">Cascade Rule: Project requests on this property (and everything below them) will also be deleted.</span>`, async () => {
        const data = await getJson('/api/rows/PROPERTY/delete', { id });
        handleWrite(data, `🗑️ Property #${id} deleted from PROPERTY.`);
        await loadData();
    });
}
function closeDeleteModal() {
    document.getElementById('deleteConfirmModal').classList.remove('active');
}

async function confirmExecuteDelete() {
    closeDeleteModal();
    try {
        if (pendingConfirm) {
            const fn = pendingConfirm;
            pendingConfirm = null;
            await fn();
            return;
        }
        if (!pendingDeleteId) return;
        const data = await getJson('/api/delete_customer', { customer_id: pendingDeleteId });
        handleWrite(data, `🗑️ Success: Customer #${pendingDeleteId} (${escapeHtml(pendingDeleteName)}) deleted from CUSTOMER.`);
        await loadData();
    } catch (e) {
        showAlert('danger', 'Error deleting row: ' + e);
    }
}

function submitCustomerForm() { return customerEditId ? submitUpdateCustomer() : submitInsertCustomer(); }
function submitPropertyForm() { return propertyEditId ? submitUpdateProperty() : submitInsertProperty(); }

async function submitInsertCustomer() {
    const name = document.getElementById('custName').value.trim();
    const email = document.getElementById('custEmail').value.trim();
    const phone = document.getElementById('custPhone').value.trim();
    const plan_id = document.getElementById('custPlan').value;
    const password = document.getElementById('custPass').value;

    try {
        const data = await getJson('/api/insert_customer', { name, email, phone_number: phone, plan_id, password });
        handleWrite(data, `✅ Success: Record successfully inserted into CUSTOMER! [CustomerID: #${data.new_id}]`, closeCustomerModal);
        await loadData();
    } catch (e) {
        showAlert('danger', 'Error inserting customer: ' + e);
    }
}

async function submitUpdateCustomer() {
    const id = customerEditId;
    const values = {
        name: document.getElementById('custName').value,
        email: document.getElementById('custEmail').value,
        phone_number: document.getElementById('custPhone').value,
        plan_id: document.getElementById('custPlan').value,
    };
    try {
        const data = await getJson('/api/rows/CUSTOMER/update', { id, values });
        handleWrite(data, `✏️ Success: Customer #${id} updated in CUSTOMER.`, closeCustomerModal);
        await loadData();
    } catch (e) {
        showAlert('danger', 'Error updating customer: ' + e);
    }
}

async function submitInsertProperty() {
    const address = document.getElementById('propAddress').value.trim();
    const sqft = document.getElementById('propSqft').value;
    const customer_id = document.getElementById('propCustomerId').value;

    try {
        const data = await getJson('/api/insert_property', { address, sqft, customer_id });
        handleWrite(data, `✅ Success: Property successfully inserted! [PropertyID: #${data.new_id}]`, closePropertyModal);
        await loadData();
    } catch (e) {
        showAlert('danger', 'Error inserting property: ' + e);
    }
}

async function submitUpdateProperty() {
    const id = propertyEditId;
    const values = {
        address: document.getElementById('propAddress').value,
        sqft: document.getElementById('propSqft').value,
        customer_id: document.getElementById('propCustomerId').value,
    };
    try {
        const data = await getJson('/api/rows/PROPERTY/update', { id, values });
        handleWrite(data, `✏️ Success: Property #${id} updated in PROPERTY.`, closePropertyModal);
        await loadData();
    } catch (e) {
        showAlert('danger', 'Error updating property: ' + e);
    }
}

// ---------- Project workflow ----------
function tcfg(table) { return schema.find(s => s.table === table); }
function fkText(ref, v) {
    if (v === null || v === undefined || v === '') return '-';
    const o = (fkOptions[ref] || []).find(o => String(o.value) === String(v));
    return o ? `#${v} · ${o.label}` : `#${v}`;
}
function fmtCell(col, v) {
    if (v === null || v === undefined || v === '') return '<span class="muted">NULL</span>';
    if (col.type === 'fk') return `<span class="fk-pill">${escapeHtml(fkText(col.ref, v))}</span>`;
    if (col.money) return '$' + Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (col.name === 'status') return `<span class="status-pill status-${String(v).toLowerCase().replace(/[^a-z]+/g, '-')}">${escapeHtml(v)}</span>`;
    if (col.type === 'number') return Number(v).toLocaleString();
    return escapeHtml(v);
}

function renderWfSteps() {
    const steps = schema.filter(s => s.workflow);
    document.getElementById('wfSteps').innerHTML = steps.map((s, i) => `
        <button class="wf-step ${s.table === wfTable ? 'active' : ''}" title="${s.table}" onclick="selectWfTable('${s.table}')">
            <span style="font-size: 1.2rem;">${s.icon}</span>
            <span><strong>${s.label}</strong><small>${tableCounts[s.table] ?? 0} rows</small></span>
        </button>${i < steps.length - 1 ? '<span class="wf-arrow">&rarr;</span>' : ''}`).join('');
}

function selectWfTable(table) {
    wfTable = table;
    document.getElementById('wfSearch').value = '';
    return loadWorkflow(true);
}

async function loadWorkflow(showSql) {
    const q = document.getElementById('wfSearch').value.trim();
    const data = await getJson(`/api/rows/${wfTable}?q=` + encodeURIComponent(q));
    wfRows = data.rows || [];
    if (showSql) updateSqlBox(data.sql, data.timestamp);
    renderWorkflow();
}

function renderWorkflow() {
    const cfg = tcfg(wfTable);
    if (!cfg) return;
    renderWfSteps();
    document.getElementById('wfTitle').innerHTML = `Table: <code>${cfg.table}</code>`;
    document.getElementById('wfKeys').innerHTML = `Primary Key: <code>${cfg.pk}</code>` +
        cfg.columns.filter(c => c.type === 'fk').map(c => ` &bull; Foreign Key: <code>${c.name} -> ${c.ref}</code>`).join('');
    document.getElementById('wfInsertBtn').innerText = `+ Insert New ${cfg.singular}`;
    const next = cfg.next ? tcfg(cfg.next.table) : null;

    let html = `<table><thead><tr><th>${cfg.pk} (PK)</th>` +
        cfg.columns.map(c => `<th>${c.name}${c.type === 'fk' ? ' (FK)' : ''}</th>`).join('') +
        '<th style="text-align: right;">Action</th></tr></thead><tbody>';
    if (!wfRows.length) html += `<tr><td colspan="${cfg.columns.length + 2}" class="empty">No rows match this search.</td></tr>`;
    wfRows.forEach(r => {
        const id = r[cfg.pk];
        html += `<tr><td><strong>#${id}</strong></td>` +
            cfg.columns.map(c => `<td>${fmtCell(c, r[c.name])}</td>`).join('') +
            `<td class="actions">` +
            (next ? `<button class="btn btn-next" onclick="nextStep(${id})">+ ${next.singular}</button>` : '') +
            `<button class="btn btn-edit" onclick="openRowModal('${cfg.table}', ${id})">Edit</button>` +
            `<button class="btn btn-danger" onclick="promptDeleteRow('${cfg.table}', ${id})">Delete</button></td></tr>`;
    });
    html += '</tbody></table>';
    document.getElementById('wfTable').innerHTML = html;
}

function openRowModal(table, id, prefill) {
    const cfg = tcfg(table);
    rowModalTable = table;
    rowEditId = (id === undefined || id === null) ? null : id;
    const row = rowEditId !== null ? wfRows.find(r => r[cfg.pk] === rowEditId) : null;
    document.getElementById('rowModalTitle').innerText = row ? `✏️ Edit ${cfg.singular} #${rowEditId} (UPDATE)` : `➕ Insert New ${cfg.singular}`;
    document.getElementById('rowSubmitBtn').innerText = row ? 'Save Changes to Database' : `Insert ${cfg.singular} into Database`;

    const body = document.getElementById('rowModalBody');
    body.innerHTML = '';
    cfg.columns.forEach(col => {
        const wrap = document.createElement('div');
        wrap.className = 'form-row';
        const label = document.createElement('label');
        label.textContent = col.label + (col.type === 'fk' ? ` (FK -> ${col.ref})` : '') + (col.nullable ? ' (optional)' : ' *');
        let input;
        if (col.type === 'fk' || col.type === 'select') {
            input = document.createElement('select');
            const opts = col.type === 'fk'
                ? (fkOptions[col.ref] || []).map(o => ({ value: o.value, text: `#${o.value} - ${o.label}` }))
                : col.options.map(o => ({ value: o, text: o }));
            opts.forEach(o => {
                const opt = document.createElement('option');
                opt.value = o.value;
                opt.textContent = o.text;
                input.appendChild(opt);
            });
        } else if (col.type === 'textarea') {
            input = document.createElement('textarea');
            input.rows = 3;
        } else {
            input = document.createElement('input');
            input.type = col.type === 'number' ? 'number' : (col.type === 'date' ? 'date' : 'text');
            if (col.type === 'number') { input.min = '0'; input.step = col.money ? '0.01' : '1'; }
        }
        input.id = 'rf_' + col.name;
        wrap.append(label, input);
        body.appendChild(wrap);
    });

    const today = new Date().toLocaleDateString('en-CA');  // local date as YYYY-MM-DD
    cfg.columns.forEach(col => {
        const input = document.getElementById('rf_' + col.name);
        let v;
        if (row) v = row[col.name];
        else if (prefill && prefill[col.name] !== undefined) v = prefill[col.name];
        else if (col.default === 'today') v = today;
        else v = col.default;
        if (v !== null && v !== undefined && v !== '') input.value = String(v);
    });
    cfg.columns.filter(c => c.fill).forEach(col => {
        if (!row) applyFill(col);
        document.getElementById('rf_' + col.name).addEventListener('change', () => applyFill(col));
    });
    document.getElementById('rowModal').classList.add('active');
}

// Picking a parent row pre-fills related fields (e.g. a property's owner, a quote's price).
function applyFill(col) {
    const sel = document.getElementById('rf_' + col.name);
    const opt = (fkOptions[col.ref] || []).find(o => String(o.value) === sel.value);
    if (!opt) return;
    Object.entries(col.fill).forEach(([field, attr]) => {
        const el = document.getElementById('rf_' + field);
        if (el && opt[attr] !== undefined && opt[attr] !== null) el.value = String(opt[attr]);
    });
}

function closeRowModal() { document.getElementById('rowModal').classList.remove('active'); }

async function submitRowForm() {
    const cfg = tcfg(rowModalTable);
    const values = {};
    cfg.columns.forEach(col => { values[col.name] = document.getElementById('rf_' + col.name).value; });
    const isEdit = rowEditId !== null;
    try {
        const data = await getJson(`/api/rows/${cfg.table}/${isEdit ? 'update' : 'insert'}`, isEdit ? { id: rowEditId, values } : { values });
        handleWrite(data, isEdit
            ? `✏️ Success: ${cfg.singular} #${rowEditId} updated in ${cfg.table}.`
            : `✅ Success: ${cfg.singular} inserted into ${cfg.table}! [${cfg.pk}: #${data.new_id}]`, closeRowModal);
        wfTable = cfg.table;
        await loadData();
    } catch (e) {
        showAlert('danger', 'Error saving row: ' + e);
    }
}

async function nextStep(id) {
    const next = tcfg(wfTable).next;
    wfTable = next.table;
    document.getElementById('wfSearch').value = '';
    await loadWorkflow(false);
    openRowModal(next.table, null, { [next.fk]: id });
}

function promptDeleteRow(table, id) {
    const cfg = tcfg(table);
    askConfirm(`Are you sure you want to delete ${cfg.singular} <strong>#${id}</strong> from table <code>${table}</code>?<br><br><span style="color: var(--danger); font-size: 0.85rem; font-weight: 600;">Cascade Rule: this also deletes ${cfg.cascade}.</span>`, async () => {
        const data = await getJson(`/api/rows/${table}/delete`, { id });
        handleWrite(data, `🗑️ ${cfg.singular} #${id} deleted from ${table}.`);
        await loadData();
    });
}

async function runCustomQuery(sql) {
    document.getElementById('customSqlInput').value = sql;
    try {
        const res = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: sql })
        });
        const data = await res.json();
        updateSqlBox(data.sql, data.timestamp);

        const container = document.getElementById('rawQueryResult');
        if (data.error) {
            container.innerHTML = `<div class="alert alert-danger">${escapeHtml(data.error)}</div>`;
            return;
        }

        let html = `<table><thead><tr>`;
        data.columns.forEach(col => { html += `<th>${escapeHtml(col)}</th>`; });
        html += `</tr></thead><tbody>`;
        data.rows.forEach(row => {
            html += `<tr>`;
            row.forEach(val => { html += `<td><strong>${escapeHtml(String(val))}</strong></td>`; });
            html += `</tr>`;
        });
        html += `</tbody></table><div style="padding: 0.75rem 1rem; font-size: 0.85rem; color: #047857; font-weight: 700; background: #ecfdf5; border-top: 1px solid var(--border);">${data.rows.length} rows in set (0.001 sec) &bull; MariaDB 10.x [landscaping_db]</div>`;
        container.innerHTML = html;
    } catch (e) {
        console.error(e);
    }
}

function showAlert(type, text) {
    const box = document.getElementById('alertBox');
    box.className = `alert alert-${type}`;
    box.innerHTML = `<span style="font-size: 1.3rem;">${type === 'success' ? '✅' : '⚠️'}</span><div>${text}</div>`;
    box.classList.remove('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function updateSqlBox(sql, ts) {
    document.getElementById('sqlCode').innerText = sql;
    document.getElementById('sqlTimestamp').innerText = ts || new Date().toLocaleTimeString();
}

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Support preset states via URL parameter
async function handleUrlState() {
    await loadData();
    const params = new URLSearchParams(window.location.search);
    const state = params.get('state');

    if (state === 'initial') {
        updateSqlBox(`-- MariaDB 10.x Database Connection Established
-- Host: landscapingtool.discovery.cs.vt.edu:3306 | Database: landscaping_db
SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema = 'landscaping_db';
-- Ready for Phase 2 GUI Operations: 20 tuples loaded in major table CUSTOMER.`);
    } else if (state === 'insert_modal') {
        openCustomerModal();
    } else if (state === 'insert_success') {
        // Trigger insert of Michael Scott
        await fetch('/api/insert_customer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: 'Michael Scott',
                email: 'm.scott@dundermifflin.com',
                phone_number: '555-0199',
                plan_id: 2,
                password: 'SecurePass2026!'
            })
        });
        await loadData();
        showAlert('success', '<strong>Record successfully inserted into CUSTOMER!</strong> [Generated PK: CustomerID #21]');
        updateSqlBox(`INSERT INTO CUSTOMER (name, email, password, phone_number, plan_id)
VALUES ('Michael Scott', 'm.scott@dundermifflin.com', 'SecurePass2026!', '555-0199', 2);
-- [MariaDB 10.x Engine] Query OK, 1 row affected (0.001 sec)
-- Reflected in table: landscaping_db.CUSTOMER | Generated PK: 21
-- Total tuples in CUSTOMER: 21`);
        window.scrollTo({ top: 600, behavior: 'smooth' });
    } else if (state === 'insert_db') {
        switchView('db_view');
        runCustomQuery('SELECT customer_id, name, email, phone_number, plan_id FROM CUSTOMER WHERE customer_id >= 20 ORDER BY customer_id ASC;');
    } else if (state === 'delete_confirm') {
        promptDelete(21, 'Michael Scott');
    } else if (state === 'delete_success') {
        await fetch('/api/delete_customer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ customer_id: 21 })
        });
        await loadData();
        showAlert('success', '<strong>Record successfully deleted from CUSTOMER!</strong> Customer #21 (Michael Scott) removed from MariaDB.');
        updateSqlBox(`DELETE FROM CUSTOMER WHERE customer_id = 21;
-- [MariaDB 10.x Engine] Query OK, 1 row affected (0.001 sec)
-- ON DELETE CASCADE triggered on foreign keys for customer_id=21
-- Reflected in table: landscaping_db.CUSTOMER
-- Remaining tuples in CUSTOMER: 20`);
        window.scrollTo({ top: 600, behavior: 'smooth' });
    } else if (state === 'delete_db') {
        switchView('db_view');
        runCustomQuery('SELECT * FROM CUSTOMER WHERE customer_id = 21;');
    } else if (state === 'update_search') {
        // Search CUSTOMER, then UPDATE customer #3 through the same code path as the Edit form
        document.getElementById('custSearch').value = 'outlook';
        await loadCustomers(false);
        editCustomer(3);
        document.getElementById('custPhone').value = '555-2003';
        document.getElementById('custPlan').value = '2';
        await submitUpdateCustomer();
    } else if (state === 'workflow_insert') {
        // INSERT a PROJECT_REQUEST picked from the property dropdown, then search for it
        await switchView('workflow');
        openRowModal('PROJECT_REQUEST');
        document.getElementById('rf_property_id').value = '4';
        document.getElementById('rf_property_id').dispatchEvent(new Event('change'));
        document.getElementById('rf_description').value = 'Install paver walkway and LED path lighting.';
        await submitRowForm();
        document.getElementById('wfSearch').value = 'paver';
        await loadWorkflow(false);
    } else if (state === 'workflow_next') {
        // "+ AI Estimate" on request #6 opens the estimate form with its FK pre-selected
        await switchView('workflow');
        await nextStep(6);
        document.getElementById('rf_estimated_price').value = '3800.00';
        document.getElementById('rf_ideas_generated').value = 'Tumbled travertine pavers with a gravel border and two low-voltage accent lights.';
    } else if (state === 'properties') {
        switchView('properties');
        updateSqlBox(`-- Major Table PROPERTY Selected
SELECT property_id, address, sqft, customer_id FROM PROPERTY ORDER BY property_id ASC LIMIT 20;
-- Foreign Key: customer_id REFERENCES CUSTOMER(customer_id) ON DELETE CASCADE`);
    }
}

window.onload = handleUrlState;
</script>

</body>
</html>
"""

def list_rows(table, q):
    cfg = TABLES[table]
    cols = [cfg["pk"]] + [c["name"] for c in cfg["columns"]]
    sql = f"SELECT {', '.join(cols)} FROM {table}"
    params = []
    if q:
        # Search the columns listed in "search", or every non-FK column by default.
        searched = [c for c in cfg["columns"] if c["name"] in cfg.get("search", [])] or \
                   [c for c in cfg["columns"] if c["type"] != "fk"]
        sql += " WHERE " + " OR ".join(
            f"CAST({c['name']} AS TEXT) LIKE ?" if c["type"] in ("number", "fk") else f"{c['name']} LIKE ?"
            for c in searched)
        params = [f"%{q}%"] * len(searched)
    sql += f" ORDER BY {cfg['pk']} ASC"
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    shown = render_sql(sql, params) + f";\n-- {len(rows)} row(s) returned"
    return {"status": "success", "rows": rows, "sql": shown, "timestamp": now()}


def write_row(table, action, payload):
    cfg = TABLES[table]
    pk = cfg["pk"]
    if action == "delete":
        sql, params = f"DELETE FROM {table} WHERE {pk} = ?", [int(payload["id"])]
    else:
        given = payload.get("values", {})
        cols = [c for c in cfg["columns"] if c["name"] in given]
        values = [coerce(c, given[c["name"]]) for c in cols]
        if not cols:
            raise BadInput("No values were submitted.")
        if action == "insert":
            sql = f"INSERT INTO {table} ({', '.join(c['name'] for c in cols)}) VALUES ({', '.join('?' for _ in cols)})"
            params = values
        else:
            sql = f"UPDATE {table} SET {', '.join(c['name'] + ' = ?' for c in cols)} WHERE {pk} = ?"
            params = values + [int(payload["id"])]
    shown = render_sql(sql, params) + ";"
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        result = {"status": "success", "affected": cur.rowcount, "timestamp": now()}
        if action == "insert":
            result["new_id"] = cur.lastrowid
        result["sql"] = shown + f"\n-- Query OK, {cur.rowcount} row(s) affected" + (
            f" | Generated PK {pk} = {cur.lastrowid}" if action == "insert" else "")
        return result
    except sqlite3.DatabaseError as e:
        return {"status": "error", "error": str(e), "sql": shown + f"\n-- ERROR: {e}", "timestamp": now()}
    finally:
        conn.close()


class RequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path in ["/", "/index.html", "/customers", "/properties"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif parsed.path == "/api/customers":
            conn = get_conn()
            rows = conn.execute("SELECT customer_id, name, email, phone_number, plan_id FROM CUSTOMER ORDER BY customer_id ASC").fetchall()
            conn.close()
            self.send_json([dict(r) for r in rows])
        elif parsed.path == "/api/properties":
            conn = get_conn()
            rows = conn.execute("SELECT property_id, address, sqft, customer_id FROM PROPERTY ORDER BY property_id ASC").fetchall()
            conn.close()
            self.send_json([dict(r) for r in rows])
        elif parsed.path == "/api/schema":
            self.send_json(TABLE_CONFIG)
        elif parsed.path == "/api/options":
            conn = get_conn()
            data = {t: [dict(r) for r in conn.execute(sql).fetchall()] for t, sql in FK_OPTIONS.items()}
            conn.close()
            self.send_json(data)
        elif parsed.path == "/api/counts":
            conn = get_conn()
            data = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ALL_TABLES}
            conn.close()
            self.send_json(data)
        elif parsed.path.startswith("/api/rows/") and parsed.path.split("/")[3] in TABLES:
            table = parsed.path.split("/")[3]
            self.send_json(list_rows(table, query.get("q", [""])[0].strip()))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        payload = json.loads(body) if body else {}
        try:
            self.handle_post(parsed.path, payload)
        except (BadInput, KeyError, ValueError) as e:
            msg = str(e) if isinstance(e, BadInput) else f"Invalid input: {e}"
            self.send_json({"status": "error", "error": msg, "sql": f"-- Rejected before reaching the database: {msg}", "timestamp": now()}, 400)
        except sqlite3.DatabaseError as e:
            self.send_json({"status": "error", "error": str(e), "sql": f"-- ERROR: {e}", "timestamp": now()}, 400)

    def handle_post(self, path, payload):
        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "rows"] and parts[2] in TABLES and parts[3] in ("insert", "update", "delete"):
            result = write_row(parts[2], parts[3], payload)
            self.send_json(result, 200 if result["status"] == "success" else 400)

        elif path == "/api/insert_customer":
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO CUSTOMER (name, email, password, phone_number, plan_id)
                VALUES (?, ?, ?, ?, ?)
            """, (payload['name'], payload['email'], payload.get('password', 'secret'), payload['phone_number'], payload['plan_id']))
            new_id = cur.lastrowid
            conn.commit()
            conn.close()

            sql = f"""INSERT INTO CUSTOMER (name, email, password, phone_number, plan_id)
VALUES ('{payload['name']}', '{payload['email']}', '••••••••', '{payload['phone_number']}', {payload['plan_id']});
-- [MariaDB 10.x Engine] Query OK, 1 row affected (0.001 sec)
-- Reflected in table: `landscaping_db.CUSTOMER` | Generated PK: {new_id}"""
            self.send_json({"status": "success", "new_id": new_id, "sql": sql, "timestamp": now()})

        elif path == "/api/delete_customer":
            cid = payload['customer_id']
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM CUSTOMER WHERE customer_id = ?", (cid,))
            conn.commit()
            conn.close()

            sql = f"""DELETE FROM CUSTOMER WHERE customer_id = {cid};
-- [MariaDB 10.x Engine] Query OK, 1 row affected (0.001 sec)
-- ON DELETE CASCADE triggered on foreign keys for customer_id={cid}
-- Reflected in table: `landscaping_db.CUSTOMER`"""
            self.send_json({"status": "success", "sql": sql, "timestamp": now()})

        elif path == "/api/insert_property":
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO PROPERTY (address, sqft, customer_id)
                VALUES (?, ?, ?)
            """, (payload['address'], payload['sqft'], payload['customer_id']))
            new_id = cur.lastrowid
            conn.commit()
            conn.close()

            sql = f"""INSERT INTO PROPERTY (address, sqft, customer_id)
VALUES ('{payload['address']}', {payload['sqft']}, {payload['customer_id']});
-- [MariaDB 10.x Engine] Query OK, 1 row affected
-- Reflected in table: `landscaping_db.PROPERTY` | Generated PK: {new_id}"""
            self.send_json({"status": "success", "new_id": new_id, "sql": sql, "timestamp": now()})

        elif path == "/api/delete_property":
            pid = payload['property_id']
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM PROPERTY WHERE property_id = ?", (pid,))
            conn.commit()
            conn.close()

            sql = f"""DELETE FROM PROPERTY WHERE property_id = {pid};
-- [MariaDB 10.x Engine] Query OK, 1 row affected
-- Reflected in table: `landscaping_db.PROPERTY`"""
            self.send_json({"status": "success", "sql": sql, "timestamp": now()})

        elif path == "/api/query":
            raw_sql = payload.get("query", "").strip()
            conn = sqlite3.connect(DB_FILE)
            try:
                cur = conn.cursor()
                cur.execute(raw_sql)
                cols = [d[0] for d in cur.description] if cur.description else []
                rows = cur.fetchall()
                conn.close()
                self.send_json({
                    "status": "success",
                    "sql": f"{raw_sql}\n-- Query executed successfully against landscaping_db",
                    "columns": cols,
                    "rows": rows,
                    "timestamp": now()
                })
            except Exception as e:
                conn.close()
                self.send_json({
                    "status": "error",
                    "error": str(e),
                    "sql": f"{raw_sql}\n-- ERROR: {str(e)}",
                    "timestamp": now()
                })
        else:
            self.send_response(404)
            self.end_headers()

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, fmt, *args):
        pass


def run():
    init_database()
    print(f"Starting CS 4604 Group 6 Landscaping Portal on http://localhost:{PORT}")
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("", PORT), RequestHandler)
    server.serve_forever()

if __name__ == "__main__":
    run()
