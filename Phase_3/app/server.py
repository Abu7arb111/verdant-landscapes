#!/usr/bin/env python3
"""
CS 4604 Introduction to Database Systems - Phase 2 GUI & Database Engine
Group 6: Landscaping AI Estimator
Team Members: Zachary Brosius, Saveer Pande, Benny He, Ahmad Abu Harb
DBMS Backend: SQLite demo or MariaDB
"""

import atexit
import getpass
import hashlib
import shutil
import socket
import subprocess
import hmac
import http.server
import socketserver
import json
import re
import secrets
import sqlite3
import sys
import time
import os
import urllib.parse
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from html import escape
from http import cookies

APP_DIR = os.path.dirname(os.path.abspath(__file__))

# MariaDB settings come from environment variables, or from the git-ignored file
# db_config.local.json next to this script (environment variables win).
DB_CONFIG_FILE = os.path.join(APP_DIR, "db_config.local.json")
if os.path.exists(DB_CONFIG_FILE):
    with open(DB_CONFIG_FILE, encoding="utf-8") as _f:
        for _key, _value in json.load(_f).items():
            if _key in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASS") and _value not in (None, ""):
                os.environ.setdefault(_key, str(_value))

# "--demo" runs against the local SQLite copy instead. Without it the server only uses
# MariaDB, so every change made on the website is what phpMyAdmin shows.
DEMO_MODE = "--demo" in sys.argv
# With no DB_HOST given, use the usual tunnel to Discovery (localhost:3307) and start it
# ourselves if it is not running, so a plain "py server.py" reaches the real database.
AUTO_TUNNEL = not DEMO_MODE and not os.environ.get("DB_HOST")
if AUTO_TUNNEL:
    os.environ["DB_HOST"] = "127.0.0.1"
    os.environ.setdefault("DB_PORT", "3307")
PORT = int(os.environ.get("PORT", 8080))
DB_HOST = None if DEMO_MODE else os.environ.get("DB_HOST")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_NAME = os.environ.get("DB_NAME", "landscaping_db")
DB_ERRORS = (sqlite3.DatabaseError,)
if DB_HOST:
    try:
        import pymysql
    except ImportError:
        raise SystemExit("Install the MariaDB driver with:  py -m pip install -r Phase_3/app/requirements.txt")
    DB_ERRORS += (pymysql.MySQLError,)

DB_FILE = os.path.join(APP_DIR, "landscaping.db")
SQL_FILE = os.path.join(APP_DIR, "..", "sql", "landscaping_phase2_schema_and_data.sql")

ALL_TABLES = [
    "SUBSCRIPTION_PLAN", "CONTRACTOR", "CUSTOMER", "PROPERTY", "PROJECT_REQUEST", "PHOTO",
    "AI_ESTIMATE", "CONTRACTOR_QUOTE", "APPOINTMENT", "JOB", "INVOICE", "PAYMENT",
]


def mariadb_to_sqlite(script):
    """Small translation so the same .sql file we import into MariaDB also runs on SQLite."""
    script = re.sub(r"(?im)^\s*(CREATE DATABASE|USE)\b[^;]*;", "", script)
    # Session settings only (not the "SET status = ..." inside a trigger's UPDATE)
    script = re.sub(r"(?im)^\s*SET\s+(FOREIGN_KEY_CHECKS|NAMES|SQL_MODE|AUTOCOMMIT|UNIQUE_CHECKS|TIME_ZONE)\b[^;]*;", "", script)
    script = re.sub(r"(?i)\bINT\s+AUTO_INCREMENT\s+PRIMARY\s+KEY", "INTEGER PRIMARY KEY AUTOINCREMENT", script)
    script = re.sub(r"(?i)\)\s*ENGINE\s*=\s*\w+[^;]*;", ");", script)
    script = re.sub(r"(?i)\bCREATE\s+OR\s+REPLACE\s+VIEW\b", "CREATE VIEW", script)
    # MariaDB allows a single-statement trigger body; SQLite needs BEGIN ... END
    script = re.sub(r"(?is)(CREATE\s+TRIGGER\b.*?\bFOR\s+EACH\s+ROW)\s+(?!BEGIN\b)(.*?;)", r"\1\nBEGIN\n\2\nEND;", script)
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


class MariaDBConnection:
    def __init__(self):
        self.connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASS"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            client_flag=pymysql.constants.CLIENT.FOUND_ROWS,
            connect_timeout=5,
        )

    def execute(self, sql, params=()):
        cursor = self.connection.cursor()
        if params:
            cursor.execute(sql.replace("%", "%%").replace("?", "%s"), params)
        else:
            cursor.execute(sql)
        return cursor

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def get_conn():
    if DB_HOST:
        return MariaDBConnection()
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
    {"table": "PROPERTY", "pk": "property_id", "singular": "Property", "workflow": False, "search": ["address", "sqft"],
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
    # "Contractors & More" tab (group "manage"): records that are not a step in the project chain.
    {"table": "CONTRACTOR", "pk": "contractor_id", "singular": "Contractor", "label": "Contractors",
     "icon": "🚜", "group": "manage", "search": ["business_name", "contact_name", "email", "phone_number"],
     "help": "Landscaping businesses that quote and do the work. They log in with their email.",
     "cascade": "their quotes, jobs, site visits and the invoices and payments for those jobs",
     "columns": [
         {"name": "business_name", "label": "Business Name", "type": "text"},
         {"name": "contact_name", "label": "Contact Name", "type": "text"},
         {"name": "email", "label": "Email (login)", "type": "email"},
         {"name": "phone_number", "label": "Phone Number", "type": "text"},
         {"name": "password", "label": "Password (at least 8 characters)", "type": "password"},
     ]},
    {"table": "APPOINTMENT", "pk": "appointment_id", "singular": "Site visit", "label": "Site visits",
     "icon": "📅", "group": "manage", "search": ["status", "scheduled"],
     "help": "Visits where a contractor looks at a customer's property for a project.",
     "cascade": "nothing else",
     "columns": [
         {"name": "request_id", "label": "Project", "type": "fk", "ref": "PROJECT_REQUEST", "fill": {"customer_id": "customer"}},
         {"name": "customer_id", "label": "Customer", "type": "fk", "ref": "CUSTOMER"},
         {"name": "contractor_id", "label": "Contractor", "type": "fk", "ref": "CONTRACTOR"},
         {"name": "scheduled", "label": "Date & Time", "type": "datetime"},
         {"name": "status", "label": "Status", "type": "select",
          "options": ["Pending", "Confirmed", "Scheduled", "Completed", "Cancelled"]},
     ]},
    {"table": "PHOTO", "pk": "photo_id", "singular": "Photo", "label": "Photos",
     "icon": "📷", "group": "manage", "search": ["file_url", "file_type"],
     "help": "Photos of a property attached to a project request (stored as a link).",
     "cascade": "nothing else",
     "columns": [
         {"name": "request_id", "label": "Project", "type": "fk", "ref": "PROJECT_REQUEST"},
         {"name": "file_url", "label": "Photo Link", "type": "url"},
         {"name": "file_type", "label": "File Type", "type": "select", "options": ["image/jpeg", "image/png", "image/webp"]},
     ]},
    {"table": "SUBSCRIPTION_PLAN", "pk": "plan_id", "singular": "Subscription plan", "label": "Plans",
     "icon": "🏷️", "group": "manage", "search": ["plan_name", "tier"],
     "help": "Monthly plans customers can sign up for.",
     "cascade": "nothing else; customers on this plan are left without a plan",
     "columns": [
         {"name": "plan_name", "label": "Plan Name", "type": "text"},
         {"name": "price", "label": "Monthly Price ($)", "type": "number", "money": True},
         {"name": "tier", "label": "Tier", "type": "text"},
     ]},
]
for _cfg in TABLE_CONFIG:
    _cfg.setdefault("group", "workflow" if _cfg.get("workflow") else None)
TABLES = {cfg["table"]: cfg for cfg in TABLE_CONFIG}

# SELECTs that fill the foreign-key dropdowns. Extra columns (owner, sqft, ...) let the form
# pre-fill related fields when a parent row is picked.
FK_OPTIONS = {
    "SUBSCRIPTION_PLAN": "SELECT plan_id AS value, plan_name || ' ($' || printf('%.2f', price) || '/mo)' AS label FROM SUBSCRIPTION_PLAN ORDER BY plan_id",
    "CUSTOMER": "SELECT customer_id AS value, name AS label FROM CUSTOMER ORDER BY name",
    "CONTRACTOR": "SELECT contractor_id AS value, business_name AS label FROM CONTRACTOR ORDER BY business_name",
    "PROPERTY": "SELECT property_id AS value, address AS label, customer_id AS owner FROM PROPERTY ORDER BY address",
    "PROJECT_REQUEST": "SELECT r.request_id AS value, c.name || ': ' || substr(r.description, 1, 48) AS label, p.sqft AS sqft, r.customer_id AS customer FROM PROJECT_REQUEST r JOIN PROPERTY p ON p.property_id = r.property_id JOIN CUSTOMER c ON c.customer_id = r.customer_id ORDER BY c.name, r.request_id",
    "AI_ESTIMATE": "SELECT e.ai_id AS value, c.name || ': ' || substr(r.description, 1, 40) || ' - $' || printf('%.2f', e.estimated_price) AS label, e.estimated_price FROM AI_ESTIMATE e JOIN PROJECT_REQUEST r ON r.request_id = e.request_id JOIN CUSTOMER c ON c.customer_id = r.customer_id ORDER BY c.name, e.ai_id",
    "CONTRACTOR_QUOTE": "SELECT q.quote_id AS value, k.business_name || ' for ' || c.name || ' - $' || printf('%.2f', q.final_price) || ' (' || q.status || ')' AS label, q.contractor_id, q.final_price FROM CONTRACTOR_QUOTE q JOIN CONTRACTOR k ON k.contractor_id = q.contractor_id JOIN AI_ESTIMATE e ON e.ai_id = q.ai_id JOIN PROJECT_REQUEST r ON r.request_id = e.request_id JOIN CUSTOMER c ON c.customer_id = r.customer_id ORDER BY k.business_name, q.quote_id",
    "JOB": "SELECT j.job_id AS value, k.business_name || ' for ' || c.name || ' (' || j.status || ', starts ' || j.start_date || ')' AS label, j.revenue FROM JOB j JOIN CONTRACTOR k ON k.contractor_id = j.contractor_id JOIN CONTRACTOR_QUOTE q ON q.quote_id = j.quote_id JOIN AI_ESTIMATE e ON e.ai_id = q.ai_id JOIN PROJECT_REQUEST r ON r.request_id = e.request_id JOIN CUSTOMER c ON c.customer_id = r.customer_id ORDER BY c.name, j.job_id",
    "INVOICE": "SELECT i.invoice_id AS value, c.name || ' - $' || printf('%.2f', i.amount_due) || ' due ' || i.due_date || ' (' || i.status || ')' AS label, i.amount_due FROM INVOICE i JOIN JOB j ON j.job_id = i.job_id JOIN CONTRACTOR_QUOTE q ON q.quote_id = j.quote_id JOIN AI_ESTIMATE e ON e.ai_id = q.ai_id JOIN PROJECT_REQUEST r ON r.request_id = e.request_id JOIN CUSTOMER c ON c.customer_id = r.customer_id ORDER BY c.name, i.invoice_id",
}


if DB_HOST:
    FK_OPTIONS.update({
        "SUBSCRIPTION_PLAN": "SELECT plan_id AS value, CONCAT(plan_name, ' ($', FORMAT(price, 2), '/mo)') AS label FROM SUBSCRIPTION_PLAN ORDER BY plan_id",
        "PROJECT_REQUEST": "SELECT r.request_id AS value, CONCAT(c.name, ': ', SUBSTR(r.description, 1, 48)) AS label, p.sqft AS sqft, r.customer_id AS customer FROM PROJECT_REQUEST r JOIN PROPERTY p ON p.property_id = r.property_id JOIN CUSTOMER c ON c.customer_id = r.customer_id ORDER BY c.name, r.request_id",
        "AI_ESTIMATE": "SELECT e.ai_id AS value, CONCAT(c.name, ': ', SUBSTR(r.description, 1, 40), ' - $', FORMAT(e.estimated_price, 2)) AS label, e.estimated_price FROM AI_ESTIMATE e JOIN PROJECT_REQUEST r ON r.request_id = e.request_id JOIN CUSTOMER c ON c.customer_id = r.customer_id ORDER BY c.name, e.ai_id",
        "CONTRACTOR_QUOTE": "SELECT q.quote_id AS value, CONCAT(k.business_name, ' for ', c.name, ' - $', FORMAT(q.final_price, 2), ' (', q.status, ')') AS label, q.contractor_id, q.final_price FROM CONTRACTOR_QUOTE q JOIN CONTRACTOR k ON k.contractor_id = q.contractor_id JOIN AI_ESTIMATE e ON e.ai_id = q.ai_id JOIN PROJECT_REQUEST r ON r.request_id = e.request_id JOIN CUSTOMER c ON c.customer_id = r.customer_id ORDER BY k.business_name, q.quote_id",
        "JOB": "SELECT j.job_id AS value, CONCAT(k.business_name, ' for ', c.name, ' (', j.status, ', starts ', j.start_date, ')') AS label, j.revenue FROM JOB j JOIN CONTRACTOR k ON k.contractor_id = j.contractor_id JOIN CONTRACTOR_QUOTE q ON q.quote_id = j.quote_id JOIN AI_ESTIMATE e ON e.ai_id = q.ai_id JOIN PROJECT_REQUEST r ON r.request_id = e.request_id JOIN CUSTOMER c ON c.customer_id = r.customer_id ORDER BY c.name, j.job_id",
        "INVOICE": "SELECT i.invoice_id AS value, CONCAT(c.name, ' - $', FORMAT(i.amount_due, 2), ' due ', i.due_date, ' (', i.status, ')') AS label, i.amount_due FROM INVOICE i JOIN JOB j ON j.job_id = i.job_id JOIN CONTRACTOR_QUOTE q ON q.quote_id = j.quote_id JOIN AI_ESTIMATE e ON e.ai_id = q.ai_id JOIN PROJECT_REQUEST r ON r.request_id = e.request_id JOIN CUSTOMER c ON c.customer_id = r.customer_id ORDER BY c.name, i.invoice_id",
    })


# Fixed report queries for the Reports tab. Each shows a different SQL technique.
# "chart" picks the label/value columns drawn as a bar chart above the table.
# Shared SQL: every job's chain back to its request (JOB -> quote -> estimate -> request).
JOB_TO_REQUEST = """JOIN CONTRACTOR_QUOTE q ON q.quote_id = j.quote_id
JOIN AI_ESTIMATE e      ON e.ai_id = q.ai_id
JOIN PROJECT_REQUEST r  ON r.request_id = e.request_id"""
PAID_BY_INVOICE = """LEFT JOIN (SELECT invoice_id, SUM(amount) AS paid FROM PAYMENT
           WHERE status = 'Completed' GROUP BY invoice_id) pd ON pd.invoice_id = i.invoice_id"""
SIZE_BUCKET = """CASE WHEN p.sqft < 5000 THEN 'Small (under 5,000 sq ft)'
            WHEN p.sqft < 10000 THEN 'Medium (5,000-9,999 sq ft)'
            ELSE 'Large (10,000+ sq ft)' END"""

REPORTS = [
    {"id": "platform_overview", "title": "Business Overview (Managerial)",
     "description": "One-line snapshot of the whole business: users, requests, jobs, revenue billed and money collected.",
     "tags": ["Managerial", "COUNT", "SUM", "AVG", "scalar subqueries"],
     "sql": """SELECT (SELECT COUNT(*) FROM CUSTOMER)        AS customers,
       (SELECT COUNT(*) FROM CONTRACTOR)                   AS contractors,
       (SELECT COUNT(*) FROM PROJECT_REQUEST)              AS requests,
       (SELECT COUNT(*) FROM JOB)                          AS jobs,
       (SELECT SUM(revenue) FROM JOB)                      AS total_revenue,
       (SELECT ROUND(AVG(revenue), 2) FROM JOB)            AS avg_job_revenue,
       (SELECT SUM(amount_due) FROM INVOICE)               AS total_invoiced_amount,
       (SELECT SUM(amount) FROM PAYMENT WHERE status = 'Completed') AS total_collected_amount"""},
    {"id": "job_stats_by_status", "title": "Job Value Statistics by Status (Managerial)",
     "description": "How many jobs are in each stage and the smallest, largest, average and total job value.",
     "tags": ["Managerial", "COUNT", "SUM", "AVG", "MIN", "MAX"], "chart": ["job_status", "total_revenue"],
     "sql": """SELECT j.status                    AS job_status,
       COUNT(*)                          AS jobs,
       SUM(j.revenue)                    AS total_revenue,
       ROUND(AVG(j.revenue), 2)          AS avg_revenue,
       MIN(j.revenue)                    AS min_revenue,
       MAX(j.revenue)                    AS max_revenue,
       SUM(j.revenue - j.expenses)       AS total_profit
FROM JOB j
GROUP BY j.status
ORDER BY total_revenue DESC"""},
    {"id": "contractor_leaderboard", "title": "Contractor Performance Leaderboard (Managerial)",
     "description": "Quotes sent, quotes won and the win rate for each contractor, with their lowest, highest and average quote.",
     "tags": ["Managerial", "COUNT", "SUM", "AVG", "MIN", "MAX", "CASE"], "chart": ["contractor", "avg_quote_price"],
     "sql": """SELECT k.business_name               AS contractor,
       COUNT(q.quote_id)                 AS quotes,
       SUM(CASE WHEN q.status = 'Accepted' THEN 1 ELSE 0 END) AS won,
       ROUND(100.0 * SUM(CASE WHEN q.status = 'Accepted' THEN 1 ELSE 0 END) / COUNT(q.quote_id), 1) AS win_pct,
       ROUND(AVG(q.final_price), 2)      AS avg_quote_price,
       MIN(q.final_price)                AS min_quote_price,
       MAX(q.final_price)                AS max_quote_price
FROM CONTRACTOR k
JOIN CONTRACTOR_QUOTE q ON q.contractor_id = k.contractor_id
GROUP BY k.contractor_id, k.business_name
ORDER BY won DESC, quotes DESC"""},
    {"id": "monthly_revenue", "title": "Monthly Revenue Trend (Managerial)",
     "description": "Jobs started per month with revenue, expenses, profit and the average profit per job.",
     "tags": ["Managerial", "COUNT", "SUM", "AVG", "MAX", "GROUP BY month"], "chart": ["month", "total_revenue"],
     "sql": """SELECT SUBSTR(j.start_date, 1, 7)    AS month,
       COUNT(*)                          AS jobs,
       SUM(j.revenue)                    AS total_revenue,
       SUM(j.expenses)                   AS total_expenses,
       SUM(j.revenue - j.expenses)       AS total_profit,
       ROUND(AVG(j.revenue - j.expenses), 2) AS avg_profit,
       MAX(j.revenue)                    AS max_revenue
FROM JOB j
GROUP BY SUBSTR(j.start_date, 1, 7)
ORDER BY month"""},
    {"id": "plan_property_stats", "title": "Customers & Property Sizes by Plan (Managerial)",
     "description": "Customers and properties on each subscription plan, with the smallest, largest and average lot size.",
     "tags": ["Managerial", "COUNT DISTINCT", "AVG", "MIN", "MAX", "LEFT JOIN"], "chart": ["plan_name", "customers"],
     "sql": """SELECT sp.plan_name,
       COUNT(DISTINCT c.customer_id)     AS customers,
       COUNT(p.property_id)              AS properties,
       ROUND(AVG(p.sqft), 0)             AS avg_sqft,
       MIN(p.sqft)                       AS min_sqft,
       MAX(p.sqft)                       AS max_sqft
FROM SUBSCRIPTION_PLAN sp
LEFT JOIN CUSTOMER c ON c.plan_id = sp.plan_id
LEFT JOIN PROPERTY p ON p.customer_id = c.customer_id
GROUP BY sp.plan_id, sp.plan_name
ORDER BY sp.plan_id"""},
    {"id": "revenue_by_plan", "title": "Revenue & Profit by Subscription Plan",
     "description": "Follows every job back to the customer who requested it and totals revenue, expenses and profit for each subscription plan.",
     "tags": ["6-table JOIN", "GROUP BY", "SUM", "computed margin"],
     "sql": """SELECT sp.plan_name, sp.tier,
       COUNT(j.job_id)                   AS jobs,
       SUM(j.revenue)                    AS total_revenue,
       SUM(j.expenses)                   AS total_expenses,
       SUM(j.revenue - j.expenses)       AS total_profit,
       ROUND(100.0 * SUM(j.revenue - j.expenses) / SUM(j.revenue), 1) AS margin_pct
FROM SUBSCRIPTION_PLAN sp
JOIN CUSTOMER c          ON c.plan_id     = sp.plan_id
JOIN PROJECT_REQUEST r   ON r.customer_id = c.customer_id
JOIN AI_ESTIMATE e       ON e.request_id  = r.request_id
JOIN CONTRACTOR_QUOTE q  ON q.ai_id       = e.ai_id
JOIN JOB j               ON j.quote_id    = q.quote_id
GROUP BY sp.plan_id, sp.plan_name, sp.tier
ORDER BY total_profit DESC"""},
    {"id": "outstanding_invoices", "title": "Outstanding Invoices",
     "description": "Every invoice that still has money owed, using the v_invoice_balance view (only Completed payments count as paid).",
     "tags": ["VIEW", "LEFT JOIN", "CASE", "WHERE on aggregate"],
     "sql": """SELECT invoice_id, customer_name, amount_due, amount_paid, balance_due, due_date, status
FROM v_invoice_balance
WHERE balance_due > 0
ORDER BY balance_due DESC"""},
    {"id": "customers_owing", "title": "Customers Owing More Than $500",
     "description": "Groups the open balances by customer and keeps only customers who owe more than $500 in total.",
     "tags": ["VIEW", "GROUP BY", "HAVING", "COUNT"],
     "sql": """SELECT customer_name,
       COUNT(*)         AS open_invoices,
       SUM(balance_due) AS total_owed
FROM v_invoice_balance
WHERE balance_due > 0
GROUP BY customer_name
HAVING SUM(balance_due) > 500
ORDER BY total_owed DESC"""},
    {"id": "estimate_accuracy", "title": "AI Estimate vs. Contractor Quote",
     "description": "How far each contractor's quote landed from the AI estimate, largest gaps first.",
     "tags": ["4-table JOIN", "computed columns", "ABS", "ORDER BY expression"],
     "sql": """SELECT r.request_id,
       k.business_name   AS contractor,
       e.estimated_price AS ai_estimate,
       q.final_price     AS quoted_price,
       q.final_price - e.estimated_price AS gap,
       ROUND(100.0 * (q.final_price - e.estimated_price) / e.estimated_price, 1) AS gap_pct,
       q.status          AS quote_status
FROM CONTRACTOR_QUOTE q
JOIN AI_ESTIMATE e      ON e.ai_id         = q.ai_id
JOIN PROJECT_REQUEST r  ON r.request_id    = e.request_id
JOIN CONTRACTOR k       ON k.contractor_id = q.contractor_id
ORDER BY ABS(q.final_price - e.estimated_price) DESC"""},
    {"id": "contractors_no_accepted", "title": "Contractors With No Accepted Quote",
     "description": "Contractors who have submitted quotes but have never had one accepted.",
     "tags": ["NOT EXISTS subquery", "LEFT JOIN", "GROUP BY"],
     "sql": """SELECT k.contractor_id, k.business_name, k.contact_name,
       COUNT(q.quote_id) AS quotes_submitted
FROM CONTRACTOR k
LEFT JOIN CONTRACTOR_QUOTE q ON q.contractor_id = k.contractor_id
WHERE NOT EXISTS (
    SELECT 1 FROM CONTRACTOR_QUOTE a
    WHERE a.contractor_id = k.contractor_id AND a.status = 'Accepted'
)
GROUP BY k.contractor_id, k.business_name, k.contact_name
ORDER BY k.contractor_id"""},
    {"id": "job_summary", "title": "Job Summary (v_job_summary)",
     "description": "The v_job_summary view: every job with its customer, property, contractor, the AI estimate, the quote and the profit.",
     "tags": ["VIEW", "7-table JOIN"],
     "sql": """SELECT job_id, customer_name, property_address, contractor, job_status,
       ai_estimate, quoted_price, revenue, profit
FROM v_job_summary
ORDER BY profit DESC"""},
]
REPORTS_BY_ID = {r["id"]: r for r in REPORTS}

# Reports for end users. Every "?" is the logged-in account's id (from the session), so each
# person only ever sees statistics about their own data. "money" lists columns shown as $.
CUSTOMER_REPORTS = [
    {"id": "spending_by_contractor", "title": "My Spending by Contractor",
     "description": "How many jobs each contractor did for you, the total you spent, and your cheapest, priciest and average job.",
     "chart": ["contractor", "total_spent"], "money": ["total_spent", "avg_job", "cheapest_job", "priciest_job"],
     "sql": f"""SELECT k.business_name AS contractor,
       COUNT(j.job_id)          AS jobs,
       SUM(j.revenue)           AS total_spent,
       ROUND(AVG(j.revenue), 2) AS avg_job,
       MIN(j.revenue)           AS cheapest_job,
       MAX(j.revenue)           AS priciest_job
FROM JOB j
{JOB_TO_REQUEST}
JOIN CONTRACTOR k ON k.contractor_id = j.contractor_id
WHERE r.customer_id = ?
GROUP BY k.contractor_id, k.business_name
ORDER BY total_spent DESC"""},
    {"id": "quote_comparison", "title": "Quote Comparison per Request",
     "description": "For each of your requests: how many quotes came in, the lowest, highest and average quote, next to the estimate.",
     "chart": ["request", "avg_quote"], "money": ["estimate", "lowest_quote", "highest_quote", "avg_quote"],
     "sql": """SELECT r.description              AS request,
       MAX(e.estimated_price)     AS estimate,
       COUNT(q.quote_id)          AS quotes,
       MIN(q.final_price)         AS lowest_quote,
       MAX(q.final_price)         AS highest_quote,
       ROUND(AVG(q.final_price), 2) AS avg_quote
FROM PROJECT_REQUEST r
JOIN AI_ESTIMATE e      ON e.request_id = r.request_id
JOIN CONTRACTOR_QUOTE q ON q.ai_id = e.ai_id
WHERE r.customer_id = ?
GROUP BY r.request_id, r.description
ORDER BY r.request_id DESC"""},
    {"id": "spending_by_property", "title": "Projects & Spending by Property",
     "description": "Requests and completed spending for each of your properties, including your largest and average job there.",
     "chart": ["property", "total_spent"], "money": ["total_spent", "avg_job", "largest_job"],
     "sql": """SELECT p.address                  AS property,
       COUNT(DISTINCT r.request_id)  AS requests,
       COUNT(j.job_id)            AS jobs,
       COALESCE(SUM(j.revenue), 0) AS total_spent,
       ROUND(AVG(j.revenue), 2)   AS avg_job,
       MAX(j.revenue)             AS largest_job
FROM PROPERTY p
LEFT JOIN PROJECT_REQUEST r  ON r.property_id = p.property_id
LEFT JOIN AI_ESTIMATE e      ON e.request_id = r.request_id
LEFT JOIN CONTRACTOR_QUOTE q ON q.ai_id = e.ai_id AND q.status = 'Accepted'
LEFT JOIN JOB j              ON j.quote_id = q.quote_id
WHERE p.customer_id = ?
GROUP BY p.property_id, p.address
ORDER BY total_spent DESC"""},
    {"id": "invoice_summary", "title": "My Invoices by Status",
     "description": "Invoices grouped by status: how many, total billed and paid, the average invoice, and the earliest and latest due dates.",
     "chart": ["status", "total_billed"], "money": ["total_billed", "total_paid", "avg_invoice"],
     "sql": f"""SELECT i.status,
       COUNT(*)                    AS invoices,
       SUM(i.amount_due)           AS total_billed,
       SUM(COALESCE(pd.paid, 0))   AS total_paid,
       ROUND(AVG(i.amount_due), 2) AS avg_invoice,
       MIN(i.due_date)             AS earliest_due,
       MAX(i.due_date)             AS latest_due
FROM INVOICE i
JOIN JOB j ON j.job_id = i.job_id
{JOB_TO_REQUEST}
{PAID_BY_INVOICE}
WHERE r.customer_id = ?
GROUP BY i.status
ORDER BY total_billed DESC"""},
    {"id": "payments_by_method", "title": "My Payments by Method",
     "description": "Completed payments grouped by how you paid: count, total, average, smallest and largest payment.",
     "chart": ["payment_method", "total_paid"], "money": ["total_paid", "avg_payment", "smallest_payment", "largest_payment"],
     "sql": f"""SELECT pm.payment_method,
       COUNT(*)                  AS payments,
       SUM(pm.amount)            AS total_paid,
       ROUND(AVG(pm.amount), 2)  AS avg_payment,
       MIN(pm.amount)            AS smallest_payment,
       MAX(pm.amount)            AS largest_payment
FROM PAYMENT pm
JOIN INVOICE i ON i.invoice_id = pm.invoice_id
JOIN JOB j     ON j.job_id = i.job_id
{JOB_TO_REQUEST}
WHERE r.customer_id = ? AND pm.status = 'Completed'
GROUP BY pm.payment_method
ORDER BY total_paid DESC"""},
]

CONTRACTOR_REPORTS = [
    {"id": "monthly_earnings", "title": "My Monthly Earnings",
     "description": "Jobs started each month with revenue, expenses, profit and the average profit per job.",
     "chart": ["month", "profit"], "money": ["revenue", "expenses", "profit", "avg_profit_per_job", "biggest_job"],
     "sql": """SELECT SUBSTR(j.start_date, 1, 7)    AS month,
       COUNT(*)                          AS jobs,
       SUM(j.revenue)                    AS revenue,
       SUM(j.expenses)                   AS expenses,
       SUM(j.revenue - j.expenses)       AS profit,
       ROUND(AVG(j.revenue - j.expenses), 2) AS avg_profit_per_job,
       MAX(j.revenue)                    AS biggest_job
FROM JOB j
WHERE j.contractor_id = ?
GROUP BY SUBSTR(j.start_date, 1, 7)
ORDER BY month"""},
    {"id": "quote_outcomes", "title": "My Quotes by Outcome",
     "description": "How many of your quotes are pending, accepted or rejected, with the total, average, lowest and highest price.",
     "chart": ["status", "quotes"], "money": ["total_quoted", "avg_price", "lowest_price", "highest_price"],
     "sql": """SELECT q.status,
       COUNT(*)                       AS quotes,
       SUM(q.final_price)             AS total_quoted,
       ROUND(AVG(q.final_price), 2)   AS avg_price,
       MIN(q.final_price)             AS lowest_price,
       MAX(q.final_price)             AS highest_price
FROM CONTRACTOR_QUOTE q
WHERE q.contractor_id = ?
GROUP BY q.status
ORDER BY quotes DESC"""},
    {"id": "pricing_by_lot_size", "title": "My Pricing vs. Estimate by Lot Size",
     "description": "Your quotes grouped by property size: average estimate vs. your average price, your price range, and price per sq ft.",
     "chart": ["lot_size", "avg_my_price"], "money": ["avg_estimate", "avg_my_price", "lowest_price", "highest_price", "avg_price_per_sqft"],
     "sql": f"""SELECT {SIZE_BUCKET} AS lot_size,
       COUNT(*)                                 AS quotes,
       ROUND(AVG(e.estimated_price), 2)         AS avg_estimate,
       ROUND(AVG(q.final_price), 2)             AS avg_my_price,
       MIN(q.final_price)                       AS lowest_price,
       MAX(q.final_price)                       AS highest_price,
       ROUND(AVG(q.final_price * 1.0 / p.sqft), 3) AS avg_price_per_sqft
FROM CONTRACTOR_QUOTE q
JOIN AI_ESTIMATE e     ON e.ai_id = q.ai_id
JOIN PROJECT_REQUEST r ON r.request_id = e.request_id
JOIN PROPERTY p        ON p.property_id = r.property_id
WHERE q.contractor_id = ?
GROUP BY {SIZE_BUCKET}
ORDER BY MIN(p.sqft)"""},
    {"id": "top_customers", "title": "My Top Customers",
     "description": "Customers ranked by the revenue their jobs brought you, with job count, average, largest job and first job date.",
     "chart": ["customer", "revenue"], "money": ["revenue", "avg_job", "largest_job"],
     "sql": f"""SELECT c.name                    AS customer,
       COUNT(j.job_id)            AS jobs,
       SUM(j.revenue)             AS revenue,
       ROUND(AVG(j.revenue), 2)   AS avg_job,
       MAX(j.revenue)             AS largest_job,
       MIN(j.start_date)          AS first_job
FROM JOB j
{JOB_TO_REQUEST}
JOIN CUSTOMER c ON c.customer_id = r.customer_id
WHERE j.contractor_id = ?
GROUP BY c.customer_id, c.name
ORDER BY revenue DESC"""},
    {"id": "collections", "title": "My Invoices & Collections by Status",
     "description": "Invoices you sent, grouped by status: total billed vs. collected, average invoice and the smallest and largest invoice.",
     "chart": ["status", "collected"], "money": ["billed", "collected", "avg_invoice", "smallest_invoice", "largest_invoice"],
     "sql": f"""SELECT i.status,
       COUNT(*)                    AS invoices,
       SUM(i.amount_due)           AS billed,
       SUM(COALESCE(pd.paid, 0))   AS collected,
       ROUND(AVG(i.amount_due), 2) AS avg_invoice,
       MIN(i.amount_due)           AS smallest_invoice,
       MAX(i.amount_due)           AS largest_invoice
FROM INVOICE i
JOIN JOB j ON j.job_id = i.job_id
{PAID_BY_INVOICE}
WHERE j.contractor_id = ?
GROUP BY i.status
ORDER BY billed DESC"""},
]
ROLE_REPORTS = {"customer": {r["id"]: r for r in CUSTOMER_REPORTS},
                "contractor": {r["id"]: r for r in CONTRACTOR_REPORTS}}


def report_meta(report):
    return {k: report[k] for k in ("id", "title", "description", "tags", "chart", "money") if k in report}


def run_report(report_id, registry=None, uid=None):
    report = (registry or REPORTS_BY_ID)[report_id]
    params = (uid,) * report["sql"].count("?")
    with closing(get_conn()) as conn:
        cur = conn.execute(report["sql"], params)
        cols = [d[0] for d in cur.description]
        rows = [[r[col] for col in cols] for r in cur.fetchall()]
    return {"status": "success", "columns": cols, "rows": rows, "chart": report.get("chart"),
            "sql": render_sql(report["sql"], params) + f";\n-- {len(rows)} row(s) returned", "timestamp": now()}


def db_objects():
    if DB_HOST:
        with closing(get_conn()) as conn:
            views = conn.execute("""
                SELECT 'view' AS type, TABLE_NAME AS name, TABLE_NAME AS tbl_name,
                       VIEW_DEFINITION AS `sql`
                FROM information_schema.VIEWS WHERE TABLE_SCHEMA = DATABASE()
                ORDER BY TABLE_NAME
            """).fetchall()
            triggers = conn.execute("""
                SELECT 'trigger' AS type, TRIGGER_NAME AS name,
                       EVENT_OBJECT_TABLE AS tbl_name, ACTION_STATEMENT AS `sql`
                FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA = DATABASE()
                ORDER BY TRIGGER_NAME
            """).fetchall()
            indexes = conn.execute("""
                SELECT 'index' AS type, INDEX_NAME AS name, TABLE_NAME AS tbl_name,
                       GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX SEPARATOR ', ') AS `sql`
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE() AND INDEX_NAME <> 'PRIMARY'
                GROUP BY TABLE_NAME, INDEX_NAME
                ORDER BY INDEX_NAME, TABLE_NAME
            """).fetchall()
            return [*views, *triggers, *indexes]
    conn = get_conn()
    rows = conn.execute("""SELECT type, name, tbl_name, sql FROM sqlite_master
                           WHERE type IN ('view', 'trigger', 'index') AND name NOT LIKE 'sqlite_%'
                           ORDER BY CASE type WHEN 'view' THEN 1 WHEN 'trigger' THEN 2 ELSE 3 END, name""").fetchall()
    conn.close()
    return [dict(r) for r in rows]


class BadInput(ValueError):
    pass


def hash_password(password):
    if not isinstance(password, str) or not password.strip():
        raise BadInput("Password is required.")
    salt = secrets.token_bytes(16)
    iterations = 600_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2-sha256${iterations}${salt.hex()}${digest.hex()}"


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
    if t == "password":
        return hash_password(check_new_password(raw))
    if t in ("text", "email", "url") and len(v) > 255:
        raise BadInput(f"{col['label']} is too long.")
    if t == "email":
        v = v.lower()
        if not EMAIL_RE.match(v):
            raise BadInput(f"{col['label']} must be a valid email address.")
    if t == "url" and not re.match(r"https?://\S+$", v):
        raise BadInput(f"{col['label']} must be a web link starting with http:// or https://.")
    if t == "datetime":
        try:
            return datetime.strptime(v.replace("T", " ")[:16], "%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M:00")
        except ValueError:
            raise BadInput(f"{col['label']} must be a date and time.")
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
        
        /* Auth */
        .user-chip { display: none; align-items: center; gap: 0.6rem; background: rgba(255,255,255,0.18); padding: 0.35rem 0.5rem 0.35rem 0.9rem; border-radius: 20px; font-size: 0.85rem; font-weight: 700; }
        body.authed .user-chip { display: flex; }
        .user-chip .role-badge { background: white; color: var(--primary-dark); border-radius: 10px; padding: 0.1rem 0.5rem; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.04em; }
        .chip-btn { background: rgba(0,0,0,0.25); color: white; border: none; border-radius: 14px; padding: 0.3rem 0.7rem; font-size: 0.75rem; font-weight: 700; cursor: pointer; }
        .chip-btn:hover { background: rgba(0,0,0,0.4); }
        body:not(.authed) .tabs, body:not(.authed) main { display: none; }
        body.non-admin .tabs { display: none; }
        body.non-admin main > :not(#viewAccount):not(#alertBox) { display: none !important; }
        body.non-admin .admin-only { display: none !important; }
        .auth-tabs { display: flex; gap: 0.3rem; }
        .auth-tab { border: none; background: #e2e8f0; color: var(--text); padding: 0.4rem 0.9rem; border-radius: 6px; font-weight: 700; font-size: 0.85rem; cursor: pointer; }
        .auth-tab.active { background: var(--primary); color: white; }
        .auth-error { background: #fef2f2; border-left: 4px solid var(--danger); color: #7f1d1d; padding: 0.7rem 0.9rem; border-radius: 6px; font-weight: 600; font-size: 0.9rem; }
        #authModal { z-index: 2000; }
        #authModal .modal-body > div { display: flex; flex-direction: column; gap: 1.15rem; }
        #viewAccount { display: none; padding: 2rem; }
        body.non-admin #viewAccount { display: block; }
        .navbar { flex-wrap: wrap; gap: 0.75rem; }

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
        .sql-code { color: #a5f3fc; white-space: pre-wrap; line-height: 1.6; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.85rem; }

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
        body:not(.show-sql) .sql-only { display: none !important; }   /* technical details, behind "Show SQL" */

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

        /* Reports */
        .report-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 0.75rem; padding: 1.1rem 1.5rem; }
        .report-card { text-align: left; background: white; border: 1px solid var(--border); border-radius: 10px; padding: 0.8rem 0.95rem; cursor: pointer; font-family: inherit; color: var(--text); }
        .report-card:hover { border-color: var(--primary); }
        .report-card.active { border-color: var(--primary); background: var(--primary-light); box-shadow: 0 0 0 2px rgba(27,94,32,0.15); }
        .report-card strong { display: block; font-size: 0.92rem; margin-bottom: 0.4rem; }
        .tag { display: inline-block; background: #eef2ff; color: #3730a3; border-radius: 10px; padding: 1px 8px; font-size: 0.7rem; font-weight: 700; margin: 0 0.25rem 0.25rem 0; }
        .bar-chart { padding: 1rem 1.5rem; border-bottom: 1px solid var(--border); display: flex; flex-direction: column; gap: 0.45rem; }
        .bar-chart h4 { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 0.2rem; }
        .bar-row { display: grid; grid-template-columns: minmax(90px, 220px) 1fr auto; gap: 0.7rem; align-items: center; font-size: 0.83rem; }
        .bar-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .bar-track { background: #f1f5f9; border-radius: 4px; height: 16px; }
        .bar-fill { background: var(--primary); border-radius: 4px; height: 100%; min-width: 2px; }
        .bar-value { font-weight: 700; min-width: 80px; text-align: right; }
        .report-total { font-size: 0.85rem; color: var(--text-muted); font-weight: 600; text-align: right; }
        .report-total strong { display: block; font-size: 1.35rem; color: var(--text); }
        td.num, th.num { text-align: right; }
        .obj-type { font-size: 0.7rem; font-weight: 800; padding: 2px 8px; border-radius: 10px; text-transform: uppercase; }
        .obj-view { background: #e0f2fe; color: #075985; }
        .obj-trigger { background: #fef3c7; color: #92400e; }
        .obj-index { background: #f1f5f9; color: #334155; }
        .obj-sql { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.75rem; white-space: pre-wrap; color: #334155; margin: 0; max-height: 9.5em; overflow-y: auto; }
    </style>
</head>
<body>

<header class="navbar">
    <div class="brand">
        <span style="font-size: 2rem;">🌿</span>
        <div>
            <h1>Landscaping AI Estimator Management Portal</h1>
            <p>CS 4604 Group 6 &bull; Virginia Tech &bull; __DATABASE_LABEL__</p>
        </div>
    </div>
    <div class="tabs">
        <button class="tab-btn active" id="tabCust" onclick="switchView('customers')">👥 Customers</button>
        <button class="tab-btn" id="tabProp" onclick="switchView('properties')">🏡 Properties</button>
        <button class="tab-btn" id="tabWf" onclick="switchView('workflow')">📋 Projects &amp; Billing</button>
        <button class="tab-btn" id="tabMg" onclick="switchView('manage')">🧰 Contractors &amp; More</button>
        <button class="tab-btn" id="tabRep" onclick="switchView('reports')">📊 Reports</button>
    </div>
    <div class="status-badge">
        <div class="dot"></div>
        <span>Database: <code>__DATABASE_LABEL__</code></span>
    </div>
    <div class="user-chip">
        <span id="chipName"></span><span class="role-badge" id="chipRole"></span>
        <button class="chip-btn" id="sqlToggle" onclick="toggleSql()">Show SQL</button>
        <button class="chip-btn" onclick="openModalById('pwModal')">Change password</button>
        <button class="chip-btn" id="chipAddAdmin" onclick="openModalById('adminModal')">Add admin</button>
        <button class="chip-btn" onclick="logout()">Log out</button>
    </div>
</header>

<main class="container">

    <div id="viewAccount" class="card">
        <h2 style="font-size: 1.4rem; margin-bottom: 0.5rem;">Welcome, <span id="acctName"></span></h2>
        <p style="color: var(--text-muted); margin-bottom: 1rem;">You are logged in as a <strong id="acctRole"></strong> (<span id="acctLogin"></span>). Use <strong>Change password</strong> or <strong>Log out</strong> in the top bar.</p>
        <p style="color: var(--text-muted);">The management tables are available to administrators only.</p>
    </div>

    <!-- Live Alerts -->
    <div id="alertBox" class="alert hidden"></div>

    <!-- SQL Reflection Box -->
    <div class="sql-box sql-only" id="sqlBox">
        <div class="sql-header">
            <span>Database Query Log</span>
            <span id="sqlTimestamp">Ready</span>
        </div>
        <div class="sql-code" id="sqlCode">-- __DATABASE_LABEL__
Waiting for a database query.</div>
    </div>

    <!-- Stats -->
    <div class="stat-grid">
        <div class="stat-card">
            <div class="stat-icon">👥</div>
            <div class="stat-info">
                <h3 id="statCustomerCount">20</h3>
                <p>Customers</p>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">🏡</div>
            <div class="stat-info">
                <h3 id="statPropertyCount">20</h3>
                <p>Properties</p>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">🚜</div>
            <div class="stat-info">
                <h3 id="statContractorCount">20</h3>
                <p>Contractors</p>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">📋</div>
            <div class="stat-info">
                <h3 id="statRequestCount">20</h3>
                <p>Project requests</p>
            </div>
        </div>
    </div>

    <!-- VIEW 1: CUSTOMERS -->
    <div id="viewCustomers" class="card">
        <div class="card-header">
            <div>
                <div class="card-title">Customers</div>
                <div class="card-sub">Homeowner accounts and their subscription plans. Search, add, edit or remove a customer.</div>
            </div>
            <div class="header-actions">
                <input type="search" id="custSearch" class="search-input" placeholder="Search name, email or phone..." oninput="onSearch(loadCustomers)">
                <button class="btn btn-primary" onclick="openCustomerModal()">+ Add customer</button>
            </div>
        </div>
        <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Phone</th>
                        <th>Subscription plan</th>
                        <th style="text-align: right;">Actions</th>
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
                <div class="card-title">Properties</div>
                <div class="card-sub">Every property on file and the customer who owns it.</div>
            </div>
            <div class="header-actions">
                <input type="search" id="propSearch" class="search-input" placeholder="Search address or lot size..." oninput="onSearch(loadProperties)">
                <button class="btn btn-primary" onclick="openPropertyModal()">+ Add property</button>
            </div>
        </div>
        <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Address</th>
                        <th>Lot size</th>
                        <th>Owner</th>
                        <th style="text-align: right;">Actions</th>
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
                <div class="card-title" id="wfGroupTitle">Project Workflow: Request &rarr; Estimate &rarr; Quote &rarr; Job &rarr; Invoice &rarr; Payment</div>
                <div class="card-sub" id="wfGroupSub">Follow a project from the customer's request to the final payment. Pick a step below, then use the green button on a row to add the next step for it.</div>
            </div>
        </div>
        <div class="wf-steps" id="wfSteps"></div>
        <div class="card-header">
            <div>
                <div class="card-title" id="wfTitle"></div>
                <div class="card-sub" id="wfKeys"></div>
            </div>
            <div class="header-actions">
                <input type="search" id="wfSearch" class="search-input" placeholder="Search..." oninput="onSearch(loadWorkflow)">
                <button class="btn btn-primary" id="wfInsertBtn" onclick="openRowModal(wfTable)">+ Insert</button>
            </div>
        </div>
        <div style="overflow-x: auto;" id="wfTable"></div>
    </div>

    <!-- VIEW 2c: REPORTS (multi-table queries, views, triggers, indexes) -->
    <div id="viewReports" class="hidden">
        <div class="card">
            <div class="card-header">
                <div>
                    <div class="card-title">Business reports</div>
                    <div class="card-sub">Statistics on the whole business. Pick a report to see a chart and the numbers.</div>
                </div>
            </div>
            <div class="report-grid" id="reportList"></div>
        </div>
        <div class="card">
            <div class="card-header">
                <div>
                    <div class="card-title" id="reportTitle">Pick a report</div>
                    <div class="card-sub" id="reportDesc"></div>
                </div>
                <div class="report-total" id="reportTotal"></div>
            </div>
            <div id="reportChart"></div>
            <div style="overflow-x: auto;" id="reportTable"></div>
        </div>
        <div class="card sql-only">
            <div class="card-header">
                <div>
                    <div class="card-title">Database Objects: Views, Triggers &amp; Indexes</div>
                    <div class="card-sub">Read from the database catalog.</div>
                </div>
            </div>
            <div style="overflow-x: auto;" id="dbObjects"></div>
        </div>
    </div>

</main>

<!-- INSERT CUSTOMER MODAL -->
<div class="modal-bg" id="customerModal">
    <div class="modal">
        <div class="modal-head">
            <h3 id="customerModalTitle" style="font-size: 1.15rem; font-weight: 800; color: var(--primary);">➕ Add customer</h3>
            <button onclick="closeCustomerModal()" style="border: none; background: none; font-size: 1.3rem; cursor: pointer; color: var(--text-muted);">✕</button>
        </div>
        <div class="modal-body">
            <div class="form-row">
                <label>Customer Full Name *</label>
                <input type="text" id="custName" required>
            </div>
            <div class="form-row">
                <label>Email Address *</label>
                <input type="email" id="custEmail" required>
            </div>
            <div class="form-row">
                <label>Phone Number *</label>
                <input type="tel" id="custPhone" required>
            </div>
            <div class="form-row">
                <label>Subscription plan</label>
                <select id="custPlan">
                </select>
            </div>
            <div class="form-row" id="custPassRow">
                <label>Password * (at least 8 characters)</label>
                <input type="password" id="custPass" autocomplete="new-password" required>
            </div>
        </div>
        <div class="modal-foot">
            <button class="btn btn-secondary" onclick="closeCustomerModal()">Cancel</button>
            <button class="btn btn-primary" id="customerSubmitBtn" onclick="submitCustomerForm()">Add customer</button>
        </div>
    </div>
</div>

<!-- DELETE CONFIRMATION MODAL -->
<div class="modal-bg" id="deleteConfirmModal">
    <div class="confirm-dialog">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">⚠️</div>
        <h3>Confirm delete</h3>
        <p id="deleteConfirmText"></p>
        <div style="display: flex; justify-content: center; gap: 1rem;">
            <button class="btn btn-secondary" onclick="closeDeleteModal()">Cancel</button>
            <button class="btn btn-danger" style="padding: 0.6rem 1.2rem; font-size: 0.9rem;" onclick="confirmExecuteDelete()">Delete</button>
        </div>
    </div>
</div>

<!-- INSERT PROPERTY MODAL -->
<div class="modal-bg" id="propertyModal">
    <div class="modal">
        <div class="modal-head">
            <h3 id="propertyModalTitle" style="font-size: 1.15rem; font-weight: 800; color: var(--primary);">➕ Add property</h3>
            <button onclick="closePropertyModal()" style="border: none; background: none; font-size: 1.3rem; cursor: pointer;">✕</button>
        </div>
        <div class="modal-body">
            <div class="form-row">
                <label>Property Address *</label>
                <input type="text" id="propAddress" required>
            </div>
            <div class="form-row">
                <label>Lot Size (Sq Ft) *</label>
                <input type="number" id="propSqft" min="1" required>
            </div>
            <div class="form-row">
                <label>Owner</label>
                <select id="propCustomerId"></select>
            </div>
        </div>
        <div class="modal-foot">
            <button class="btn btn-secondary" onclick="closePropertyModal()">Cancel</button>
            <button class="btn btn-primary" id="propertySubmitBtn" onclick="submitPropertyForm()">Add property</button>
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

<!-- ============ AUTH: LOGIN / SIGN UP ============ -->
<div class="modal-bg active" id="authModal">
    <div class="modal">
        <div class="modal-head">
            <h3 style="font-size: 1.15rem; font-weight: 800; color: var(--primary);">🌿 Landscaping AI Estimator</h3>
            <div class="auth-tabs">
                <button class="auth-tab active" id="authTabLogin" onclick="authMode('login')">Log in</button>
                <button class="auth-tab" id="authTabSignup" onclick="authMode('signup')">Sign up</button>
            </div>
        </div>
        <div class="modal-body">
            <div id="authError" class="auth-error hidden"></div>

            <div id="loginFields">
                <div class="form-row">
                    <label>I am a</label>
                    <select id="loginRole" onchange="syncLoginRole()">
                        <option value="customer">Customer</option>
                        <option value="contractor">Contractor</option>
                        <option value="admin">Administrator</option>
                    </select>
                </div>
                <div class="form-row">
                    <label id="loginIdentLabel">Email</label>
                    <input type="text" id="loginIdent" autocomplete="username">
                </div>
                <div class="form-row">
                    <label>Password</label>
                    <input type="password" id="loginPass" autocomplete="current-password">
                </div>
            </div>

            <div id="signupFields" class="hidden">
                <div class="form-row">
                    <label>Account type</label>
                    <select id="signRole" onchange="syncSignupRole()">
                        <option value="customer">Customer (homeowner)</option>
                        <option value="contractor">Contractor</option>
                    </select>
                </div>
                <div class="form-row" id="signNameRow">
                    <label>Full name *</label>
                    <input type="text" id="signName" autocomplete="name">
                </div>
                <div class="form-row hidden" id="signBizRow">
                    <label>Business name *</label>
                    <input type="text" id="signBiz" autocomplete="organization">
                </div>
                <div class="form-row hidden" id="signContactRow">
                    <label>Contact name *</label>
                    <input type="text" id="signContact" autocomplete="name">
                </div>
                <div class="form-row">
                    <label>Email *</label>
                    <input type="email" id="signEmail" autocomplete="email">
                </div>
                <div class="form-row">
                    <label>Phone number *</label>
                    <input type="tel" id="signPhone" autocomplete="tel">
                </div>
                <div class="form-row" id="signPlanRow">
                    <label>Subscription plan</label>
                    <select id="signPlan"></select>
                </div>
                <div class="form-row">
                    <label>Password * (at least 8 characters)</label>
                    <input type="password" id="signPass" autocomplete="new-password">
                </div>
                <div class="form-row">
                    <label>Confirm password *</label>
                    <input type="password" id="signPass2" autocomplete="new-password">
                </div>
            </div>
        </div>
        <div class="modal-foot">
            <button class="btn btn-primary" id="authSubmit" onclick="submitAuth()">Log in</button>
        </div>
    </div>
</div>

<!-- CHANGE PASSWORD MODAL -->
<div class="modal-bg" id="pwModal">
    <div class="modal">
        <div class="modal-head">
            <h3 style="font-size: 1.15rem; font-weight: 800; color: var(--primary);">🔑 Change Password</h3>
            <button onclick="closeModalById('pwModal')" style="border: none; background: none; font-size: 1.3rem; cursor: pointer; color: var(--text-muted);">✕</button>
        </div>
        <div class="modal-body">
            <div id="pwError" class="auth-error hidden"></div>
            <div class="form-row"><label>Current password</label><input type="password" id="pwCurrent" autocomplete="current-password"></div>
            <div class="form-row"><label>New password (at least 8 characters)</label><input type="password" id="pwNew" autocomplete="new-password"></div>
            <div class="form-row"><label>Confirm new password</label><input type="password" id="pwNew2" autocomplete="new-password"></div>
        </div>
        <div class="modal-foot">
            <button class="btn btn-secondary" onclick="closeModalById('pwModal')">Cancel</button>
            <button class="btn btn-primary" onclick="submitPasswordChange()">Update Password</button>
        </div>
    </div>
</div>

<!-- ADD ADMIN MODAL -->
<div class="modal-bg" id="adminModal">
    <div class="modal">
        <div class="modal-head">
            <h3 style="font-size: 1.15rem; font-weight: 800; color: var(--primary);">🛡️ Add Administrator</h3>
            <button onclick="closeModalById('adminModal')" style="border: none; background: none; font-size: 1.3rem; cursor: pointer; color: var(--text-muted);">✕</button>
        </div>
        <div class="modal-body">
            <div id="adminError" class="auth-error hidden"></div>
            <div class="form-row"><label>Username</label><input type="text" id="newAdminUser" autocomplete="off"></div>
            <div class="form-row"><label>Password (at least 8 characters)</label><input type="password" id="newAdminPass" autocomplete="new-password"></div>
            <div class="form-row"><label>Confirm password</label><input type="password" id="newAdminPass2" autocomplete="new-password"></div>
        </div>
        <div class="modal-foot">
            <button class="btn btn-secondary" onclick="closeModalById('adminModal')">Cancel</button>
            <button class="btn btn-primary" onclick="submitNewAdmin()">Create Administrator</button>
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

async function getJson(url, body) {
    const opts = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
    const res = await fetch(url, opts);
    const data = await res.json();
    if (res.status === 401) { showAuth(); throw new Error(data.error || 'Please log in.'); }
    if (!res.ok && body === undefined) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
}

// ---------- Authentication ----------
let currentUser = null;
let authModeNow = 'login';
let portalStarted = false;

async function authPost(url, body) {
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
    let data = {};
    try { data = await res.json(); } catch (e) { data = { status: 'error', error: 'Unexpected server response.' }; }
    return data;
}

function showAuthError(id, msg) {
    const box = document.getElementById(id);
    box.textContent = msg;
    box.classList.remove('hidden');
}
function clearAuthErrors() {
    ['authError', 'pwError', 'adminError'].forEach(id => document.getElementById(id).classList.add('hidden'));
}
function closeModalById(id) { document.getElementById(id).classList.remove('active'); }
function openModalById(id) { clearAuthErrors(); document.getElementById(id).classList.add('active'); }

function showAuth() {
    currentUser = null;
    document.body.classList.remove('authed', 'non-admin');
    openModalById('authModal');
}

function authMode(mode) {
    authModeNow = mode;
    clearAuthErrors();
    document.getElementById('authTabLogin').classList.toggle('active', mode === 'login');
    document.getElementById('authTabSignup').classList.toggle('active', mode === 'signup');
    document.getElementById('loginFields').classList.toggle('hidden', mode !== 'login');
    document.getElementById('signupFields').classList.toggle('hidden', mode !== 'signup');
    document.getElementById('authSubmit').textContent = mode === 'login' ? 'Log in' : 'Create account';
    if (mode === 'signup') loadSignupPlans();
}

function syncLoginRole() {
    const admin = document.getElementById('loginRole').value === 'admin';
    document.getElementById('loginIdentLabel').textContent = admin ? 'Username' : 'Email';
    document.getElementById('loginIdent').autocomplete = 'username';
}

function syncSignupRole() {
    const contractor = document.getElementById('signRole').value === 'contractor';
    document.getElementById('signNameRow').classList.toggle('hidden', contractor);
    document.getElementById('signPlanRow').classList.toggle('hidden', contractor);
    document.getElementById('signBizRow').classList.toggle('hidden', !contractor);
    document.getElementById('signContactRow').classList.toggle('hidden', !contractor);
}

async function loadSignupPlans() {
    const sel = document.getElementById('signPlan');
    if (sel.options.length) return;
    try {
        const res = await fetch('/api/plans');
        const plans = await res.json();
        plans.forEach(p => {
            const o = document.createElement('option');
            o.value = p.value;
            o.textContent = p.label;
            sel.appendChild(o);
        });
    } catch (e) { /* the server falls back to plan 1 */ }
}

async function submitAuth() {
    clearAuthErrors();
    let data;
    if (authModeNow === 'login') {
        data = await authPost('/api/login', {
            role: document.getElementById('loginRole').value,
            identifier: document.getElementById('loginIdent').value,
            password: document.getElementById('loginPass').value
        });
    } else {
        const role = document.getElementById('signRole').value;
        const pass = document.getElementById('signPass').value;
        if (pass !== document.getElementById('signPass2').value) {
            showAuthError('authError', 'Passwords do not match.');
            return;
        }
        const body = {
            role: role,
            email: document.getElementById('signEmail').value,
            phone_number: document.getElementById('signPhone').value,
            password: pass
        };
        if (role === 'customer') {
            body.name = document.getElementById('signName').value;
            body.plan_id = document.getElementById('signPlan').value || 1;
        } else {
            body.business_name = document.getElementById('signBiz').value;
            body.contact_name = document.getElementById('signContact').value;
        }
        data = await authPost('/api/signup', body);
    }
    if (data.status !== 'success') {
        showAuthError('authError', data.error || 'Something went wrong.');
        return;
    }
    ['loginPass', 'signPass', 'signPass2'].forEach(id => document.getElementById(id).value = '');
    applyUser(data.user);
}

function applyUser(user) {
    currentUser = user;
    closeModalById('authModal');
    document.body.classList.add('authed');
    document.body.classList.toggle('non-admin', user.role !== 'admin');
    document.getElementById('chipName').textContent = user.name;
    document.getElementById('chipRole').textContent = user.role;
    document.getElementById('chipAddAdmin').classList.toggle('hidden', user.role !== 'admin');
    document.getElementById('acctName').textContent = user.name;
    document.getElementById('acctRole').textContent = user.role;
    document.getElementById('acctLogin').textContent = user.login;
    if (user.role === 'admin') {
        if (!portalStarted) { portalStarted = true; handleUrlState(); }
    } else {
        window.location.href = '/' + user.role;   // customers and contractors have their own page
    }
}

async function authInit() {
    syncLoginRole();
    syncSignupRole();
    let data = {};
    try { data = await (await fetch('/api/me')).json(); } catch (e) { data = {}; }
    if (data.authenticated) applyUser(data.user); else showAuth();
}

async function logout() {
    await authPost('/api/logout');
    window.location.href = '/';
}

async function submitPasswordChange() {
    clearAuthErrors();
    const next = document.getElementById('pwNew').value;
    if (next !== document.getElementById('pwNew2').value) {
        showAuthError('pwError', 'New passwords do not match.');
        return;
    }
    const data = await authPost('/api/change_password', { current_password: document.getElementById('pwCurrent').value, new_password: next });
    if (data.status !== 'success') {
        if (data.code === 401) { showAuth(); return; }
        showAuthError('pwError', data.error || 'Could not change the password.');
        return;
    }
    ['pwCurrent', 'pwNew', 'pwNew2'].forEach(id => document.getElementById(id).value = '');
    closeModalById('pwModal');
    showAlert('success', '<strong>Password updated.</strong> Your other sessions were logged out.');
}

async function submitNewAdmin() {
    clearAuthErrors();
    const pass = document.getElementById('newAdminPass').value;
    if (pass !== document.getElementById('newAdminPass2').value) {
        showAuthError('adminError', 'Passwords do not match.');
        return;
    }
    const data = await authPost('/api/admins', { username: document.getElementById('newAdminUser').value, password: pass });
    if (data.status !== 'success') {
        showAuthError('adminError', data.error || 'Could not create the administrator.');
        return;
    }
    const name = document.getElementById('newAdminUser').value.trim();
    ['newAdminUser', 'newAdminPass', 'newAdminPass2'].forEach(id => document.getElementById(id).value = '');
    closeModalById('adminModal');
    showAlert('success', '<strong>Administrator created.</strong> ' + name.replace(/[<>&]/g, '') + ' can now log in as Admin.');
}

document.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    if (document.getElementById('authModal').classList.contains('active')) submitAuth();
    else if (document.getElementById('pwModal').classList.contains('active')) submitPasswordChange();
    else if (document.getElementById('adminModal').classList.contains('active')) submitNewAdmin();
});

// ---------- Loading ----------
async function loadMeta() {
    if (!schema.length) schema = await getJson('/api/schema');
    fkOptions = await getJson('/api/options');
    tableCounts = await getJson('/api/counts');
    fillSelect(document.getElementById('custPlan'), fkOptions.SUBSCRIPTION_PLAN, false);
    fillSelect(document.getElementById('propCustomerId'), fkOptions.CUSTOMER, false);
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
        showAlert('danger', escapeHtml(e.message));
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
        tbody.innerHTML = '<tr><td colspan="5" class="empty">No customers match this search.</td></tr>';
        return;
    }
    customersData.forEach(c => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${escapeHtml(c.name)}</strong></td>
            <td>${escapeHtml(c.email)}</td>
            <td>${escapeHtml(c.phone_number)}</td>
            <td><span style="background: #e0f2fe; color: #0369a1; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 0.75rem;">${escapeHtml(fkText('SUBSCRIPTION_PLAN', c.plan_id))}</span></td>
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
        tbody.innerHTML = '<tr><td colspan="4" class="empty">No properties match this search.</td></tr>';
        return;
    }
    propertiesData.forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
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
    ['viewCustomers', 'viewProperties', 'viewWorkflow', 'viewReports'].forEach(id => document.getElementById(id).classList.add('hidden'));

    if (view === 'customers') {
        document.getElementById('tabCust').classList.add('active');
        document.getElementById('viewCustomers').classList.remove('hidden');
    } else if (view === 'properties') {
        document.getElementById('tabProp').classList.add('active');
        document.getElementById('viewProperties').classList.remove('hidden');
    } else if (view === 'workflow' || view === 'manage') {
        // Both tabs share one screen; "manage" lists contractors, site visits, photos and plans.
        wfGroup = view;
        document.getElementById(view === 'manage' ? 'tabMg' : 'tabWf').classList.add('active');
        document.getElementById('viewWorkflow').classList.remove('hidden');
        const [title, sub] = WF_GROUPS[view];
        document.getElementById('wfGroupTitle').innerHTML = title;
        document.getElementById('wfGroupSub').innerHTML = sub;
        const cur = tcfg(wfTable);
        if (!cur || cur.group !== view) { wfTable = schema.find(s => s.group === view).table; document.getElementById('wfSearch').value = ''; }
        return loadWorkflow(true);
    } else if (view === 'reports') {
        document.getElementById('tabRep').classList.add('active');
        document.getElementById('viewReports').classList.remove('hidden');
        return loadReports();
    }
}

function openCustomerModal() {
    customerEditId = null;
    ['custName', 'custEmail', 'custPhone'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('custPlan').selectedIndex = 0;
    document.getElementById('custPass').value = '';
    document.getElementById('custPassRow').classList.remove('hidden');
    document.getElementById('customerModalTitle').innerText = '➕ Add customer';
    document.getElementById('customerSubmitBtn').innerText = 'Add customer';
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
    document.getElementById('customerModalTitle').innerText = `✏️ Edit ${c.name}`;
    document.getElementById('customerSubmitBtn').innerText = 'Save changes';
    document.getElementById('customerModal').classList.add('active');
}
function closeCustomerModal() { document.getElementById('customerModal').classList.remove('active'); }

function openPropertyModal() {
    propertyEditId = null;
    document.getElementById('propAddress').value = '';
    document.getElementById('propSqft').value = '';
    document.getElementById('propertyModalTitle').innerText = '➕ Add property';
    document.getElementById('propertySubmitBtn').innerText = 'Add property';
    document.getElementById('propertyModal').classList.add('active');
}
function editProperty(id) {
    const p = propertiesData.find(x => x.property_id === id);
    if (!p) return;
    propertyEditId = id;
    document.getElementById('propAddress').value = p.address;
    document.getElementById('propSqft').value = p.sqft;
    document.getElementById('propCustomerId').value = String(p.customer_id);
    document.getElementById('propertyModalTitle').innerText = `✏️ Edit ${p.address}`;
    document.getElementById('propertySubmitBtn').innerText = 'Save changes';
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
    if (data.trigger_note) successText += ' <br><span style="font-weight: 500;">⚡ The invoice is now fully paid and was marked Paid automatically.</span>';
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
    document.getElementById('deleteConfirmText').innerHTML = `Delete customer <strong>${escapeHtml(name)}</strong>?<br><br><span style="color: var(--danger); font-size: 0.85rem; font-weight: 600;">Their properties, project requests, quotes, jobs, invoices and payments are deleted too.</span>`;
    document.getElementById('deleteConfirmModal').classList.add('active');
}
function promptDeleteCustomer(id) {
    const c = customersData.find(x => x.customer_id === id);
    promptDelete(id, c ? c.name : '');
}
function promptDeleteProperty(id) {
    const p = propertiesData.find(x => x.property_id === id);
    askConfirm(`Delete the property at <strong>${escapeHtml(p ? p.address : '')}</strong>?<br><br><span style="color: var(--danger); font-size: 0.85rem; font-weight: 600;">Its project requests and everything that came from them are deleted too.</span>`, async () => {
        const data = await getJson('/api/rows/PROPERTY/delete', { id });
        handleWrite(data, `🗑️ Property ${escapeHtml(p ? p.address : '')} deleted.`);
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
        handleWrite(data, `🗑️ Customer ${escapeHtml(pendingDeleteName)} deleted.`);
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
    if (!password.trim()) {
        showAlert('danger', 'Password is required.');
        return;
    }

    try {
        const data = await getJson('/api/insert_customer', { name, email, phone_number: phone, plan_id, password });
        handleWrite(data, `✅ Customer ${escapeHtml(name)} added.`, closeCustomerModal);
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
        handleWrite(data, `✏️ Customer ${escapeHtml(values.name)} updated.`, closeCustomerModal);
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
        handleWrite(data, `✅ Property ${escapeHtml(address)} added.`, closePropertyModal);
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
        handleWrite(data, `✏️ Property ${escapeHtml(values.address)} updated.`, closePropertyModal);
        await loadData();
    } catch (e) {
        showAlert('danger', 'Error updating property: ' + e);
    }
}

// ---------- Reports ----------
let reportList = [];
let currentReport = null;
const MONEY_COLS = /(price|revenue|expenses|profit|amount|balance|owed|estimate|gap$)/;

async function loadReports() {
    if (!reportList.length) reportList = await getJson('/api/reports');
    if (!currentReport) currentReport = reportList[0].id;
    await runReport(currentReport);
    await loadDbObjects();
}

function renderReportList() {
    document.getElementById('reportList').innerHTML = reportList.map(r => `
        <button class="report-card ${r.id === currentReport ? 'active' : ''}" onclick="runReport('${r.id}')">
            <strong>${escapeHtml(r.title)}</strong>
            <span class="sql-only">${r.tags.map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}</span>
            <span class="card-sub" style="display:block">${escapeHtml(r.description)}</span>
        </button>`).join('');
}

function fmtReportCell(col, v) {
    if (v === null || v === undefined) return '<span class="muted">—</span>';
    if (typeof v === 'number' && col.endsWith('_pct')) return `${v > 0 && col.startsWith('gap') ? '+' : ''}${v.toFixed(1)}%`;
    if (typeof v === 'number' && MONEY_COLS.test(col)) return (v < 0 ? '-$' : '$') + Math.abs(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (col.endsWith('status')) return `<span class="status-pill status-${String(v).toLowerCase().replace(/[^a-z]+/g, '-')}">${escapeHtml(v)}</span>`;
    if (typeof v === 'number') return v.toLocaleString();
    return escapeHtml(v);
}

async function runReport(id) {
    currentReport = id;
    renderReportList();
    const meta = reportList.find(r => r.id === id);
    const data = await getJson('/api/report/' + id);
    updateSqlBox(data.sql, data.timestamp);
    document.getElementById('reportTitle').innerText = meta.title;
    document.getElementById('reportDesc').innerText = meta.description;
    // Show a total for the first money column, when there is one
    let moneyIdx = data.columns.findIndex(c => /^(total_|balance)/.test(c) && MONEY_COLS.test(c));
    if (moneyIdx < 0) moneyIdx = data.columns.findIndex(c => MONEY_COLS.test(c) && !c.endsWith('_pct') && c !== 'gap' && c !== 'ai_estimate' && c !== 'quoted_price');
    const totalCol = moneyIdx >= 0 ? data.columns[moneyIdx] : null;
    document.getElementById('reportTotal').innerHTML = totalCol
        ? `<strong>${fmtReportCell(totalCol, data.rows.reduce((s, r) => s + Number(r[moneyIdx] || 0), 0))}</strong>total ${escapeHtml(totalCol.replace(/^total_/, '').replace(/_/g, ' '))} &bull; ${data.rows.length} rows`
        : `<strong>${data.rows.length}</strong>rows`;
    let html = '<table><thead><tr>' + data.columns.map(c => `<th>${escapeHtml(prettyCol(c))}</th>`).join('') + '</tr></thead><tbody>';
    if (!data.rows.length) html += `<tr><td colspan="${data.columns.length}" class="empty">No rows returned.</td></tr>`;
    data.rows.forEach(row => {
        html += '<tr>' + row.map((v, i) => `<td>${fmtReportCell(data.columns[i], v)}</td>`).join('') + '</tr>';
    });
    document.getElementById('reportTable').innerHTML = html + '</tbody></table>';
    document.getElementById('reportChart').innerHTML = barChart(data, fmtReportCell);
}

// Horizontal bar chart from the report's chart: [labelColumn, valueColumn]
function barChart(data, fmt) {
    if (!data.chart || !data.rows.length) return '';
    const [labelCol, valueCol] = data.chart;
    const li = data.columns.indexOf(labelCol), vi = data.columns.indexOf(valueCol);
    if (li < 0 || vi < 0) return '';
    const max = Math.max(...data.rows.map(r => Math.abs(Number(r[vi]) || 0))) || 1;
    const nice = c => c.replace(/_/g, ' ');
    return `<div class="bar-chart"><h4>${escapeHtml(nice(valueCol))} by ${escapeHtml(nice(labelCol))}</h4>` +
        data.rows.slice(0, 15).map(r => {
            const pct = Math.max(0, (Number(r[vi]) || 0) / max * 100);
            return `<div class="bar-row"><span class="bar-label" title="${escapeHtml(r[li])}">${escapeHtml(r[li] ?? '—')}</span>
                <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
                <span class="bar-value">${fmt(valueCol, Number(r[vi]) || 0)}</span></div>`;
        }).join('') + '</div>';
}

async function loadDbObjects() {
    const objs = await getJson('/api/db_objects');
    let html = '<table><thead><tr><th>Type</th><th>Name</th><th>On Table</th><th>Definition</th></tr></thead><tbody>';
    objs.forEach(o => {
        html += `<tr><td><span class="obj-type obj-${o.type}">${o.type}</span></td><td><strong>${escapeHtml(o.name)}</strong></td><td><code>${escapeHtml(o.tbl_name)}</code></td><td><pre class="obj-sql">${escapeHtml(o.sql)}</pre></td></tr>`;
    });
    document.getElementById('dbObjects').innerHTML = html + '</tbody></table>';
}

// ---------- Project workflow ----------
function tcfg(table) { return schema.find(s => s.table === table); }
function fkText(ref, v) {
    if (v === null || v === undefined || v === '') return '-';
    const o = (fkOptions[ref] || []).find(o => String(o.value) === String(v));
    return o ? o.label : '(removed)';
}
function fmtCell(col, v) {
    if (v === null || v === undefined || v === '') return '<span class="muted">—</span>';
    if (col.type === 'fk') return `<span class="fk-pill">${escapeHtml(fkText(col.ref, v))}</span>`;
    if (col.money) return '$' + Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (col.name === 'status') return `<span class="status-pill status-${String(v).toLowerCase().replace(/[^a-z]+/g, '-')}">${escapeHtml(v)}</span>`;
    if (col.type === 'number') return Number(v).toLocaleString();
    if (col.type === 'datetime') return escapeHtml(String(v).replace('T', ' ').slice(0, 16));
    if (col.type === 'url' && (String(v).startsWith('http://') || String(v).startsWith('https://'))) return `<a href="${escapeHtml(v)}" target="_blank" rel="noopener noreferrer">View photo</a>`;
    return escapeHtml(v);
}

function renderWfSteps() {
    const steps = schema.filter(s => s.group === wfGroup);
    document.getElementById('wfSteps').innerHTML = steps.map((s, i) => `
        <button class="wf-step ${s.table === wfTable ? 'active' : ''}" onclick="selectWfTable('${s.table}')">
            <span style="font-size: 1.2rem;">${s.icon}</span>
            <span><strong>${s.label}</strong><small>${tableCounts[s.table] ?? 0} on file</small></span>
        </button>${i < steps.length - 1 && wfGroup === 'workflow' ? '<span class="wf-arrow">&rarr;</span>' : ''}`).join('');
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
    document.getElementById('wfTitle').innerHTML = `${cfg.icon} ${escapeHtml(cfg.label)}`;
    document.getElementById('wfKeys').innerHTML = escapeHtml(cfg.help || WF_HELP[cfg.table] || '');
    document.getElementById('wfInsertBtn').innerText = `+ Add ${cfg.singular.toLowerCase()}`;
    const next = cfg.next ? tcfg(cfg.next.table) : null;

    const shownCols = cfg.columns.filter(c => c.type !== 'password');
    let html = '<table><thead><tr>' +
        shownCols.map(c => `<th>${escapeHtml(c.label.replace(' ($)', '').replace(' (login)', ''))}</th>`).join('') +
        '<th style="text-align: right;">Actions</th></tr></thead><tbody>';
    if (!wfRows.length) html += `<tr><td colspan="${shownCols.length + 1}" class="empty">Nothing matches this search.</td></tr>`;
    wfRows.forEach(r => {
        const id = r[cfg.pk];
        html += '<tr>' +
            shownCols.map(c => `<td>${fmtCell(c, r[c.name])}</td>`).join('') +
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
    document.getElementById('rowModalTitle').innerText = row ? `✏️ Edit ${cfg.singular.toLowerCase()}` : `➕ Add ${cfg.singular.toLowerCase()}`;
    document.getElementById('rowSubmitBtn').innerText = row ? 'Save changes' : `Add ${cfg.singular.toLowerCase()}`;

    const body = document.getElementById('rowModalBody');
    body.innerHTML = '';
    cfg.columns.forEach(col => {
        const wrap = document.createElement('div');
        wrap.className = 'form-row';
        const label = document.createElement('label');
        const keepPassword = col.type === 'password' && rowEditId !== null;
        label.textContent = col.label + (keepPassword ? ' (leave blank to keep the current one)' : col.nullable ? ' (optional)' : ' *');
        let input;
        if (col.type === 'fk' || col.type === 'select') {
            input = document.createElement('select');
            const opts = col.type === 'fk'
                ? (fkOptions[col.ref] || []).map(o => ({ value: o.value, text: o.label }))
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
            input.type = { number: 'number', date: 'date', datetime: 'datetime-local', password: 'password', email: 'email', url: 'url' }[col.type] || 'text';
            if (col.type === 'password') input.autocomplete = 'new-password';
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
        if (col.type === 'password') v = '';
        else if (row) v = row[col.name];
        else if (prefill && prefill[col.name] !== undefined) v = prefill[col.name];
        else if (col.default === 'today') v = today;
        else v = col.default;
        if (v !== null && v !== undefined && v !== '') input.value = col.type === 'datetime' ? String(v).replace(' ', 'T').slice(0, 16) : String(v);
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
        handleWrite(data, isEdit ? `✏️ ${cfg.singular} updated.` : `✅ ${cfg.singular} added.`, closeRowModal);
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
    askConfirm(`Delete this ${cfg.singular.toLowerCase()}?<br><br><span style="color: var(--danger); font-size: 0.85rem; font-weight: 600;">This also deletes ${cfg.cascade}.</span>`, async () => {
        const data = await getJson(`/api/rows/${table}/delete`, { id });
        handleWrite(data, `🗑️ ${cfg.singular} deleted.`);
        await loadData();
    });
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

async function handleUrlState() {
    try { if (localStorage.getItem('adminShowSql') === '1') toggleSql(); } catch (e) {}
    await loadData();
}

// Technical details (SQL log, report SQL tags, database objects) stay hidden unless asked for.
function toggleSql() {
    const on = document.body.classList.toggle('show-sql');
    document.getElementById('sqlToggle').textContent = on ? 'Hide SQL' : 'Show SQL';
    try { localStorage.setItem('adminShowSql', on ? '1' : '0'); } catch (e) {}
}

let wfGroup = 'workflow';
const WF_GROUPS = {
    workflow: ['Project Workflow: Request &rarr; Estimate &rarr; Quote &rarr; Job &rarr; Invoice &rarr; Payment',
               "Follow a project from the customer's request to the final payment. Pick a step below, then use the green button on a row to add the next step for it."],
    manage: ['Contractors, Site Visits, Photos &amp; Plans',
             'Add, edit or remove contractors, site visits, project photos and subscription plans.'],
};
const WF_HELP = {
    PROJECT_REQUEST: 'Work customers asked for on one of their properties.',
    AI_ESTIMATE: 'Automatic price estimates for each request.',
    CONTRACTOR_QUOTE: 'Prices contractors offered on an estimate. The customer accepts one.',
    JOB: 'Work scheduled from an accepted quote.',
    INVOICE: 'Bills sent to customers for their jobs.',
    PAYMENT: 'Money received against an invoice.',
};
const COL_WORDS = { avg: 'Average', min: 'Lowest', max: 'Highest', pct: '%', sqft: 'Sq Ft', ai: 'AI' };
const prettyCol = c => c.split('_').map(w => COL_WORDS[w] || (w.charAt(0).toUpperCase() + w.slice(1))).join(' ');

window.onload = authInit;
</script>

</body>
</html>
"""

def list_rows(table, q):
    cfg = TABLES[table]
    cols = [cfg["pk"]] + [c["name"] for c in cfg["columns"] if c["type"] != "password"]
    sql = f"SELECT {', '.join(cols)} FROM {table}"
    params = []
    if q:
        cast_type = "CHAR" if DB_HOST else "TEXT"
        # Search the columns listed in "search", or every non-FK column by default.
        searched = [c for c in cfg["columns"] if c["name"] in cfg.get("search", [])] or \
                   [c for c in cfg["columns"] if c["type"] not in ("fk", "password")]
        sql += " WHERE " + " OR ".join(
            f"CAST({c['name']} AS {cast_type}) LIKE ?" if c["type"] in ("number", "fk") else f"{c['name']} LIKE ?"
            for c in searched)
        params = [f"%{q}%"] * len(searched)
    sql += f" ORDER BY {cfg['pk']} ASC"
    with closing(get_conn()) as conn:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    shown = render_sql(sql, params) + f";\n-- {len(rows)} row(s) returned"
    return {"status": "success", "rows": rows, "sql": shown, "timestamp": now()}


def write_row(table, action, payload):
    cfg = TABLES[table]
    pk = cfg["pk"]
    if action == "delete":
        sql, params = f"DELETE FROM {table} WHERE {pk} = ?", [int(payload["id"])]
    else:
        given = dict(payload.get("values", {}))
        for c in cfg["columns"]:
            # On edit, an empty password box means "keep the current password".
            if c["type"] == "password" and action == "update" and not str(given.get(c["name"]) or "").strip():
                given.pop(c["name"], None)
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
    hidden = {i for i, c in enumerate(cols) if c["type"] == "password"} if action != "delete" else set()
    shown = render_sql(sql, [("••••••••" if i in hidden else p) for i, p in enumerate(params)]) + ";"
    conn = get_conn()
    try:
        invoice_id, before = None, None
        if table == "PAYMENT" and action != "delete":
            invoice_id = dict(zip((c["name"] for c in cols), values)).get("invoice_id")
            if invoice_id is None and action == "update":
                payment = conn.execute("SELECT invoice_id FROM PAYMENT WHERE payment_id = ?", (int(payload["id"]),)).fetchone()
                invoice_id = payment["invoice_id"] if payment else None
            if invoice_id is not None:
                row = conn.execute("SELECT status FROM INVOICE WHERE invoice_id = ?", (invoice_id,)).fetchone()
                before = row["status"] if row else None
        cur = conn.execute(sql, params)
        result = {"status": "success", "affected": cur.rowcount, "timestamp": now()}
        if action == "insert":
            result["new_id"] = cur.lastrowid
        result["sql"] = shown + f"\n-- Query OK, {cur.rowcount} row(s) affected" + (
            f" | Generated PK {pk} = {cur.lastrowid}" if action == "insert" else "")
        if invoice_id is not None:
            row = conn.execute("SELECT status FROM INVOICE WHERE invoice_id = ?", (invoice_id,)).fetchone()
            after = row["status"] if row else None
            if after != before:
                trigger = f"trg_payment_{action}_mark_paid"
                note = f"Trigger {trigger} fired: INVOICE #{invoice_id} status '{before}' -> '{after}'."
                result["trigger_note"] = note
                result["sql"] += f"\n-- {note}"
        conn.commit()
        return result
    except DB_ERRORS as e:
        msg = str(e)
        if "UNIQUE" in msg.upper() or "DUPLICATE" in msg.upper():
            msg = "That email is already used by another account."
        return {"status": "error", "error": msg, "sql": shown + f"\n-- ERROR: {e}", "timestamp": now()}
    finally:
        conn.close()


# ==============================================================================
# AUTHENTICATION: accounts, sessions, lockout
# Roles: customer (CUSTOMER.email), contractor (CONTRACTOR.email), admin (ADMIN.username)
# ==============================================================================
COOKIE_NAME = "landscaping_session"
SESSION_TTL = 8 * 3600          # seconds
MAX_FAILS = 5                   # failed logins before a lockout
LOCK_SECONDS = 300
MIN_PASSWORD = 8
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")

ROLES = {
    "customer":   {"table": "CUSTOMER",   "pk": "customer_id",   "ident": "email",    "display": "name"},
    "contractor": {"table": "CONTRACTOR", "pk": "contractor_id", "ident": "email",    "display": "business_name"},
    "admin":      {"table": "ADMIN",      "pk": "admin_id",      "ident": "username", "display": "username"},
}

SESSIONS = {}   # token -> {"role", "id", "expires"}   (in memory: restarting the server logs everyone out)
FAILS = {}      # "role:identifier" -> [failed_count, locked_until]
_DUMMY_HASH = None


class AuthError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def ensure_auth_schema():
    """Creates the ADMIN table on databases built before it existed (no-op otherwise)."""
    pk = "INTEGER PRIMARY KEY AUTOINCREMENT" if not DB_HOST else "INT AUTO_INCREMENT PRIMARY KEY"
    engine = " ENGINE=InnoDB" if DB_HOST else ""
    with closing(get_conn()) as conn:
        conn.execute(f"""CREATE TABLE IF NOT EXISTS ADMIN (
            admin_id {pk},
            username VARCHAR(50) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            created_by INT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_admin_creator FOREIGN KEY (created_by)
                REFERENCES ADMIN(admin_id) ON UPDATE CASCADE ON DELETE SET NULL
        ){engine}""")
        conn.commit()


def verify_password(password, stored):
    """Checks a password against 'pbkdf2-sha256$iterations$salt_hex$digest_hex' in constant time."""
    try:
        scheme, iterations, salt_hex, digest_hex = stored.split("$")
        if scheme != "pbkdf2-sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (AttributeError, ValueError):
        return False


def check_new_password(password):
    if not isinstance(password, str) or len(password) < MIN_PASSWORD:
        raise BadInput(f"Password must be at least {MIN_PASSWORD} characters.")
    if len(password) > 200:
        raise BadInput("Password is too long.")
    return password


def clean(payload, key, label, maxlen=100):
    v = payload.get(key)
    v = v.strip() if isinstance(v, str) else ""
    if not v:
        raise BadInput(f"{label} is required.")
    if len(v) > maxlen:
        raise BadInput(f"{label} is too long.")
    return v


def lookup_account(role, ident):
    r = ROLES[role]
    ident = ident.lower() if r["ident"] == "email" else ident
    col = f"LOWER({r['ident']})" if r["ident"] == "email" else r["ident"]
    with closing(get_conn()) as conn:
        row = conn.execute(f"SELECT {r['pk']} AS id, {r['display']} AS display, password FROM {r['table']} WHERE {col} = ?",
                           (ident,)).fetchone()
    return dict(row) if row else None


def profile(role, uid):
    r = ROLES[role]
    with closing(get_conn()) as conn:
        row = conn.execute(f"SELECT {r['display']} AS name, {r['ident']} AS login FROM {r['table']} WHERE {r['pk']} = ?",
                           (uid,)).fetchone()
    return dict(row) if row else None


def attempt_login(role, ident, password):
    global _DUMMY_HASH
    if role not in ROLES:
        raise BadInput("Choose an account type.")
    ident = (ident or "").strip()
    password = password if isinstance(password, str) else ""
    if not ident or not password:
        raise BadInput("Enter your login and password.")
    key = f"{role}:{ident.lower()}"
    count, locked_until = FAILS.get(key, [0, 0])
    if locked_until > time.time():
        minutes = int((locked_until - time.time()) // 60) + 1
        raise AuthError(429, f"Too many failed attempts. Try again in {minutes} minute(s).")
    account = lookup_account(role, ident)
    if account:
        ok = verify_password(password, account["password"])
    else:
        # Same work as a real check so response time does not reveal which logins exist.
        if _DUMMY_HASH is None:
            _DUMMY_HASH = hash_password("dummy-password")
        verify_password(password, _DUMMY_HASH)
        ok = False
    if not ok:
        if locked_until and locked_until <= time.time():
            count = 0   # an earlier lockout has expired; start counting again
        count += 1
        FAILS[key] = [count, time.time() + LOCK_SECONDS if count >= MAX_FAILS else 0]
        raise AuthError(401, "Invalid login or password.")
    FAILS.pop(key, None)
    return account["id"]


def start_session(role, uid):
    now_ts = time.time()
    for t in [t for t, s in SESSIONS.items() if s["expires"] < now_ts]:
        del SESSIONS[t]
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = {"role": role, "id": uid, "expires": now_ts + SESSION_TTL}
    return token


def session_from_token(token):
    s = SESSIONS.get(token)
    if not s:
        return None
    if s["expires"] < time.time():
        del SESSIONS[token]
        return None
    return s


def end_other_sessions(role, uid, keep_token):
    for t in [t for t, s in SESSIONS.items() if s["role"] == role and s["id"] == uid and t != keep_token]:
        del SESSIONS[t]


def sign_up(payload):
    role = payload.get("role")
    password = check_new_password(payload.get("password"))
    email = clean(payload, "email", "Email", 100).lower()
    if not EMAIL_RE.match(email):
        raise BadInput("Enter a valid email address.")
    phone = clean(payload, "phone_number", "Phone number", 20)
    if role == "customer":
        plan = payload.get("plan_id") or 1
        values = (clean(payload, "name", "Full name"), email, hash_password(password), phone, int(plan))
        sql = "INSERT INTO CUSTOMER (name, email, password, phone_number, plan_id) VALUES (?, ?, ?, ?, ?)"
    elif role == "contractor":
        values = (clean(payload, "business_name", "Business name"), clean(payload, "contact_name", "Contact name"),
                  email, hash_password(password), phone)
        sql = "INSERT INTO CONTRACTOR (business_name, contact_name, email, password, phone_number) VALUES (?, ?, ?, ?, ?)"
    else:
        raise BadInput("Only customers and contractors can sign up. Administrators are created by another administrator.")
    if lookup_account(role, email):
        raise BadInput("An account with that email already exists.")
    with closing(get_conn()) as conn:
        try:
            cur = conn.execute(sql, values)
            conn.commit()
        except DB_ERRORS:
            raise BadInput("Could not create the account. Check the details and try again.")
        return role, cur.lastrowid


def change_password(role, uid, current, new):
    r = ROLES[role]
    check_new_password(new)
    with closing(get_conn()) as conn:
        row = conn.execute(f"SELECT password FROM {r['table']} WHERE {r['pk']} = ?", (uid,)).fetchone()
        if not row or not verify_password(current if isinstance(current, str) else "", row["password"]):
            raise BadInput("Current password is incorrect.")
        if current == new:
            raise BadInput("New password must be different from the current one.")
        conn.execute(f"UPDATE {r['table']} SET password = ? WHERE {r['pk']} = ?", (hash_password(new), uid))
        conn.commit()


def create_admin(username, password, created_by=None):
    username = (username or "").strip()
    if not USERNAME_RE.match(username):
        raise BadInput("Username must be 3-32 characters: letters, numbers, dot, dash or underscore.")
    check_new_password(password)
    if lookup_account("admin", username):
        raise BadInput("That username is already taken.")
    with closing(get_conn()) as conn:
        try:
            cur = conn.execute("INSERT INTO ADMIN (username, password, created_by) VALUES (?, ?, ?)",
                               (username, hash_password(password), created_by))
            conn.commit()
        except DB_ERRORS:
            raise BadInput("Could not create the administrator.")
        return cur.lastrowid


NO_DB_MESSAGE = """No MariaDB connection is configured, so nothing would reach phpMyAdmin.

  Easiest:  powershell -ExecutionPolicy Bypass -File Phase_3\\app\\start_mariadb.ps1
            (starts the port-forward and the server together)

  Or set DB_HOST / DB_PORT / DB_USER (and optionally DB_PASS) in the environment or in
  Phase_3\\app\\db_config.local.json (copy db_config.local.example.json).

  To run the offline SQLite demo instead (NOT shown in phpMyAdmin):  py server.py --demo"""


def port_open(port):
    with closing(socket.socket()) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_kubectl():
    found = shutil.which("kubectl")
    if found:
        return found
    # winget installs here; a terminal opened before the install has an old PATH.
    packages = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages")
    if os.path.isdir(packages):
        for name in os.listdir(packages):
            exe = os.path.join(packages, name, "kubectl.exe")
            if name.startswith("Kubernetes.kubectl") and os.path.exists(exe):
                return exe
    return None


def start_tunnel():
    """Starts 'kubectl port-forward' to the Discovery MariaDB if localhost:DB_PORT is not already open."""
    if port_open(DB_PORT):
        print(f"Using the port-forward already running on localhost:{DB_PORT}.")
        return
    kubectl = find_kubectl()
    if not kubectl:
        raise SystemExit("kubectl is not installed, so the server cannot reach MariaDB.\n"
                         "  winget install -e --id Kubernetes.kubectl\n\n" + NO_DB_MESSAGE)
    print(f"Starting port-forward localhost:{DB_PORT} -> svc/mariadb:3306 ...")
    proc = subprocess.Popen([kubectl, "-n", "ai-landscaping-db", "port-forward", "svc/mariadb", f"{DB_PORT}:3306"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    atexit.register(proc.terminate)
    deadline = time.time() + 20
    while not port_open(DB_PORT):
        if proc.poll() is not None:
            raise SystemExit("The port-forward failed:\n  " + (proc.stderr.read().strip() or "unknown error") +
                             "\nCheck that the Discovery KubeConfig is saved as %USERPROFILE%\\.kube\\config.")
        if time.time() > deadline:
            proc.terminate()
            raise SystemExit("The port-forward did not open within 20 seconds.")
        time.sleep(0.3)


def ask_password(prompt):
    """Password prompt that shows * for each character and accepts pasting (Windows console)."""
    if os.environ.get("PYCHARM_HOSTED") or os.environ.get("TERM_PROGRAM") == "vscode" or not sys.stdin.isatty():
        # IDE run consoles are not real terminals: key-by-key reading never sees the input there,
        # so use a normal line prompt (the password is visible in that console).
        sys.stdout.write(prompt.replace("(shows *, paste OK)", "(visible in this console)"))
        sys.stdout.flush()
        return sys.stdin.readline().rstrip("\r\n")
    try:
        import msvcrt
    except ImportError:
        return getpass.getpass(prompt)
    sys.stdout.write(prompt)
    sys.stdout.flush()
    chars = []
    while True:
        ch = msvcrt.getwch()
        if ch in ("\r", "\n"):
            break
        if ch == "\x03":
            raise KeyboardInterrupt
        if ch == "\x16":            # Ctrl+V when the console does not paste by itself
            try:
                import tkinter
                root = tkinter.Tk(); root.withdraw()
                pasted = root.clipboard_get(); root.destroy()
            except Exception:
                pasted = ""
            pasted = pasted.strip("\r\n")
            chars.extend(pasted); sys.stdout.write("*" * len(pasted))
        elif ch == "\b":
            if chars:
                chars.pop(); sys.stdout.write("\b \b")
        elif ch in ("\x00", "\xe0"):
            msvcrt.getwch()         # arrow/function key: ignore
        else:
            chars.append(ch); sys.stdout.write("*")
        sys.stdout.flush()
    sys.stdout.write("\n")
    return "".join(chars)


def prepare_db():
    if DB_HOST:
        if AUTO_TUNNEL:
            start_tunnel()
        if not os.environ.get("DB_USER"):
            os.environ["DB_USER"] = input(f"MariaDB username for {DB_NAME}: ").strip()
        if "DB_PASS" not in os.environ:
            os.environ["DB_PASS"] = ask_password(f"MariaDB password for {os.environ['DB_USER']} (shows *, paste OK): ")
    elif not DEMO_MODE:
        raise SystemExit(NO_DB_MESSAGE)
    elif not os.path.exists(DB_FILE):
        init_database()
    try:
        ensure_auth_schema()
    except DB_ERRORS as e:
        if DB_HOST and getattr(e, "args", [None])[0] in (2003, 2013):
            raise SystemExit(f"Cannot reach MariaDB at {DB_HOST}:{DB_PORT}. Is the port-forward running?\n"
                             "  kubectl -n ai-landscaping-db port-forward svc/mariadb 3307:3306")
        if DB_HOST and getattr(e, "args", [None])[0] in (1044, 1045):
            raise SystemExit(f"MariaDB rejected the login for user '{os.environ.get('DB_USER')}': {e}")
        raise SystemExit(f"Could not open the database or create the ADMIN table: {e}\n"
                         "If the DB account cannot CREATE tables, run sql/add_admin_table.sql as a privileged user.")


def cli_create_admin(username):
    prepare_db()
    with closing(get_conn()) as conn:
        existing = conn.execute("SELECT COUNT(*) AS n FROM ADMIN").fetchone()["n"]
    if existing:
        raise SystemExit("An administrator already exists. Log in and use 'Add admin' in the app to create more.")
    pw = ask_password("Password for the first administrator: ")
    if pw != ask_password("Repeat password: "):
        raise SystemExit("Passwords did not match.")
    try:
        create_admin(username, pw)
    except BadInput as e:
        raise SystemExit(str(e))
    print(f"Administrator '{username}' created. Start the server and log in as Admin.")


def cli_reset_password(role, ident):
    """Recovery tool: sets a new password for any account (used for the seeded sample users)."""
    prepare_db()
    if role not in ROLES:
        raise SystemExit("Role must be customer, contractor or admin.")
    account = lookup_account(role, ident)
    if not account:
        raise SystemExit("No such account.")
    pw = ask_password(f"New password for {role} '{ident}': ")
    if pw != ask_password("Repeat password: "):
        raise SystemExit("Passwords did not match.")
    try:
        check_new_password(pw)
    except BadInput as e:
        raise SystemExit(str(e))
    r = ROLES[role]
    with closing(get_conn()) as conn:
        conn.execute(f"UPDATE {r['table']} SET password = ? WHERE {r['pk']} = ?", (hash_password(pw), account["id"]))
        conn.commit()
    for t in [t for t, s in SESSIONS.items() if s["role"] == role and s["id"] == account["id"]]:
        del SESSIONS[t]
    print("Password updated.")


# ==============================================================================
# CUSTOMER & CONTRACTOR PORTALS
# Every query is scoped to the logged-in account's id (taken from the session, never
# from the request body), and every write re-checks ownership in its WHERE clause.
# ==============================================================================
PORTAL_FILE = os.path.join(APP_DIR, "portal.html")
APPOINTMENT_STATUSES = ["Pending", "Confirmed", "Scheduled", "Completed", "Cancelled"]
JOB_STATUSES = ["Scheduled", "In Progress", "Completed", "Cancelled"]
PAYMENT_METHODS = ["Credit Card", "Debit Card", "Bank Transfer", "PayPal"]

# Rule-based stand-in for the AI estimator: keyword -> (price per sq ft, flat price, idea).
ESTIMATE_RULES = [
    (("sod", "lawn", "grass", "turf", "seed"), 0.85, 0, "Install new sod or overseed the lawn, then aerate and fertilize."),
    (("xeriscap", "drought", "rock", "gravel"), 1.10, 0, "Drought-tolerant xeriscape layout with native plants and river rock."),
    (("mulch", "flower", "bed", "plant", "shrub", "garden"), 0.30, 400, "Refresh planting beds with perennials, shrubs and dark mulch."),
    (("patio", "paver", "walkway", "hardscape", "path"), 0, 4500, "Paver patio or walkway on a compacted gravel base."),
    (("irrigation", "sprinkler", "drip"), 0, 2200, "Zoned drip and sprinkler irrigation with a smart controller."),
    (("tree", "prune", "trim", "stump"), 0, 650, "Tree pruning, deadwood removal and stump grinding."),
    (("light", "lighting"), 0, 1800, "Low-voltage LED landscape lighting along paths and focal plants."),
    (("fence", "retaining", "wall"), 0, 3200, "Retaining wall or fence line with proper drainage."),
    (("maintenance", "mow", "weekly", "cleanup", "clean-up", "leaf"), 0, 350, "Recurring maintenance: mowing, edging, leaf and debris cleanup."),
]


def auto_estimate(description, sqft):
    text = description.lower()
    price, ideas = 0.0, []
    for words, per_sqft, flat, idea in ESTIMATE_RULES:
        if any(w in text for w in words):
            price += per_sqft * sqft + flat
            ideas.append(idea)
    if not ideas:
        price = 0.40 * sqft
        ideas.append("General yard cleanup and a planting plan sized to the property.")
    return round(max(price, 150.0), 2), " ".join(ideas)


def today():
    return datetime.now().strftime("%Y-%m-%d")


class Tx:
    """One database connection for a portal action. Writes are logged for the on-page SQL log."""

    def __init__(self):
        self.conn = get_conn()
        self.log = []

    def one(self, sql, params=()):
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def all(self, sql, params=()):
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def run(self, sql, params=(), expect_row=True, hide=()):
        cur = self.conn.execute(sql, params)
        if expect_row and cur.rowcount == 0:
            raise BadInput("That record was not found, belongs to another account, or can no longer be changed.")
        shown = render_sql(sql, [("••••••••" if i in hide else p) for i, p in enumerate(params)])
        note = f"-- {cur.rowcount} row(s) affected"
        if sql.lstrip().upper().startswith("INSERT"):
            note += f" | new id = {cur.lastrowid}"
        self.log.append(f"{shown};\n{note}")
        return cur


def num(payload, key, label, money=False, allow_zero=True):
    raw = payload.get(key)
    try:
        v = float(raw)
    except (TypeError, ValueError):
        raise BadInput(f"{label} must be a number.")
    if v != v or v < 0:
        raise BadInput(f"{label} cannot be negative.")
    if not allow_zero and v == 0:
        raise BadInput(f"{label} must be greater than zero.")
    if v > 100_000_000:
        raise BadInput(f"{label} is too large.")
    return round(v, 2) if money else int(v)


def date_field(payload, key, label, nullable=False):
    v = payload.get(key)
    v = v.strip() if isinstance(v, str) else ""
    if not v:
        if nullable:
            return None
        raise BadInput(f"{label} is required.")
    try:
        datetime.strptime(v, "%Y-%m-%d")
    except ValueError:
        raise BadInput(f"{label} must be a date (YYYY-MM-DD).")
    return v


def choice(payload, key, label, options):
    v = payload.get(key)
    if v not in options:
        raise BadInput(f"{label} must be one of: {', '.join(options)}.")
    return v


# Request -> latest estimate. (A request can have several estimates; portals show the newest.)
LATEST_ESTIMATE = "AI_ESTIMATE e ON e.ai_id = (SELECT MAX(e2.ai_id) FROM AI_ESTIMATE e2 WHERE e2.request_id = r.request_id)"
PAID = "COALESCE((SELECT SUM(pm.amount) FROM PAYMENT pm WHERE pm.invoice_id = i.invoice_id AND pm.status = 'Completed'), 0)"


def customer_data(uid):
    t = Tx()
    try:
        return {
            "me": t.one("""SELECT c.customer_id, c.name, c.email, c.phone_number, c.plan_id, sp.plan_name, sp.price
                           FROM CUSTOMER c LEFT JOIN SUBSCRIPTION_PLAN sp ON sp.plan_id = c.plan_id
                           WHERE c.customer_id = ?""", (uid,)),
            "plans": t.all("SELECT plan_id, plan_name, price, tier FROM SUBSCRIPTION_PLAN ORDER BY plan_id"),
            "properties": t.all("""SELECT p.property_id, p.address, p.sqft,
                                          (SELECT COUNT(*) FROM PROJECT_REQUEST r WHERE r.property_id = p.property_id) AS requests
                                   FROM PROPERTY p WHERE p.customer_id = ? ORDER BY p.property_id""", (uid,)),
            "requests": t.all(f"""SELECT r.request_id, r.description, r.status, r.property_id, p.address,
                                         e.ai_id, e.estimated_price, e.ideas_generated,
                                         (SELECT COUNT(*) FROM CONTRACTOR_QUOTE q JOIN AI_ESTIMATE e3 ON e3.ai_id = q.ai_id
                                          WHERE e3.request_id = r.request_id) AS quotes
                                  FROM PROJECT_REQUEST r
                                  JOIN PROPERTY p ON p.property_id = r.property_id
                                  LEFT JOIN {LATEST_ESTIMATE}
                                  WHERE r.customer_id = ? ORDER BY r.request_id DESC""", (uid,)),
            "quotes": t.all("""SELECT q.quote_id, q.scope, q.final_price, q.status, q.contractor_id,
                                      k.business_name, k.contact_name, k.phone_number, k.email AS contractor_email,
                                      e.request_id, e.estimated_price, r.description,
                                      (SELECT COUNT(*) FROM JOB j WHERE j.quote_id = q.quote_id) AS jobs
                               FROM CONTRACTOR_QUOTE q
                               JOIN AI_ESTIMATE e     ON e.ai_id = q.ai_id
                               JOIN PROJECT_REQUEST r ON r.request_id = e.request_id
                               JOIN CONTRACTOR k      ON k.contractor_id = q.contractor_id
                               WHERE r.customer_id = ? ORDER BY q.quote_id DESC""", (uid,)),
            "jobs": t.all("""SELECT j.job_id, j.status, j.start_date, j.end_date, j.revenue,
                                    k.business_name, r.request_id, r.description, p.address
                             FROM JOB j
                             JOIN CONTRACTOR_QUOTE q ON q.quote_id = j.quote_id
                             JOIN AI_ESTIMATE e      ON e.ai_id = q.ai_id
                             JOIN PROJECT_REQUEST r  ON r.request_id = e.request_id
                             JOIN PROPERTY p         ON p.property_id = r.property_id
                             JOIN CONTRACTOR k       ON k.contractor_id = j.contractor_id
                             WHERE r.customer_id = ? ORDER BY j.job_id DESC""", (uid,)),
            "invoices": t.all(f"""SELECT i.invoice_id, i.job_id, i.amount_due, i.issued, i.due_date, i.status,
                                         k.business_name, r.description, {PAID} AS amount_paid
                                  FROM INVOICE i
                                  JOIN JOB j              ON j.job_id = i.job_id
                                  JOIN CONTRACTOR_QUOTE q ON q.quote_id = j.quote_id
                                  JOIN AI_ESTIMATE e      ON e.ai_id = q.ai_id
                                  JOIN PROJECT_REQUEST r  ON r.request_id = e.request_id
                                  JOIN CONTRACTOR k       ON k.contractor_id = j.contractor_id
                                  WHERE r.customer_id = ? ORDER BY i.invoice_id DESC""", (uid,)),
            "payments": t.all("""SELECT pm.payment_id, pm.invoice_id, pm.amount, pm.payment_date, pm.payment_method, pm.status, r.description
                                 FROM PAYMENT pm
                                 JOIN INVOICE i          ON i.invoice_id = pm.invoice_id
                                 JOIN JOB j              ON j.job_id = i.job_id
                                 JOIN CONTRACTOR_QUOTE q ON q.quote_id = j.quote_id
                                 JOIN AI_ESTIMATE e      ON e.ai_id = q.ai_id
                                 JOIN PROJECT_REQUEST r  ON r.request_id = e.request_id
                                 WHERE r.customer_id = ? ORDER BY pm.payment_id DESC""", (uid,)),
            "appointments": t.all("""SELECT a.appointment_id, a.scheduled, a.status, a.request_id, a.contractor_id,
                                            r.description, k.business_name, k.phone_number
                                     FROM APPOINTMENT a
                                     JOIN PROJECT_REQUEST r ON r.request_id = a.request_id
                                     JOIN CONTRACTOR k      ON k.contractor_id = a.contractor_id
                                     WHERE a.customer_id = ? ORDER BY a.scheduled DESC""", (uid,)),
        }
    finally:
        t.conn.close()


def contractor_data(uid):
    t = Tx()
    try:
        return {
            "me": t.one("SELECT contractor_id, business_name, contact_name, email, phone_number FROM CONTRACTOR WHERE contractor_id = ?", (uid,)),
            "open_requests": t.all(f"""SELECT r.request_id, r.description, r.status, p.address, p.sqft, c.name AS customer_name,
                                              e.ai_id, e.estimated_price, e.ideas_generated,
                                              (SELECT COUNT(*) FROM CONTRACTOR_QUOTE q WHERE q.ai_id = e.ai_id) AS quotes
                                       FROM PROJECT_REQUEST r
                                       JOIN PROPERTY p ON p.property_id = r.property_id
                                       JOIN CUSTOMER c ON c.customer_id = r.customer_id
                                       JOIN {LATEST_ESTIMATE}
                                       WHERE r.status = 'Pending'
                                         AND NOT EXISTS (SELECT 1 FROM CONTRACTOR_QUOTE q JOIN AI_ESTIMATE e4 ON e4.ai_id = q.ai_id
                                                         WHERE e4.request_id = r.request_id
                                                           AND (q.contractor_id = ? OR q.status = 'Accepted'))
                                       ORDER BY r.request_id DESC""", (uid,)),
            "quotes": t.all("""SELECT q.quote_id, q.scope, q.final_price, q.status, q.ai_id,
                                      e.estimated_price, r.request_id, r.description, p.address,
                                      c.name AS customer_name, c.phone_number AS customer_phone, c.email AS customer_email,
                                      (SELECT MAX(j.job_id) FROM JOB j WHERE j.quote_id = q.quote_id) AS job_id
                               FROM CONTRACTOR_QUOTE q
                               JOIN AI_ESTIMATE e     ON e.ai_id = q.ai_id
                               JOIN PROJECT_REQUEST r ON r.request_id = e.request_id
                               JOIN PROPERTY p        ON p.property_id = r.property_id
                               JOIN CUSTOMER c        ON c.customer_id = r.customer_id
                               WHERE q.contractor_id = ? ORDER BY q.quote_id DESC""", (uid,)),
            "jobs": t.all("""SELECT j.job_id, j.quote_id, j.status, j.start_date, j.end_date, j.revenue, j.expenses,
                                    r.request_id, r.description, p.address, c.name AS customer_name,
                                    (SELECT COUNT(*) FROM INVOICE i WHERE i.job_id = j.job_id) AS invoices
                             FROM JOB j
                             JOIN CONTRACTOR_QUOTE q ON q.quote_id = j.quote_id
                             JOIN AI_ESTIMATE e      ON e.ai_id = q.ai_id
                             JOIN PROJECT_REQUEST r  ON r.request_id = e.request_id
                             JOIN PROPERTY p         ON p.property_id = r.property_id
                             JOIN CUSTOMER c         ON c.customer_id = r.customer_id
                             WHERE j.contractor_id = ? ORDER BY j.job_id DESC""", (uid,)),
            "invoices": t.all(f"""SELECT i.invoice_id, i.job_id, i.amount_due, i.issued, i.due_date, i.status,
                                         c.name AS customer_name, r.description, {PAID} AS amount_paid
                                  FROM INVOICE i
                                  JOIN JOB j              ON j.job_id = i.job_id
                                  JOIN CONTRACTOR_QUOTE q ON q.quote_id = j.quote_id
                                  JOIN AI_ESTIMATE e      ON e.ai_id = q.ai_id
                                  JOIN PROJECT_REQUEST r  ON r.request_id = e.request_id
                                  JOIN CUSTOMER c         ON c.customer_id = r.customer_id
                                  WHERE j.contractor_id = ? ORDER BY i.invoice_id DESC""", (uid,)),
            "appointments": t.all("""SELECT a.appointment_id, a.scheduled, a.status, a.request_id,
                                            r.description, p.address, c.name AS customer_name, c.phone_number AS customer_phone
                                     FROM APPOINTMENT a
                                     JOIN PROJECT_REQUEST r ON r.request_id = a.request_id
                                     JOIN PROPERTY p        ON p.property_id = r.property_id
                                     JOIN CUSTOMER c        ON c.customer_id = a.customer_id
                                     WHERE a.contractor_id = ? ORDER BY a.scheduled DESC""", (uid,)),
        }
    finally:
        t.conn.close()


def customer_action(t, uid, action, p):
    """Returns a short success message. Raises BadInput for anything not allowed."""
    if action == "update_profile":
        plan = int(p.get("plan_id"))
        if not t.one("SELECT plan_id FROM SUBSCRIPTION_PLAN WHERE plan_id = ?", (plan,)):
            raise BadInput("Choose a valid subscription plan.")
        t.run("UPDATE CUSTOMER SET name = ?, phone_number = ?, plan_id = ? WHERE customer_id = ?",
              (clean(p, "name", "Full name"), clean(p, "phone_number", "Phone number", 20), plan, uid))
        return "Profile updated."

    if action == "add_property":
        t.run("INSERT INTO PROPERTY (address, sqft, customer_id) VALUES (?, ?, ?)",
              (clean(p, "address", "Address", 200), num(p, "sqft", "Lot size", allow_zero=False), uid))
        return "Property added."

    if action == "update_property":
        t.run("UPDATE PROPERTY SET address = ?, sqft = ? WHERE property_id = ? AND customer_id = ?",
              (clean(p, "address", "Address", 200), num(p, "sqft", "Lot size", allow_zero=False), int(p["id"]), uid))
        return "Property updated."

    if action == "delete_property":
        t.run("DELETE FROM PROPERTY WHERE property_id = ? AND customer_id = ?", (int(p["id"]), uid))
        return "Property deleted (with its project requests)."

    if action == "create_request":
        prop = t.one("SELECT property_id, sqft FROM PROPERTY WHERE property_id = ? AND customer_id = ?", (int(p["property_id"]), uid))
        if not prop:
            raise BadInput("Choose one of your properties.")
        desc = clean(p, "description", "Description", 2000)
        cur = t.run("INSERT INTO PROJECT_REQUEST (description, status, customer_id, property_id) VALUES (?, 'Pending', ?, ?)",
                    (desc, uid, prop["property_id"]))
        price, ideas = auto_estimate(desc, int(prop["sqft"]))
        t.run("INSERT INTO AI_ESTIMATE (estimated_price, estimated_prop_size, ideas_generated, request_id) VALUES (?, ?, ?, ?)",
              (price, int(prop["sqft"]), ideas, cur.lastrowid))
        return f"Request submitted. Estimated price: ${price:,.2f}. Contractors can now send quotes."

    if action == "cancel_request":
        t.run("""DELETE FROM PROJECT_REQUEST WHERE request_id = ? AND customer_id = ? AND status = 'Pending'
                 AND NOT EXISTS (SELECT 1 FROM CONTRACTOR_QUOTE q JOIN AI_ESTIMATE e ON e.ai_id = q.ai_id
                                 WHERE e.request_id = PROJECT_REQUEST.request_id AND q.status = 'Accepted')""",
              (int(p["id"]), uid))
        return "Request cancelled."

    if action in ("accept_quote", "reject_quote"):
        q = t.one("""SELECT q.quote_id, q.status, e.request_id FROM CONTRACTOR_QUOTE q
                     JOIN AI_ESTIMATE e ON e.ai_id = q.ai_id
                     JOIN PROJECT_REQUEST r ON r.request_id = e.request_id
                     WHERE q.quote_id = ? AND r.customer_id = ?""", (int(p["id"]), uid))
        if not q or q["status"] != "Pending":
            raise BadInput("Only pending quotes on your own requests can be accepted or rejected.")
        if action == "reject_quote":
            t.run("UPDATE CONTRACTOR_QUOTE SET status = 'Rejected' WHERE quote_id = ?", (q["quote_id"],))
            return "Quote rejected."
        if t.one("""SELECT q.quote_id FROM CONTRACTOR_QUOTE q JOIN AI_ESTIMATE e ON e.ai_id = q.ai_id
                    WHERE e.request_id = ? AND q.status = 'Accepted'""", (q["request_id"],)):
            raise BadInput("You already accepted a quote for this request.")
        t.run("UPDATE CONTRACTOR_QUOTE SET status = 'Accepted' WHERE quote_id = ?", (q["quote_id"],))
        t.run("""UPDATE CONTRACTOR_QUOTE SET status = 'Rejected'
                 WHERE status = 'Pending' AND quote_id <> ?
                   AND ai_id IN (SELECT ai_id FROM AI_ESTIMATE WHERE request_id = ?)""",
              (q["quote_id"], q["request_id"]), expect_row=False)
        t.run("UPDATE PROJECT_REQUEST SET status = 'Approved' WHERE request_id = ?", (q["request_id"],))
        return "Quote accepted. The contractor can now schedule the job; other pending quotes were declined."

    if action == "book_appointment":
        req, contractor = int(p["request_id"]), int(p["contractor_id"])
        if not t.one("""SELECT 1 AS ok FROM CONTRACTOR_QUOTE q
                        JOIN AI_ESTIMATE e ON e.ai_id = q.ai_id
                        JOIN PROJECT_REQUEST r ON r.request_id = e.request_id
                        WHERE r.request_id = ? AND r.customer_id = ? AND q.contractor_id = ?""", (req, uid, contractor)):
            raise BadInput("You can book a visit with a contractor who quoted on one of your requests.")
        raw = (p.get("scheduled") or "").strip().replace("T", " ")
        try:
            when = datetime.strptime(raw[:16], "%Y-%m-%d %H:%M")
        except ValueError:
            raise BadInput("Pick a date and time for the visit.")
        if when < datetime.now():
            raise BadInput("The visit must be in the future.")
        t.run("INSERT INTO APPOINTMENT (scheduled, status, customer_id, contractor_id, request_id) VALUES (?, 'Pending', ?, ?, ?)",
              (when.strftime("%Y-%m-%d %H:%M:00"), uid, contractor, req))
        return "Visit requested. The contractor will confirm it."

    if action == "cancel_appointment":
        t.run("""UPDATE APPOINTMENT SET status = 'Cancelled'
                 WHERE appointment_id = ? AND customer_id = ? AND status IN ('Pending', 'Confirmed', 'Scheduled')""",
              (int(p["id"]), uid))
        return "Visit cancelled."

    if action == "pay_invoice":
        inv = t.one(f"""SELECT i.invoice_id, i.status, i.amount_due, {PAID} AS amount_paid
                        FROM INVOICE i
                        JOIN JOB j              ON j.job_id = i.job_id
                        JOIN CONTRACTOR_QUOTE q ON q.quote_id = j.quote_id
                        JOIN AI_ESTIMATE e      ON e.ai_id = q.ai_id
                        JOIN PROJECT_REQUEST r  ON r.request_id = e.request_id
                        WHERE i.invoice_id = ? AND r.customer_id = ?""", (int(p["invoice_id"]), uid))
        if not inv:
            raise BadInput("Invoice not found.")
        balance = round(float(inv["amount_due"]) - float(inv["amount_paid"]), 2)
        amount = num(p, "amount", "Amount", money=True, allow_zero=False)
        if balance <= 0:
            raise BadInput("This invoice is already paid.")
        if amount > balance:
            raise BadInput(f"Amount cannot exceed the balance of ${balance:,.2f}.")
        method = choice(p, "payment_method", "Payment method", PAYMENT_METHODS)
        t.run("INSERT INTO PAYMENT (amount, payment_date, status, payment_method, invoice_id) VALUES (?, ?, 'Completed', ?, ?)",
              (amount, today(), method, inv["invoice_id"]))
        after = t.one("SELECT status FROM INVOICE WHERE invoice_id = ?", (inv["invoice_id"],))["status"]
        if after != inv["status"]:
            t.log.append(f"-- Trigger trg_payment_insert_mark_paid fired: INVOICE #{inv['invoice_id']} status '{inv['status']}' -> '{after}'")
        elif amount >= balance - 0.005 and after != "Paid":
            # The trigger is missing on this database (e.g. it was not imported), so do its job here.
            t.log.append("-- trg_payment_insert_mark_paid did not fire (trigger missing on this database); updating the status directly:")
            t.run("UPDATE INVOICE SET status = 'Paid' WHERE invoice_id = ?", (inv["invoice_id"],))
            after = "Paid"
        return f"Payment of ${amount:,.2f} recorded." + (" Invoice is now fully paid." if after == "Paid" else "")

    raise BadInput("Unknown action.")


def contractor_action(t, uid, action, p):
    if action == "update_profile":
        t.run("UPDATE CONTRACTOR SET business_name = ?, contact_name = ?, phone_number = ? WHERE contractor_id = ?",
              (clean(p, "business_name", "Business name"), clean(p, "contact_name", "Contact name"),
               clean(p, "phone_number", "Phone number", 20), uid))
        return "Profile updated."

    if action == "submit_quote":
        est = t.one("""SELECT e.ai_id, r.request_id, r.status FROM AI_ESTIMATE e
                       JOIN PROJECT_REQUEST r ON r.request_id = e.request_id WHERE e.ai_id = ?""", (int(p["ai_id"]),))
        if not est or est["status"] != "Pending":
            raise BadInput("This request is no longer open for quotes.")
        if t.one("""SELECT 1 AS x FROM CONTRACTOR_QUOTE q JOIN AI_ESTIMATE e ON e.ai_id = q.ai_id
                    WHERE e.request_id = ? AND (q.contractor_id = ? OR q.status = 'Accepted')""", (est["request_id"], uid)):
            raise BadInput("You already quoted this request, or the customer already accepted a quote.")
        cur = t.run("INSERT INTO CONTRACTOR_QUOTE (scope, final_price, status, contractor_id, ai_id) VALUES (?, ?, 'Pending', ?, ?)",
                    (clean(p, "scope", "Scope of work", 2000), num(p, "final_price", "Price", money=True, allow_zero=False), uid, est["ai_id"]))
        return "Quote sent to the customer."

    if action == "update_quote":
        t.run("UPDATE CONTRACTOR_QUOTE SET scope = ?, final_price = ? WHERE quote_id = ? AND contractor_id = ? AND status = 'Pending'",
              (clean(p, "scope", "Scope of work", 2000), num(p, "final_price", "Price", money=True, allow_zero=False), int(p["id"]), uid))
        return "Quote updated."

    if action == "withdraw_quote":
        t.run("DELETE FROM CONTRACTOR_QUOTE WHERE quote_id = ? AND contractor_id = ? AND status = 'Pending'", (int(p["id"]), uid))
        return "Quote withdrawn."

    if action == "start_job":
        q = t.one("""SELECT q.quote_id, q.final_price, e.request_id,
                            (SELECT COUNT(*) FROM JOB j WHERE j.quote_id = q.quote_id) AS jobs
                     FROM CONTRACTOR_QUOTE q JOIN AI_ESTIMATE e ON e.ai_id = q.ai_id
                     WHERE q.quote_id = ? AND q.contractor_id = ? AND q.status = 'Accepted'""", (int(p["quote_id"]), uid))
        if not q:
            raise BadInput("Only your accepted quotes can become jobs.")
        if q["jobs"]:
            raise BadInput("A job already exists for this quote.")
        cur = t.run("""INSERT INTO JOB (status, start_date, end_date, revenue, expenses, quote_id, contractor_id)
                       VALUES ('Scheduled', ?, NULL, ?, ?, ?, ?)""",
                    (date_field(p, "start_date", "Start date"), float(q["final_price"]),
                     num(p, "expenses", "Expected expenses", money=True), q["quote_id"], uid))
        t.run("UPDATE PROJECT_REQUEST SET status = 'In Progress' WHERE request_id = ?", (q["request_id"],))
        return "Job scheduled."

    if action == "update_job":
        job = t.one("""SELECT j.job_id, j.start_date, e.request_id FROM JOB j
                       JOIN CONTRACTOR_QUOTE q ON q.quote_id = j.quote_id
                       JOIN AI_ESTIMATE e ON e.ai_id = q.ai_id
                       WHERE j.job_id = ? AND j.contractor_id = ?""", (int(p["id"]), uid))
        if not job:
            raise BadInput("Job not found.")
        status = choice(p, "status", "Status", JOB_STATUSES)
        end = date_field(p, "end_date", "End date", nullable=True)
        start = str(job["start_date"])[:10]
        if status == "Completed" and not end:
            end = max(today(), start)
        if end and end < start:
            raise BadInput(f"End date cannot be before the start date ({start}).")
        t.run("UPDATE JOB SET status = ?, end_date = ?, expenses = ? WHERE job_id = ? AND contractor_id = ?",
              (status, end, num(p, "expenses", "Expenses", money=True), job["job_id"], uid))
        req_status = {"Scheduled": "In Progress", "In Progress": "In Progress", "Completed": "Completed", "Cancelled": "Approved"}[status]
        t.run("UPDATE PROJECT_REQUEST SET status = ? WHERE request_id = ?", (req_status, job["request_id"]))
        return f"Job marked {status}."

    if action == "create_invoice":
        job = t.one("""SELECT job_id, revenue, (SELECT COUNT(*) FROM INVOICE i WHERE i.job_id = JOB.job_id) AS invoices
                       FROM JOB WHERE job_id = ? AND contractor_id = ?""", (int(p["job_id"]), uid))
        if not job:
            raise BadInput("Job not found.")
        if job["invoices"]:
            raise BadInput("This job already has an invoice.")
        due = date_field(p, "due_date", "Due date")
        if due < today():
            raise BadInput("The due date cannot be in the past.")
        cur = t.run("INSERT INTO INVOICE (amount_due, issued, due_date, status, job_id) VALUES (?, ?, ?, 'Issued', ?)",
                    (num(p, "amount_due", "Amount due", money=True, allow_zero=False), today(), due, job["job_id"]))
        return "Invoice sent to the customer."

    if action == "update_appointment":
        status = choice(p, "status", "Status", ["Confirmed", "Completed", "Cancelled"])
        t.run("UPDATE APPOINTMENT SET status = ? WHERE appointment_id = ? AND contractor_id = ? AND status <> 'Cancelled'",
              (status, int(p["id"]), uid))
        return f"Visit marked {status}."

    raise BadInput("Unknown action.")


def portal_action(role, uid, action, payload):
    t = Tx()
    try:
        handler = customer_action if role == "customer" else contractor_action
        message = handler(t, uid, action, payload)
        t.conn.commit()
        return {"status": "success", "message": message, "sql": "\n\n".join(t.log) or "-- no changes", "timestamp": now()}
    except Exception:
        t.conn.rollback()
        raise
    finally:
        t.conn.close()


class RequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if not self.valid_host():
            return
        try:
            self.handle_get()
        except AuthError as e:
            self.send_json({"status": "error", "error": e.message, "code": e.code}, e.code)
        except DB_ERRORS as e:
            self.send_json({"status": "error", "error": str(e)}, 503)

    def valid_host(self):
        if not DB_HOST or self.headers.get("Host") in (f"localhost:{PORT}", f"127.0.0.1:{PORT}"):
            return True
        self.send_error(403)
        return False

    def current_session(self):
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        try:
            morsel = cookies.SimpleCookie(raw).get(COOKIE_NAME)
        except cookies.CookieError:
            return None
        s = session_from_token(morsel.value) if morsel else None
        return {**s, "token": morsel.value} if s else None

    def require(self, role=None):
        s = self.current_session()
        if not s or not profile(s["role"], s["id"]):
            if s:
                SESSIONS.pop(s["token"], None)
            raise AuthError(401, "Please log in.")
        roles = (role,) if isinstance(role, str) else role
        if roles and s["role"] not in roles:
            raise AuthError(403, "Administrator access required." if roles == ("admin",) else "This page is not available for your account type.")
        return s

    def redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def send_html(self, page):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))

    def serve_portal(self, role):
        """/customer and /contractor: only for a logged-in account of that role; everyone else goes to the login page."""
        s = self.current_session()
        if not s or not profile(s["role"], s["id"]):
            self.redirect("/")
        elif s["role"] != role:
            self.redirect("/" if s["role"] == "admin" else f"/{s['role']}")
        else:
            with open(PORTAL_FILE, encoding="utf-8") as f:
                page = f.read()
            label = f"MariaDB {DB_HOST}:{DB_PORT}/{DB_NAME}" if DB_HOST else "Local SQLite"
            self.send_html(page.replace("__ROLE__", role).replace("__DATABASE_LABEL__", escape(label)))

    def send_login(self, role, uid):
        token = start_session(role, uid)
        p = profile(role, uid)
        self.send_json({"status": "success", "user": {"role": role, "id": uid, "name": p["name"], "login": p["login"]}},
                       cookie=f"{COOKIE_NAME}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}")

    def handle_get(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/api/me":
            s = self.current_session()
            p = profile(s["role"], s["id"]) if s else None
            if not p:
                self.send_json({"authenticated": False})
            else:
                self.send_json({"authenticated": True, "user": {"role": s["role"], "id": s["id"], "name": p["name"], "login": p["login"]}})
            return
        if parsed.path == "/api/plans":
            with closing(get_conn()) as conn:
                self.send_json([dict(r) for r in conn.execute(FK_OPTIONS["SUBSCRIPTION_PLAN"]).fetchall()])
            return
        if parsed.path in ("/customer", "/contractor"):
            self.serve_portal(parsed.path[1:])
            return
        if parsed.path == "/api/portal":
            s = self.require(("customer", "contractor"))
            self.send_json(customer_data(s["id"]) if s["role"] == "customer" else contractor_data(s["id"]))
            return
        if parsed.path == "/api/portal/reports":
            s = self.require(("customer", "contractor"))
            self.send_json([report_meta(r) for r in ROLE_REPORTS[s["role"]].values()])
            return
        if parsed.path.startswith("/api/portal/report/"):
            s = self.require(("customer", "contractor"))
            report_id = parsed.path.split("/")[4]
            if report_id not in ROLE_REPORTS[s["role"]]:
                raise AuthError(404, "No such report.")
            self.send_json(run_report(report_id, ROLE_REPORTS[s["role"]], s["id"]))
            return
        if parsed.path.startswith("/api/"):
            self.require("admin")
        if parsed.path in ["/", "/index.html", "/admin", "/customers", "/properties"]:
            s = self.current_session()
            if s and s["role"] in ("customer", "contractor") and profile(s["role"], s["id"]):
                self.redirect(f"/{s['role']}")
                return
            label = f"MariaDB {DB_HOST}:{DB_PORT}/{DB_NAME}" if DB_HOST else "Local SQLite"
            page = HTML_PAGE.replace("__DATABASE_LABEL__", escape(label))
            page = page.replace("__LIVE_MODE__", "true" if DB_HOST else "false")
            page = page.replace("__DEMO_ONLY__", 'style="display:none"' if DB_HOST else "")
            self.send_html(page)
        elif parsed.path == "/api/customers":
            with closing(get_conn()) as conn:
                rows = conn.execute("SELECT customer_id, name, email, phone_number, plan_id FROM CUSTOMER ORDER BY customer_id ASC").fetchall()
            self.send_json([dict(r) for r in rows])
        elif parsed.path == "/api/properties":
            with closing(get_conn()) as conn:
                rows = conn.execute("SELECT property_id, address, sqft, customer_id FROM PROPERTY ORDER BY property_id ASC").fetchall()
            self.send_json([dict(r) for r in rows])
        elif parsed.path == "/api/schema":
            self.send_json(TABLE_CONFIG)
        elif parsed.path == "/api/options":
            with closing(get_conn()) as conn:
                data = {t: [dict(r) for r in conn.execute(sql).fetchall()] for t, sql in FK_OPTIONS.items()}
            self.send_json(data)
        elif parsed.path == "/api/counts":
            with closing(get_conn()) as conn:
                data = {t: conn.execute(f"SELECT COUNT(*) AS total FROM {t}").fetchone()["total"] for t in ALL_TABLES}
            self.send_json(data)
        elif parsed.path == "/api/reports":
            self.send_json([report_meta(r) for r in REPORTS])
        elif parsed.path.startswith("/api/report/") and parsed.path.split("/")[3] in REPORTS_BY_ID:
            self.send_json(run_report(parsed.path.split("/")[3]))
        elif parsed.path == "/api/db_objects":
            self.send_json(db_objects())
        elif parsed.path.startswith("/api/rows/") and parsed.path.split("/")[3] in TABLES:
            table = parsed.path.split("/")[3]
            self.send_json(list_rows(table, query.get("q", [""])[0].strip()))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if not self.valid_host():
            return
        if self.headers.get_content_type() != "application/json":
            self.send_error(415)
            return
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        if length > 1_000_000:
            self.send_error(413)
            return
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body) if body else {}
            self.handle_post(parsed.path, payload)
        except AuthError as e:
            self.send_json({"status": "error", "error": e.message, "code": e.code}, e.code)
        except (BadInput, KeyError, ValueError, TypeError) as e:
            msg = str(e) if isinstance(e, BadInput) else f"Invalid input: {e}"
            self.send_json({"status": "error", "error": msg, "sql": f"-- Rejected before reaching the database: {msg}", "timestamp": now()}, 400)
        except DB_ERRORS as e:
            self.send_json({"status": "error", "error": str(e), "sql": f"-- ERROR: {e}", "timestamp": now()}, 400)

    def handle_post(self, path, payload):
        if path == "/api/login":
            role = payload.get("role")
            self.send_login(role, attempt_login(role, payload.get("identifier"), payload.get("password")))
        elif path == "/api/signup":
            role, uid = sign_up(payload)
            self.send_login(role, uid)
        elif path == "/api/logout":
            s = self.current_session()
            if s:
                SESSIONS.pop(s["token"], None)
            self.send_json({"status": "success"}, cookie=f"{COOKIE_NAME}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
        elif path == "/api/change_password":
            s = self.require()
            change_password(s["role"], s["id"], payload.get("current_password"), payload.get("new_password"))
            end_other_sessions(s["role"], s["id"], s["token"])
            self.send_json({"status": "success"})
        elif path == "/api/admins":
            s = self.require("admin")
            create_admin(payload.get("username"), payload.get("password"), s["id"])
            self.send_json({"status": "success"})
        elif path.startswith("/api/portal/"):
            s = self.require(("customer", "contractor"))
            self.send_json(portal_action(s["role"], s["id"], path.split("/")[3], payload))
        else:
            self.require("admin")
            self.handle_admin_post(path, payload)

    def handle_admin_post(self, path, payload):
        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "rows"] and parts[2] in TABLES and parts[3] in ("insert", "update", "delete"):
            result = write_row(parts[2], parts[3], payload)
            self.send_json(result, 200 if result["status"] == "success" else 400)

        elif path == "/api/insert_customer":
            params = (payload["name"], payload["email"], hash_password(payload.get("password")),
                      payload["phone_number"], payload["plan_id"])
            statement = """INSERT INTO CUSTOMER (name, email, password, phone_number, plan_id)
VALUES (?, ?, ?, ?, ?)"""
            with closing(get_conn()) as conn:
                cursor = conn.execute(statement, params)
                conn.commit()
            shown = render_sql(statement, (*params[:2], "••••••••", *params[3:]))
            self.send_json({"status": "success", "new_id": cursor.lastrowid,
                            "sql": f"{shown};\n-- Generated PK: {cursor.lastrowid}", "timestamp": now()})

        elif path in ("/api/delete_customer", "/api/insert_property", "/api/delete_property"):
            table = "CUSTOMER" if path == "/api/delete_customer" else "PROPERTY"
            if path == "/api/insert_property":
                action, data = "insert", {"values": payload}
            else:
                action, data = "delete", {"id": payload[TABLES[table]["pk"]]}
            result = write_row(table, action, data)
            self.send_json(result, 200 if result["status"] == "success" else 400)

        else:
            self.send_response(404)
            self.end_headers()

    def send_json(self, data, code=200, cookie=None):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(json.dumps(data, default=json_value).encode("utf-8"))

    def log_message(self, fmt, *args):
        pass


def json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def run():
    prepare_db()
    try:
        with closing(get_conn()) as conn:
            conn.execute("SELECT 1 FROM CUSTOMER LIMIT 1")
            admins = conn.execute("SELECT COUNT(*) AS n FROM ADMIN").fetchone()["n"]
    except DB_ERRORS as e:
        raise SystemExit(f"Could not open the database: {e}")
    if not admins:
        print("No administrator exists yet. Create the first one with:  python server.py create-admin <username>")
    if DB_HOST:
        print(f"Database: MariaDB {DB_HOST}:{DB_PORT}/{DB_NAME} - website changes show up in phpMyAdmin")
    else:
        print(f"Database: DEMO SQLite file {DB_FILE}\n"
              "  Changes are saved in that file only and will NOT appear in phpMyAdmin.")
    print(f"Starting CS 4604 Group 6 Landscaping Portal on http://localhost:{PORT}")
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("127.0.0.1", PORT), RequestHandler)
    server.serve_forever()


def main():
    args = [a for a in sys.argv[1:] if a != "--demo"]
    if len(args) == 2 and args[0] == "create-admin":
        cli_create_admin(args[1])
    elif len(args) == 3 and args[0] == "reset-password":
        cli_reset_password(args[1], args[2])
    elif args:
        raise SystemExit("Usage: server.py [--demo] [create-admin <username> | reset-password <customer|contractor|admin> <email-or-username>]")
    else:
        run()


if __name__ == "__main__":
    main()
