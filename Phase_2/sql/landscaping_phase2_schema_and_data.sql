-- ==============================================================================
-- CS 4604: INTRODUCTION TO DATABASE SYSTEMS
-- Team 6: Landscaping AI Estimator
-- Team Members: Zachary Brosius, Saveer Pande, Benny He, Ahmad Abu Harb
-- Phase 2: Relational Schema DDL & 20+ Sample Tuples per Major Table
-- DBMS: MariaDB / MySQL (InnoDB Engine)
-- Database: landscaping_db
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS landscaping_db;
USE landscaping_db;

-- Drop existing tables in reverse dependency order
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS PAYMENT;
DROP TABLE IF EXISTS INVOICE;
DROP TABLE IF EXISTS JOB;
DROP TABLE IF EXISTS APPOINTMENT;
DROP TABLE IF EXISTS CONTRACTOR_QUOTE;
DROP TABLE IF EXISTS AI_ESTIMATE;
DROP TABLE IF EXISTS PHOTO;
DROP TABLE IF EXISTS PROJECT_REQUEST;
DROP TABLE IF EXISTS PROPERTY;
DROP TABLE IF EXISTS CUSTOMER;
DROP TABLE IF EXISTS CONTRACTOR;
DROP TABLE IF EXISTS SUBSCRIPTION_PLAN;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. SUBSCRIPTION_PLAN
CREATE TABLE SUBSCRIPTION_PLAN (
    plan_id INT AUTO_INCREMENT PRIMARY KEY,
    plan_name VARCHAR(50) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    tier VARCHAR(50) NOT NULL
) ENGINE=InnoDB;

-- 2. CONTRACTOR
CREATE TABLE CONTRACTOR (
    contractor_id INT AUTO_INCREMENT PRIMARY KEY,
    business_name VARCHAR(100) NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL
) ENGINE=InnoDB;

-- 3. CUSTOMER
CREATE TABLE CUSTOMER (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    plan_id INT,
    CONSTRAINT fk_customer_plan FOREIGN KEY (plan_id)
        REFERENCES SUBSCRIPTION_PLAN(plan_id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- 4. PROPERTY
CREATE TABLE PROPERTY (
    property_id INT AUTO_INCREMENT PRIMARY KEY,
    address VARCHAR(200) NOT NULL,
    sqft INT NOT NULL,
    customer_id INT NOT NULL,
    CONSTRAINT fk_property_customer FOREIGN KEY (customer_id)
        REFERENCES CUSTOMER(customer_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- 5. PROJECT_REQUEST
CREATE TABLE PROJECT_REQUEST (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    description TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    customer_id INT NOT NULL,
    property_id INT NOT NULL,
    CONSTRAINT fk_request_customer FOREIGN KEY (customer_id)
        REFERENCES CUSTOMER(customer_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_request_property FOREIGN KEY (property_id)
        REFERENCES PROPERTY(property_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- 6. PHOTO
CREATE TABLE PHOTO (
    photo_id INT AUTO_INCREMENT PRIMARY KEY,
    file_type VARCHAR(50) NOT NULL,
    file_url VARCHAR(255) NOT NULL,
    request_id INT NOT NULL,
    CONSTRAINT fk_photo_request FOREIGN KEY (request_id)
        REFERENCES PROJECT_REQUEST(request_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- 7. AI_ESTIMATE
CREATE TABLE AI_ESTIMATE (
    ai_id INT AUTO_INCREMENT PRIMARY KEY,
    estimated_price DECIMAL(10,2) NOT NULL,
    estimated_prop_size INT NOT NULL,
    ideas_generated TEXT NOT NULL,
    request_id INT NOT NULL,
    CONSTRAINT fk_estimate_request FOREIGN KEY (request_id)
        REFERENCES PROJECT_REQUEST(request_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- 8. CONTRACTOR_QUOTE
CREATE TABLE CONTRACTOR_QUOTE (
    quote_id INT AUTO_INCREMENT PRIMARY KEY,
    scope TEXT NOT NULL,
    final_price DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    contractor_id INT NOT NULL,
    ai_id INT NOT NULL,
    CONSTRAINT fk_quote_contractor FOREIGN KEY (contractor_id)
        REFERENCES CONTRACTOR(contractor_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_quote_estimate FOREIGN KEY (ai_id)
        REFERENCES AI_ESTIMATE(ai_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- 9. APPOINTMENT
CREATE TABLE APPOINTMENT (
    appointment_id INT AUTO_INCREMENT PRIMARY KEY,
    scheduled DATETIME NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    customer_id INT NOT NULL,
    contractor_id INT NOT NULL,
    request_id INT NOT NULL,
    CONSTRAINT fk_apt_customer FOREIGN KEY (customer_id)
        REFERENCES CUSTOMER(customer_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_apt_contractor FOREIGN KEY (contractor_id)
        REFERENCES CONTRACTOR(contractor_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_apt_request FOREIGN KEY (request_id)
        REFERENCES PROJECT_REQUEST(request_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- 10. JOB
CREATE TABLE JOB (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    status VARCHAR(50) NOT NULL DEFAULT 'Scheduled',
    start_date DATE NOT NULL,
    end_date DATE NULL,
    revenue DECIMAL(10,2) NOT NULL,
    expenses DECIMAL(10,2) NOT NULL,
    quote_id INT NOT NULL,
    contractor_id INT NOT NULL,
    CONSTRAINT fk_job_quote FOREIGN KEY (quote_id)
        REFERENCES CONTRACTOR_QUOTE(quote_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_job_contractor FOREIGN KEY (contractor_id)
        REFERENCES CONTRACTOR(contractor_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- 11. INVOICE
CREATE TABLE INVOICE (
    invoice_id INT AUTO_INCREMENT PRIMARY KEY,
    amount_due DECIMAL(10,2) NOT NULL,
    issued DATE NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Issued',
    job_id INT NOT NULL,
    CONSTRAINT fk_invoice_job FOREIGN KEY (job_id)
        REFERENCES JOB(job_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- 12. PAYMENT
CREATE TABLE PAYMENT (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    amount DECIMAL(10,2) NOT NULL,
    payment_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Completed',
    payment_method VARCHAR(50) NOT NULL,
    invoice_id INT NOT NULL,
    CONSTRAINT fk_payment_invoice FOREIGN KEY (invoice_id)
        REFERENCES INVOICE(invoice_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- ==============================================================================
-- POPULATE SAMPLE DATA (At least 20 Tuples per Major Table)
-- ==============================================================================

-- SUBSCRIPTION_PLAN
INSERT INTO SUBSCRIPTION_PLAN (plan_id, plan_name, price, tier) VALUES
(1, 'Basic Homeowner', 19.99, 'Tier 1'),
(2, 'Pro Landscaper', 49.99, 'Tier 2'),
(3, 'Enterprise Contractor', 99.99, 'Tier 3');

-- CONTRACTOR (20 Tuples)
INSERT INTO CONTRACTOR (contractor_id, business_name, contact_name, email, password, phone_number) VALUES
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
(20, 'MeadowView Services', 'Ryan Howard', 'ryan@meadowview.com', 'hash_pass_20', '555-0120');

-- CUSTOMER (20 Tuples)
INSERT INTO CUSTOMER (customer_id, name, email, password, phone_number, plan_id) VALUES
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
(20, 'Christopher Robinson', 'crobinson@gmail.com', 'cust_pass_20', '555-1020', 1);

-- PROPERTY (20 Tuples)
INSERT INTO PROPERTY (property_id, address, sqft, customer_id) VALUES
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
(20, '568 Alder Rd, Shelbyville', 6900, 20);

-- PROJECT_REQUEST (20 Tuples)
INSERT INTO PROJECT_REQUEST (request_id, description, status, customer_id, property_id) VALUES
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
(20, 'Garden bed mulching and weed barrier placement.', 'Pending', 20, 20);

-- PHOTO (20 Tuples)
INSERT INTO PHOTO (photo_id, file_type, file_url, request_id) VALUES
(1, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req1_before.jpg', 1),
(2, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req1_after.jpg', 1),
(3, 'image/png', 'https://storage.landscapingtool.com/photos/req2_lawn.png', 2),
(4, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req3_design.jpg', 3),
(5, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req4_sprinkler.jpg', 4),
(6, 'image/png', 'https://storage.landscapingtool.com/photos/req5_tree.png', 5),
(7, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req6_patio.jpg', 6),
(8, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req7_weed.jpg', 7),
(9, 'image/png', 'https://storage.landscapingtool.com/photos/req8_wall.png', 8),
(10, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req9_flower.jpg', 9),
(11, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req10_estate.jpg', 10),
(12, 'image/png', 'https://storage.landscapingtool.com/photos/req11_leaves.png', 11),
(13, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req12_hedge.jpg', 12),
(14, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req13_turf.jpg', 13),
(15, 'image/png', 'https://storage.landscapingtool.com/photos/req14_drain.png', 14),
(16, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req15_seed.jpg', 15),
(17, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req16_powerwash.jpg', 16),
(18, 'image/png', 'https://storage.landscapingtool.com/photos/req17_fence.png', 17),
(19, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req18_maples.jpg', 18),
(20, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req20_mulch.jpg', 20);

-- AI_ESTIMATE (20 Tuples)
INSERT INTO AI_ESTIMATE (ai_id, estimated_price, estimated_prop_size, ideas_generated, request_id) VALUES
(1, 1200.00, 7500, 'Recommended Kentucky Bluegrass sod and dark brown mulch.', 1),
(2, 350.00, 10200, 'Weekly maintenance schedule with bi-weekly edge trimming.', 2),
(3, 2400.00, 15000, 'Drought-tolerant xeriscaping layout with river rock.', 3),
(4, 450.00, 5400, 'Replace 3 broken sprinkler heads and adjust spray nozzle angles.', 4),
(5, 800.00, 8900, 'Safe removal of dead oak tree branch hanging over patio.', 5),
(6, 4200.00, 6200, 'Patio layout using gray flagstone pavers and integrated fire pit.', 6),
(7, 300.00, 12500, 'Core aeration coupled with nitrogen-rich organic fertilizer.', 7),
(8, 5500.00, 9100, 'Engineered cinder block retaining wall 3 feet high with drainage.', 8),
(9, 650.00, 4800, 'Curved garden bed layout with black mulch and drip lines.', 9),
(10, 15000.00, 18000, 'Complete estate landscape redesign with smart irrigation system.', 10),
(11, 200.00, 7300, 'Leaf blowing and bagging for standard suburban yard.', 11),
(12, 400.00, 6700, 'Boxwood and privet hedge shaping with organic fertilizer.', 12),
(13, 3100.00, 11000, 'Pet-friendly artificial turf installation with antimicrobial infill.', 13),
(14, 1800.00, 14200, 'French drain system along the northern foundation line.', 14),
(15, 500.00, 5900, 'Fall overseeding with perennial ryegrass blend.', 15),
(16, 350.00, 8300, 'Hot water pressure wash and joint filling with polymeric sand.', 16),
(17, 900.00, 9500, 'Privacy shrub line with arborvitae trees along perimeter.', 17),
(18, 2500.00, 16000, 'Placement of 5 mature autumn blaze maples with support staking.', 18),
(19, 250.00, 7800, 'Routine weeding and bed maintenance.', 19),
(20, 450.00, 6900, 'Shredded bark mulch replenishment (4 cubic yards).', 20);

-- CONTRACTOR_QUOTE (20 Tuples)
INSERT INTO CONTRACTOR_QUOTE (quote_id, scope, final_price, status, contractor_id, ai_id) VALUES
(1, 'Includes labor, sod material, and mulch.', 1250.00, 'Accepted', 1, 1),
(2, 'Standard seasonal contract billed monthly.', 340.00, 'Accepted', 2, 2),
(3, 'Full rock installation including weed barrier fabric.', 2500.00, 'Pending', 3, 3),
(4, 'Sprinkler head replacement and pressure check.', 420.00, 'Accepted', 4, 4),
(5, 'Tree limb removal and debris haul away.', 750.00, 'Accepted', 5, 5),
(6, 'Paver patio installation with base gravel.', 4300.00, 'Pending', 6, 6),
(7, 'Aeration and fertilizer application service.', 290.00, 'Accepted', 7, 7),
(8, 'Retaining wall construction with drainage pipe.', 5400.00, 'Pending', 8, 8),
(9, 'Flower bed edging, mulch, and planting.', 680.00, 'Accepted', 9, 9),
(10, 'Comprehensive estate landscape upgrade.', 14500.00, 'Accepted', 10, 10),
(11, 'Leaf cleanup and disposal.', 190.00, 'Accepted', 11, 11),
(12, 'Shrub pruning and waste cleanup.', 380.00, 'Accepted', 12, 12),
(13, 'Synthetic turf base prep and laying.', 3200.00, 'Pending', 13, 13),
(14, 'French drain trenching and gravel fill.', 1750.00, 'Accepted', 14, 14),
(15, 'Aeration and seed spreading.', 480.00, 'Accepted', 15, 15),
(16, 'Pressure washing patio and walkway.', 340.00, 'Accepted', 16, 16),
(17, 'Arborvitae tree planting and staking.', 920.00, 'Pending', 17, 17),
(18, 'Maple tree delivery and planting.', 2450.00, 'Accepted', 18, 18),
(19, 'Weekly grounds maintenance.', 250.00, 'Accepted', 19, 19),
(20, 'Mulch delivery and spreading.', 440.00, 'Pending', 20, 20);

-- APPOINTMENT (20 Tuples)
INSERT INTO APPOINTMENT (appointment_id, scheduled, status, customer_id, contractor_id, request_id) VALUES
(1, '2026-05-01 09:00:00', 'Completed', 1, 1, 1),
(2, '2026-05-02 10:00:00', 'Scheduled', 2, 2, 2),
(3, '2026-05-03 13:00:00', 'Pending', 3, 3, 3),
(4, '2026-05-04 08:30:00', 'Completed', 4, 4, 4),
(5, '2026-05-05 11:00:00', 'Confirmed', 5, 5, 5),
(6, '2026-05-06 14:00:00', 'Scheduled', 6, 6, 6),
(7, '2026-05-07 09:30:00', 'Completed', 7, 7, 7),
(8, '2026-05-08 15:00:00', 'Pending', 8, 8, 8),
(9, '2026-05-09 10:30:00', 'Completed', 9, 9, 9),
(10, '2026-05-10 08:00:00', 'Confirmed', 10, 10, 10),
(11, '2026-05-11 12:00:00', 'Completed', 11, 11, 11),
(12, '2026-05-12 13:30:00', 'Scheduled', 12, 12, 12),
(13, '2026-05-13 09:00:00', 'Pending', 13, 13, 13),
(14, '2026-05-14 11:30:00', 'Confirmed', 14, 14, 14),
(15, '2026-05-15 14:30:00', 'Completed', 15, 15, 15),
(16, '2026-05-16 10:00:00', 'Completed', 16, 16, 16),
(17, '2026-05-17 11:00:00', 'Pending', 17, 17, 17),
(18, '2026-05-18 08:00:00', 'Confirmed', 18, 18, 18),
(19, '2026-05-19 09:30:00', 'Completed', 19, 19, 19),
(20, '2026-05-20 13:00:00', 'Pending', 20, 20, 20);

-- JOB (20 Tuples)
INSERT INTO JOB (job_id, status, start_date, end_date, revenue, expenses, quote_id, contractor_id) VALUES
(1, 'Completed', '2026-05-01', '2026-05-02', 1250.00, 800.00, 1, 1),
(2, 'In Progress', '2026-05-02', NULL, 340.00, 150.00, 2, 2),
(3, 'Scheduled', '2026-05-05', '2026-05-07', 2500.00, 1400.00, 3, 3),
(4, 'Completed', '2026-05-04', '2026-05-04', 420.00, 200.00, 4, 4),
(5, 'Completed', '2026-05-05', '2026-05-05', 750.00, 350.00, 5, 5),
(6, 'Scheduled', '2026-05-10', '2026-05-12', 4300.00, 2500.00, 6, 6),
(7, 'Completed', '2026-05-07', '2026-05-07', 290.00, 100.00, 7, 7),
(8, 'Scheduled', '2026-05-15', '2026-05-18', 5400.00, 3100.00, 8, 8),
(9, 'Completed', '2026-05-09', '2026-05-09', 680.00, 300.00, 9, 9),
(10, 'In Progress', '2026-05-10', NULL, 14500.00, 9000.00, 10, 10),
(11, 'Completed', '2026-05-11', '2026-05-11', 190.00, 50.00, 11, 11),
(12, 'In Progress', '2026-05-12', NULL, 380.00, 120.00, 12, 12),
(13, 'Scheduled', '2026-05-16', '2026-05-17', 3200.00, 1900.00, 13, 13),
(14, 'Completed', '2026-05-14', '2026-05-14', 1750.00, 900.00, 14, 14),
(15, 'Completed', '2026-05-15', '2026-05-15', 480.00, 200.00, 15, 15),
(16, 'Completed', '2026-05-16', '2026-05-16', 340.00, 110.00, 16, 16),
(17, 'Scheduled', '2026-05-19', '2026-05-19', 920.00, 500.00, 17, 17),
(18, 'Completed', '2026-05-18', '2026-05-18', 2450.00, 1400.00, 18, 18),
(19, 'Completed', '2026-05-19', '2026-05-19', 250.00, 80.00, 19, 19),
(20, 'Scheduled', '2026-05-22', '2026-05-22', 440.00, 200.00, 20, 20);

-- INVOICE (20 Tuples)
INSERT INTO INVOICE (invoice_id, amount_due, issued, due_date, status, job_id) VALUES
(1, 1250.00, '2026-05-02', '2026-06-02', 'Paid', 1),
(2, 340.00, '2026-05-03', '2026-06-03', 'Pending', 2),
(3, 2500.00, '2026-05-04', '2026-06-04', 'Issued', 3),
(4, 420.00, '2026-05-04', '2026-06-04', 'Paid', 4),
(5, 750.00, '2026-05-05', '2026-06-05', 'Paid', 5),
(6, 4300.00, '2026-05-06', '2026-06-06', 'Issued', 6),
(7, 290.00, '2026-05-07', '2026-06-07', 'Paid', 7),
(8, 5400.00, '2026-05-08', '2026-06-08', 'Issued', 8),
(9, 680.00, '2026-05-09', '2026-06-09', 'Paid', 9),
(10, 14500.00, '2026-05-10', '2026-06-10', 'Pending', 10),
(11, 190.00, '2026-05-11', '2026-06-11', 'Paid', 11),
(12, 380.00, '2026-05-12', '2026-06-12', 'Pending', 12),
(13, 3200.00, '2026-05-13', '2026-06-13', 'Issued', 13),
(14, 1750.00, '2026-05-14', '2026-06-14', 'Paid', 14),
(15, 480.00, '2026-05-15', '2026-06-15', 'Paid', 15),
(16, 340.00, '2026-05-16', '2026-06-16', 'Paid', 16),
(17, 920.00, '2026-05-17', '2026-06-17', 'Issued', 17),
(18, 2450.00, '2026-05-18', '2026-06-18', 'Paid', 18),
(19, 250.00, '2026-05-19', '2026-06-19', 'Paid', 19),
(20, 440.00, '2026-05-20', '2026-06-20', 'Issued', 20);

-- PAYMENT (20 Tuples)
INSERT INTO PAYMENT (payment_id, amount, payment_date, status, payment_method, invoice_id) VALUES
(1, 1250.00, '2026-05-02', 'Completed', 'Credit Card', 1),
(2, 340.00, '2026-05-03', 'Pending', 'Bank Transfer', 2),
(3, 2500.00, '2026-05-04', 'Pending', 'Credit Card', 3),
(4, 420.00, '2026-05-04', 'Completed', 'PayPal', 4),
(5, 750.00, '2026-05-05', 'Completed', 'Credit Card', 5),
(6, 4300.00, '2026-05-06', 'Pending', 'Credit Card', 6),
(7, 290.00, '2026-05-07', 'Completed', 'Debit Card', 7),
(8, 5400.00, '2026-05-08', 'Pending', 'Bank Transfer', 8),
(9, 680.00, '2026-05-09', 'Completed', 'Credit Card', 9),
(10, 14500.00, '2026-05-10', 'Pending', 'Bank Transfer', 10),
(11, 190.00, '2026-05-11', 'Completed', 'Credit Card', 11),
(12, 380.00, '2026-05-12', 'Pending', 'PayPal', 12),
(13, 3200.00, '2026-05-13', 'Pending', 'Credit Card', 13),
(14, 1750.00, '2026-05-14', 'Completed', 'Credit Card', 14),
(15, 480.00, '2026-05-15', 'Completed', 'PayPal', 15),
(16, 340.00, '2026-05-16', 'Completed', 'Credit Card', 16),
(17, 920.00, '2026-05-17', 'Pending', 'Bank Transfer', 17),
(18, 2450.00, '2026-05-18', 'Completed', 'Credit Card', 18),
(19, 250.00, '2026-05-19', 'Completed', 'Debit Card', 19),
(20, 440.00, '2026-05-20', 'Pending', 'Credit Card', 20);
