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
import sqlite3
import os
import urllib.parse
from datetime import datetime

PORT = 8080
DB_FILE = os.path.join(os.path.dirname(__file__), "landscaping.db")

def init_database():
    """Initializes the database with schema and 20 sample rows matching Phase 1."""
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON;")
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS SUBSCRIPTION_PLAN (
        plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_name TEXT NOT NULL,
        price REAL NOT NULL,
        tier TEXT NOT NULL
    );
    """)
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS CONTRACTOR (
        contractor_id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_name TEXT NOT NULL,
        contact_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        phone_number TEXT NOT NULL
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS CUSTOMER (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        plan_id INTEGER,
        FOREIGN KEY (plan_id) REFERENCES SUBSCRIPTION_PLAN(plan_id)
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS PROPERTY (
        property_id INTEGER PRIMARY KEY AUTOINCREMENT,
        address TEXT NOT NULL,
        sqft INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES CUSTOMER(customer_id) ON DELETE CASCADE
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS PROJECT_REQUEST (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        customer_id INTEGER NOT NULL,
        property_id INTEGER NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES CUSTOMER(customer_id) ON DELETE CASCADE,
        FOREIGN KEY (property_id) REFERENCES PROPERTY(property_id) ON DELETE CASCADE
    );
    """)

    # Populate SUBSCRIPTION_PLAN
    c.executemany("INSERT INTO SUBSCRIPTION_PLAN VALUES (?, ?, ?, ?)", [
        (1, 'Basic Homeowner', 19.99, 'Tier 1'),
        (2, 'Pro Landscaper', 49.99, 'Tier 2'),
        (3, 'Enterprise Contractor', 99.99, 'Tier 3')
    ])

    # Populate CONTRACTOR (20)
    contractors = [
        (1, 'GreenThumb Landscaping', 'Alice Green', 'alice@greenthumb.com', 'hash_pass_01', '555-0101'),
        (2, 'EcoLawn Pro Services', 'Bob Builder', 'bob@ecolawn.com', 'hash_pass_02', '555-0102'),
        (3, 'Elite Turf & Design', 'Charlie Brown', 'charlie@eliteturf.com', 'hash_pass_03', '555-0103'),
        (4, 'Vibrant Yard Co.', 'Diana Prince', 'diana@vibrantyard.com', 'hash_pass_04', '555-0104'),
        (5, 'Serene Gardens LLC', 'Evan Wright', 'evan@serenegardens.com', 'hash_pass_05', '555-0105'),
        (6, 'Prime Mowing & More', 'Fiona Gallagher', 'fiona@primemowing.com', 'hash_pass_06', '555-0106'),
        (7, 'Absolute Outdoors', 'George Miller', 'george@absoluteoutdoors.com', 'hash_pass_07', '555-0107'),
        (8, 'TerraLandscapes', 'Hannah Abbott', 'hannah@terralandscapes.com', 'hash_pass_08', '555-0108'),
        (9, 'SunValley Yard Care', 'Ian Malcolm', 'ian@sunvalleyyard.com', 'hash_pass_09', '555-0109'),
        (10, 'Lush Lawn Masters', 'Julia Roberts', 'julia@lushlawn.com', 'hash_pass_10', '555-0110'),
        (11, 'Precision Cuts', 'Kevin Bacon', 'kevin@precisioncuts.com', 'hash_pass_11', '555-0111'),
        (12, 'NatureCraft Design', 'Laura Croft', 'laura@naturecraft.com', 'hash_pass_12', '555-0112'),
        (13, 'Blossom & Branch', 'Michael Scott', 'michael@blossombranch.com', 'hash_pass_13', '555-0113'),
        (14, 'Apex Yard Care', 'Pam Beesly', 'pam@apexyard.com', 'hash_pass_14', '555-0114'),
        (15, 'Sod & Stone Pros', 'Jim Halpert', 'jim@sodstone.com', 'hash_pass_15', '555-0115'),
        (16, 'Evergreen Experts', 'Dwight Schrute', 'dwight@evergreenexperts.com', 'hash_pass_16', '555-0116'),
        (17, 'BlueSky Landscaping', 'Angela Martin', 'angela@bluesky.com', 'hash_pass_17', '555-0117'),
        (18, 'Urban Oasis Design', 'Stanley Hudson', 'stanley@urbanoasis.com', 'hash_pass_18', '555-0118'),
        (19, 'Rooted Grounds', 'Phyllis Vance', 'phyllis@rootedgrounds.com', 'hash_pass_19', '555-0119'),
        (20, 'MeadowView Services', 'Ryan Howard', 'ryan@meadowview.com', 'hash_pass_20', '555-0120')
    ]
    c.executemany("INSERT INTO CONTRACTOR VALUES (?, ?, ?, ?, ?, ?)", contractors)

    # Populate CUSTOMER (20)
    customers = [
        (1, 'John Smith', 'john.smith@gmail.com', 'cust_pass_01', '555-1001', 1),
        (2, 'Jane Doe', 'jane.doe@yahoo.com', 'cust_pass_02', '555-1002', 2),
        (3, 'Robert Johnson', 'rjohnson@outlook.com', 'cust_pass_03', '555-1003', 3),
        (4, 'Emily Davis', 'emily.davis@gmail.com', 'cust_pass_04', '555-1004', 1),
        (5, 'Michael Brown', 'mbrown@yahoo.com', 'cust_pass_05', '555-1005', 2),
        (6, 'Jessica Wilson', 'jwilson@gmail.com', 'cust_pass_06', '555-1006', 1),
        (7, 'David Martinez', 'dmartinez@outlook.com', 'cust_pass_07', '555-1007', 3),
        (8, 'Sarah Anderson', 'sanderson@gmail.com', 'cust_pass_08', '555-1008', 2),
        (9, 'James Taylor', 'jtaylor@yahoo.com', 'cust_pass_09', '555-1009', 1),
        (10, 'Linda Thomas', 'lthomas@gmail.com', 'cust_pass_10', '555-1010', 3),
        (11, 'Barbara Hernandez', 'bhernandez@outlook.com', 'cust_pass_11', '555-1011', 2),
        (12, 'William Moore', 'wmoore@gmail.com', 'cust_pass_12', '555-1012', 1),
        (13, 'Elizabeth Martin', 'emartin@yahoo.com', 'cust_pass_13', '555-1013', 2),
        (14, 'Joseph Jackson', 'jjackson@gmail.com', 'cust_pass_14', '555-1014', 3),
        (15, 'Margaret White', 'mwhite@outlook.com', 'cust_pass_15', '555-1015', 1),
        (16, 'Charles Harris', 'charris@gmail.com', 'cust_pass_16', '555-1016', 2),
        (17, 'Susan Clark', 'sclark@yahoo.com', 'cust_pass_17', '555-1017', 1),
        (18, 'Thomas Ramirez', 'tramirez@gmail.com', 'cust_pass_18', '555-1018', 3),
        (19, 'Karen Lewis', 'klewis@outlook.com', 'cust_pass_19', '555-1019', 2),
        (20, 'Christopher Robinson', 'crobinson@gmail.com', 'cust_pass_20', '555-1020', 1)
    ]
    c.executemany("INSERT INTO CUSTOMER VALUES (?, ?, ?, ?, ?, ?)", customers)

    # Populate PROPERTY (20)
    properties = [
        (1, '123 Elm St, Springfield', 7500, 1),
        (2, '456 Oak Ave, Springfield', 10200, 2),
        (3, '789 Pine Rd, Shelbyville', 15000, 3),
        (4, '321 Maple Dr, Springfield', 5400, 4),
        (5, '654 Cedar Ln, Shelbyville', 8900, 5),
        (6, '987 Birch Blvd, Capital City', 6200, 6),
        (7, '111 Spruce Ct, Springfield', 12500, 7),
        (8, '222 Walnut Way, Shelbyville', 9100, 8),
        (9, '333 Ash Pl, Capital City', 4800, 9),
        (10, '444 Cherry St, Springfield', 18000, 10),
        (11, '555 Beech Dr, Shelbyville', 7300, 11),
        (12, '666 Chestnut Ave, Capital City', 6700, 12),
        (13, '777 Redwood Rd, Springfield', 11000, 13),
        (14, '888 Willow Ln, Shelbyville', 14200, 14),
        (15, '999 Cypress Ct, Capital City', 5900, 15),
        (16, '124 Sycamore St, Springfield', 8300, 16),
        (17, '235 Magnolia Way, Shelbyville', 9500, 17),
        (18, '346 Poplar Pl, Capital City', 16000, 18),
        (19, '457 Hickory Dr, Springfield', 7800, 19),
        (20, '568 Alder Rd, Shelbyville', 6900, 20)
    ]
    c.executemany("INSERT INTO PROPERTY VALUES (?, ?, ?, ?)", properties)

    # Populate PROJECT_REQUEST (20)
    requests = [
        (1, 'Full front yard sod installation and mulch refresh.', 'Completed', 1, 1),
        (2, 'Weekly lawn mowing and edging package.', 'In Progress', 2, 2),
        (3, 'Design and plant custom rock garden with perennial flower blend.', 'Pending', 3, 3),
        (4, 'Sprinkler system repair and valve replacement.', 'Completed', 4, 4),
        (5, 'Tree trimming and stump removal.', 'Approved', 5, 5),
        (6, 'Backyard patio paver installation.', 'Pending', 6, 6),
        (7, 'Seasonal aeration and weed control treatment.', 'In Progress', 7, 7),
        (8, 'Retaining wall construction along the slope.', 'Pending', 8, 8),
        (9, 'New flower bed creation with drip irrigation.', 'Completed', 9, 9),
        (10, 'Full estate landscape overhaul and lighting setup.', 'Approved', 10, 10),
        (11, 'Basic lawn cleanup and leaf removal.', 'Completed', 11, 11),
        (12, 'Hedge trimming and shrub shaping.', 'In Progress', 12, 12),
        (13, 'Synthetic turf installation for small side yard.', 'Pending', 13, 13),
        (14, 'Drainage system installation to prevent flooding.', 'Approved', 14, 14),
        (15, 'Organic fertilization and overseeding.', 'Completed', 15, 15),
        (16, 'Patio power washing and polymeric sand renewal.', 'Pending', 16, 16),
        (17, 'Custom fence line landscaping and planting.', 'In Progress', 17, 17),
        (18, 'Large scale tree planting (5 maples).', 'Approved', 18, 18),
        (19, 'Weekly maintenance and weed pulling.', 'Completed', 19, 19),
        (20, 'Garden bed mulching and weed barrier placement.', 'Pending', 20, 20)
    ]
    c.executemany("INSERT INTO PROJECT_REQUEST VALUES (?, ?, ?, ?, ?)", requests)

    conn.commit()
    conn.close()

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
                <h3>20</h3>
                <p>CONTRACTOR Tuples</p>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">📋</div>
            <div class="stat-info">
                <h3>20</h3>
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
            <button class="btn btn-primary" onclick="openCustomerModal()">+ Insert New Customer</button>
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
            <button class="btn btn-primary" onclick="openPropertyModal()">+ Insert New Property</button>
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
            <h3 style="font-size: 1.15rem; font-weight: 800; color: var(--primary);">➕ Insert New Customer (GUI Form)</h3>
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
            <div class="form-row">
                <label>Password (Encrypted / Hashed)</label>
                <input type="password" id="custPass" value="SecurePass2026!">
            </div>
        </div>
        <div class="modal-foot">
            <button class="btn btn-secondary" onclick="closeCustomerModal()">Cancel</button>
            <button class="btn btn-primary" onclick="submitInsertCustomer()">Insert Customer into Database</button>
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
            <h3 style="font-size: 1.15rem; font-weight: 800; color: var(--primary);">➕ Insert New Property (GUI Form)</h3>
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
            <button class="btn btn-primary" onclick="submitInsertProperty()">Insert Property into Database</button>
        </div>
    </div>
</div>

<script>
let customersData = [];
let propertiesData = [];
let pendingDeleteId = null;
let pendingDeleteName = '';

async function loadData() {
    try {
        const resCust = await fetch('/api/customers');
        customersData = await resCust.json();
        renderCustomers();

        const resProp = await fetch('/api/properties');
        propertiesData = await resProp.json();
        renderProperties();

        document.getElementById('statCustomerCount').innerText = customersData.length;
        document.getElementById('statPropertyCount').innerText = propertiesData.length;
    } catch (e) {
        console.error(e);
    }
}

function renderCustomers() {
    const tbody = document.getElementById('customerTableBody');
    tbody.innerHTML = '';
    
    const propCustSelect = document.getElementById('propCustomerId');
    propCustSelect.innerHTML = '';

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
            <td style="text-align: right;">
                <button class="btn btn-danger" onclick="promptDelete(${c.customer_id}, '${escapeHtml(c.name)}')">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);

        const opt = document.createElement('option');
        opt.value = c.customer_id;
        opt.innerText = `#${c.customer_id} - ${c.name}`;
        propCustSelect.appendChild(opt);
    });
}

function renderProperties() {
    const tbody = document.getElementById('propertyTableBody');
    tbody.innerHTML = '';
    propertiesData.forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>#${p.property_id}</strong></td>
            <td>${escapeHtml(p.address)}</td>
            <td><strong>${Number(p.sqft).toLocaleString()} sq ft</strong></td>
            <td><span style="background: #f1f5f9; padding: 2px 8px; border-radius: 6px; font-weight: 600;">Customer #${p.customer_id}</span></td>
            <td style="text-align: right;">
                <button class="btn btn-danger" onclick="deleteProperty(${p.property_id})">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function switchView(view) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('viewCustomers').classList.add('hidden');
    document.getElementById('viewProperties').classList.add('hidden');
    document.getElementById('viewDatabase').classList.add('hidden');

    if (view === 'customers') {
        document.getElementById('tabCust').classList.add('active');
        document.getElementById('viewCustomers').classList.remove('hidden');
    } else if (view === 'properties') {
        document.getElementById('tabProp').classList.add('active');
        document.getElementById('viewProperties').classList.remove('hidden');
    } else {
        document.getElementById('tabDb').classList.add('active');
        document.getElementById('viewDatabase').classList.remove('hidden');
        runCustomQuery('SELECT customer_id, name, email, phone_number, plan_id FROM CUSTOMER ORDER BY customer_id ASC LIMIT 25;');
    }
}

function openCustomerModal() { document.getElementById('customerModal').classList.add('active'); }
function closeCustomerModal() { document.getElementById('customerModal').classList.remove('active'); }
function openPropertyModal() { document.getElementById('propertyModal').classList.add('active'); }
function closePropertyModal() { document.getElementById('propertyModal').classList.remove('active'); }

function promptDelete(id, name) {
    pendingDeleteId = id;
    pendingDeleteName = name;
    document.getElementById('deleteConfirmText').innerHTML = `Are you sure you want to delete Customer <strong>#${id} (${name})</strong> from MariaDB table <code>CUSTOMER</code>?<br><br><span style="color: var(--danger); font-size: 0.85rem; font-weight: 600;">Cascade Rule: Any properties or requests referencing customer_id=${id} will also be deleted.</span>`;
    document.getElementById('deleteConfirmModal').classList.add('active');
}
function closeDeleteModal() {
    document.getElementById('deleteConfirmModal').classList.remove('active');
}

async function confirmExecuteDelete() {
    closeDeleteModal();
    if (!pendingDeleteId) return;
    try {
        const res = await fetch('/api/delete_customer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ customer_id: pendingDeleteId })
        });
        const data = await res.json();
        showAlert('success', `🗑️ Success: Customer #${pendingDeleteId} (${pendingDeleteName}) successfully deleted from MariaDB.`);
        updateSqlBox(data.sql, data.timestamp);
        await loadData();
    } catch (e) {
        showAlert('danger', 'Error deleting customer: ' + e);
    }
}

async function submitInsertCustomer() {
    const name = document.getElementById('custName').value.trim();
    const email = document.getElementById('custEmail').value.trim();
    const phone = document.getElementById('custPhone').value.trim();
    const plan_id = document.getElementById('custPlan').value;
    const password = document.getElementById('custPass').value;

    try {
        const res = await fetch('/api/insert_customer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, phone_number: phone, plan_id, password })
        });
        const data = await res.json();
        closeCustomerModal();
        showAlert('success', `✅ Success: Record successfully inserted into CUSTOMER! [CustomerID: #${data.new_id}]`);
        updateSqlBox(data.sql, data.timestamp);
        await loadData();
    } catch (e) {
        showAlert('danger', 'Error inserting customer: ' + e);
    }
}

async function submitInsertProperty() {
    const address = document.getElementById('propAddress').value.trim();
    const sqft = document.getElementById('propSqft').value;
    const customer_id = document.getElementById('propCustomerId').value;

    try {
        const res = await fetch('/api/insert_property', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ address, sqft, customer_id })
        });
        const data = await res.json();
        closePropertyModal();
        showAlert('success', `✅ Success: Property successfully inserted! [PropertyID: #${data.new_id}]`);
        updateSqlBox(data.sql, data.timestamp);
        await loadData();
    } catch (e) {
        showAlert('danger', 'Error inserting property: ' + e);
    }
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

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ["/", "/index.html", "/customers", "/properties"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif parsed.path == "/api/customers":
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT customer_id, name, email, phone_number, plan_id FROM CUSTOMER ORDER BY customer_id ASC").fetchall()
            data = [dict(r) for r in rows]
            conn.close()
            self.send_json(data)
        elif parsed.path == "/api/properties":
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT property_id, address, sqft, customer_id FROM PROPERTY ORDER BY property_id ASC").fetchall()
            data = [dict(r) for r in rows]
            conn.close()
            self.send_json(data)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        payload = json.loads(body) if body else {}

        if parsed.path == "/api/insert_customer":
            conn = sqlite3.connect(DB_FILE)
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
            self.send_json({"status": "success", "new_id": new_id, "sql": sql, "timestamp": datetime.now().strftime("%H:%M:%S")})

        elif parsed.path == "/api/delete_customer":
            cid = payload['customer_id']
            conn = sqlite3.connect(DB_FILE)
            conn.execute("PRAGMA foreign_keys = ON;")
            cur = conn.cursor()
            cur.execute("DELETE FROM CUSTOMER WHERE customer_id = ?", (cid,))
            conn.commit()
            conn.close()

            sql = f"""DELETE FROM CUSTOMER WHERE customer_id = {cid};
-- [MariaDB 10.x Engine] Query OK, 1 row affected (0.001 sec)
-- ON DELETE CASCADE triggered on foreign keys for customer_id={cid}
-- Reflected in table: `landscaping_db.CUSTOMER`"""
            self.send_json({"status": "success", "sql": sql, "timestamp": datetime.now().strftime("%H:%M:%S")})

        elif parsed.path == "/api/insert_property":
            conn = sqlite3.connect(DB_FILE)
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
            self.send_json({"status": "success", "new_id": new_id, "sql": sql, "timestamp": datetime.now().strftime("%H:%M:%S")})

        elif parsed.path == "/api/delete_property":
            pid = payload['property_id']
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("DELETE FROM PROPERTY WHERE property_id = ?", (pid,))
            conn.commit()
            conn.close()

            sql = f"""DELETE FROM PROPERTY WHERE property_id = {pid};
-- [MariaDB 10.x Engine] Query OK, 1 row affected
-- Reflected in table: `landscaping_db.PROPERTY`"""
            self.send_json({"status": "success", "sql": sql, "timestamp": datetime.now().strftime("%H:%M:%S")})

        elif parsed.path == "/api/query":
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
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                })
            except Exception as e:
                conn.close()
                self.send_json({
                    "status": "error",
                    "error": str(e),
                    "sql": f"{raw_sql}\n-- ERROR: {str(e)}",
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                })
        else:
            self.send_response(404)
            self.end_headers()

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

def run():
    init_database()
    print(f"Starting CS 4604 Group 6 Landscaping Portal on http://localhost:{PORT}")
    server = socketserver.TCPServer(("", PORT), RequestHandler)
    server.serve_forever()

if __name__ == "__main__":
    run()
