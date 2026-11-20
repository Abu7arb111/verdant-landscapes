-- ==============================================================================
-- CS 4604: INTRODUCTION TO DATABASE SYSTEMS
-- Team 6: Landscaping AI Estimator
-- Team Members: Zachary Brosius, Saveer Pande, Benny He, Ahmad Abu Harb
-- Schema DDL, 30 sample tuples per entity table, views, triggers and indexes
-- DBMS: MariaDB / MySQL (InnoDB Engine)
-- Database: landscaping_db
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS landscaping_db;
USE landscaping_db;

-- Drop existing tables in reverse dependency order
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS ADMIN;
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

-- 13. ADMIN (application administrators; customers and contractors log in with their own tables)
-- No admin is seeded. Create the first one with:  py Phase_3/app/server.py create-admin <username>
-- That admin can change their password and add more admins inside the app.
CREATE TABLE ADMIN (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_admin_creator FOREIGN KEY (created_by)
        REFERENCES ADMIN(admin_id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- ==============================================================================
-- POPULATE SAMPLE DATA (30 Tuples per Entity Table)
-- ==============================================================================

-- SUBSCRIPTION_PLAN
INSERT INTO SUBSCRIPTION_PLAN (plan_id, plan_name, price, tier) VALUES
(1, 'Basic Homeowner', 19.99, 'Tier 1'),
(2, 'Pro Landscaper', 49.99, 'Tier 2'),
(3, 'Enterprise Contractor', 99.99, 'Tier 3');

-- CONTRACTOR (20 Tuples)
INSERT INTO CONTRACTOR (contractor_id, business_name, contact_name, email, password, phone_number) VALUES
(1, 'GreenThumb Landscaping', 'Alice Green', 'alice@greenthumb.com', 'pbkdf2-sha256$600000$0782278d7c771af6bfa295ec1e6280a0$99097bbdf5cef7da076af031ad7ee746ec24c73ff056f897576f2d8d4e830996', '555-0101'),
(2, 'EcoLawn Pro Services', 'Bob Builder', 'bob@ecolawn.com', 'pbkdf2-sha256$600000$d963a6d102360d4b8dd0abf252d129c5$297b5466f60d475501f156527bb593f828db1653e819a5fddd8193ccbac38ac8', '555-0102'),
(3, 'Elite Turf & Design', 'Charlie Brown', 'charlie@eliteturf.com', 'pbkdf2-sha256$600000$bccc08decf451efa0f5f1c8b2d976e2d$53e06c43780acb23cf4d3d35e3c80799e44b13d10fc5b80832ead0a4ed70e260', '555-0103'),
(4, 'Vibrant Yard Co.', 'Diana Prince', 'diana@vibrantyard.com', 'pbkdf2-sha256$600000$60cc21e96d57a7ebc97d8c25c9ba8761$be018611b20ab2e28e1a1e9d5c41f7dfcdc6731dc1f8cae4564390d38f568a24', '555-0104'),
(5, 'Serene Gardens LLC', 'Evan Wright', 'evan@serenegardens.com', 'pbkdf2-sha256$600000$35ec46b4568fc60eb89a6c91a833d72d$6e60b5bd250c316d98ae26534f62a49752ab513c4331d29eb21b0cf83831a6e4', '555-0105'),
(6, 'Prime Mowing & More', 'Fiona Gallagher', 'fiona@primemowing.com', 'pbkdf2-sha256$600000$344390be49eb28eb7ced6c41b0adbf43$bfa04fa83f98966dff85e6374c3e94ae4f0f196aaaf22a7d5f8c32b08758c546', '555-0106'),
(7, 'Absolute Outdoors', 'George Miller', 'george@absoluteoutdoors.com', 'pbkdf2-sha256$600000$cbbe0e4069d7d3cb5b24eacbc8ea6f68$4a041f168e274d969a88528fa702dc0e1a5b0c1a3d2e558b7d1374997c89bf59', '555-0107'),
(8, 'TerraLandscapes', 'Hannah Abbott', 'hannah@terralandscapes.com', 'pbkdf2-sha256$600000$9d4678caf5ffac5851c9e420dfe4e3df$464d960823f9aea4cf9f33e6917425e2729c68cd1c40df14ec7e20a086a625da', '555-0108'),
(9, 'SunValley Yard Care', 'Ian Malcolm', 'ian@sunvalleyyard.com', 'pbkdf2-sha256$600000$f11a3b56ac613d9a86358d2c569eafff$db9f7169182c41d45793c4ba4c24a949af52e420c315dcddb0df8dc590920bfb', '555-0109'),
(10, 'Lush Lawn Masters', 'Julia Roberts', 'julia@lushlawn.com', 'pbkdf2-sha256$600000$49fbbdf4dba8f93dacd9400ee277ab17$9de2f6f486d9e52745293e2e1f9e97c7629cf24559077aec34f92f7b75f1c5a6', '555-0110'),
(11, 'Precision Cuts', 'Kevin Bacon', 'kevin@precisioncuts.com', 'pbkdf2-sha256$600000$e0204f91746a74249affc8728cfd63d3$b847b82d6ae28e6c137978c4ecf833edf56682fbc7f6543e674d21a5f8791db6', '555-0111'),
(12, 'NatureCraft Design', 'Laura Croft', 'laura@naturecraft.com', 'pbkdf2-sha256$600000$4338a9abebd5268227cefce943cc553a$e3705c614db6ee38f0097b669c9eaeac90c07a3ecbd8c6d5374f712267e03f45', '555-0112'),
(13, 'Blossom & Branch', 'Michael Scott', 'michael@blossombranch.com', 'pbkdf2-sha256$600000$ee26d2856df9c0554ed622427c19f95f$b28771920f5b79607dbd690a620d2ac9c68d1fa3153dd03c5cfc1b45b8d6c1c1', '555-0113'),
(14, 'Apex Yard Care', 'Pam Beesly', 'pam@apexyard.com', 'pbkdf2-sha256$600000$c0b71817d8597dae1032995a09d7239d$33c786eac878eb22cadb51be2fef8266651d479ba3ffc612077415d13ce0e40b', '555-0114'),
(15, 'Sod & Stone Pros', 'Jim Halpert', 'jim@sodstone.com', 'pbkdf2-sha256$600000$573c839b47b87df5a0131bf3bde42108$205a51642c04e50b2a59dc76d104d8cb9a9cf5c5889df6897a1a93503802e65e', '555-0115'),
(16, 'Evergreen Experts', 'Dwight Schrute', 'dwight@evergreenexperts.com', 'pbkdf2-sha256$600000$88115039d2e8d306cd0c6df4ed9d5ec6$ac6f1361ef74bb0ad88b1572bd861eab80a0351d272cadd229c90f6ce5def3b3', '555-0116'),
(17, 'BlueSky Landscaping', 'Angela Martin', 'angela@bluesky.com', 'pbkdf2-sha256$600000$0fc48edd5faec3e7ea2df1d41a515fbb$26923a64b6eb04fce3fc6907e09bb47e57fcfb5cd97c27e7196bee79ff9f6905', '555-0117'),
(18, 'Urban Oasis Design', 'Stanley Hudson', 'stanley@urbanoasis.com', 'pbkdf2-sha256$600000$876fe34a3ff99b9bdfe851bae897534e$ccfb8397a8c0527bf70d866731f1a2bbb31a84ef277ac2451d1ec64e88aef53a', '555-0118'),
(19, 'Rooted Grounds', 'Phyllis Vance', 'phyllis@rootedgrounds.com', 'pbkdf2-sha256$600000$fdeaee63b12756997745a61bd8ac5f12$f9382bdea2c56b434d89c404c852d0d5c2a19298c37b8d6c30a5296c7312688a', '555-0119'),
(20, 'MeadowView Services', 'Ryan Howard', 'ryan@meadowview.com', 'pbkdf2-sha256$600000$d302c1aa7fa4c80fcf16f30faba76f43$e344bd2cdd41891653ec29f3d179b3abf582eb70d8ef2bdc1cc2670a02824c68', '555-0120');

-- CUSTOMER (20 Tuples)
INSERT INTO CUSTOMER (customer_id, name, email, password, phone_number, plan_id) VALUES
(1, 'John Smith', 'john.smith@gmail.com', 'pbkdf2-sha256$600000$d188f4da657c07f6343fe92dce40ae36$b81e0c51d8a48d564b160fcc051685b3b2a3663c6ac353e8125db454ec87557d', '555-1001', 1),
(2, 'Jane Doe', 'jane.doe@yahoo.com', 'pbkdf2-sha256$600000$136d5cd78fd027801d992780f9fdc199$1cce28cff55388bae0fda9273ad961a71882255f1d9a58192a0ddd401e6dd905', '555-1002', 2),
(3, 'Robert Johnson', 'rjohnson@outlook.com', 'pbkdf2-sha256$600000$e11d99526b0c5d1042c86a0a8fbc56c9$f59603ad37e22c1a36ccd73b19e667ae98a2fdb3aaa95b98fdfd7a8846be7b36', '555-1003', 3),
(4, 'Emily Davis', 'emily.davis@gmail.com', 'pbkdf2-sha256$600000$d0f0df32c5480558f651c51c6f6c29fa$d3bc8e53c4173e147ed132da1035894558fdbf27a62ccd85faaff982cab0ec20', '555-1004', 1),
(5, 'Michael Brown', 'mbrown@yahoo.com', 'pbkdf2-sha256$600000$1cab19fea99e0f79a62add90b54312db$8ecfeaf080e6b821efc0eb5d5241b701fd43e77d24956afbb379f5e49faa4dee', '555-1005', 2),
(6, 'Jessica Wilson', 'jwilson@gmail.com', 'pbkdf2-sha256$600000$90262e3ecda884e4732750921782958a$20196064778954cab25eb0d5fbd17f7a9c5aae47445dd61a44f5fa49dc222c17', '555-1006', 1),
(7, 'David Martinez', 'dmartinez@outlook.com', 'pbkdf2-sha256$600000$7b2c407f88dc2f20725fa0cf540d18e5$3abc0afccb50326a6aa97f8a46f37db1fd43c9b0de192886f6215a0d3d5b4f73', '555-1007', 3),
(8, 'Sarah Anderson', 'sanderson@gmail.com', 'pbkdf2-sha256$600000$21c520ec985fd3fde737cb7d7ac7d5f2$97554dc6ef60565d5a51e46f05b19cc7806c7ce38619138e3748a24494cf0b86', '555-1008', 2),
(9, 'James Taylor', 'jtaylor@yahoo.com', 'pbkdf2-sha256$600000$a285b1406ed5cab20f836f0d656b38b6$f9a13f7af6c3d8ffdce2288267ac834d794e7918c7340697b6a91a9cb0e6efae', '555-1009', 1),
(10, 'Linda Thomas', 'lthomas@gmail.com', 'pbkdf2-sha256$600000$a6c969e5b12ba85d811afb8303caa10a$b51eae857466dd97ed34f7b99e2d3932010e17e565e6667cde49eab7abf88476', '555-1010', 3),
(11, 'Barbara Hernandez', 'bhernandez@outlook.com', 'pbkdf2-sha256$600000$bb5e1bbfa5f136cc4c304693e739dbfc$0f264d7a0f0d70aaf3b5a040fb3987ebe28dba07c05d6e4a42ef6cdedeeeb9bc', '555-1011', 2),
(12, 'William Moore', 'wmoore@gmail.com', 'pbkdf2-sha256$600000$78aab262fadcc380c950c2773f341d91$88fd6e5e01c007f209e9876e533a428167a532d72eeacccbcbfbe0dbadb0aa81', '555-1012', 1),
(13, 'Elizabeth Martin', 'emartin@yahoo.com', 'pbkdf2-sha256$600000$840601a59ddbbd3a0238efabadc849e3$9d25ca37ac070b26b46cc5060e3cfe32193262cb5fe04b733ab89f6fe0b54c75', '555-1013', 2),
(14, 'Joseph Jackson', 'jjackson@gmail.com', 'pbkdf2-sha256$600000$c1f01273a309ec3f248cd6f281b4068f$ef9f741b5505b1ab526fd47657a0625406f6a989d2d630df2d7dfc8684b50f57', '555-1014', 3),
(15, 'Margaret White', 'mwhite@outlook.com', 'pbkdf2-sha256$600000$dbbc82b5e83ed1387dc8cb3b89171656$77c217d7f182afb3b889245a53ea54a5abd4c0500b78c87396f8863e2347ffa6', '555-1015', 1),
(16, 'Charles Harris', 'charris@gmail.com', 'pbkdf2-sha256$600000$d75043be56ab492c92b82bfc63ea0b81$db770190708f6968194b9b3f1e611d357bddad4a37cb890d166b1b13a3d2d4a6', '555-1016', 2),
(17, 'Susan Clark', 'sclark@yahoo.com', 'pbkdf2-sha256$600000$87f7852900d3c5baed5b36646f6b2a2f$7e524c31e5f800d03661ec551afc8dcd15f9281a7adb42cc8f41627152e752f0', '555-1017', 1),
(18, 'Thomas Ramirez', 'tramirez@gmail.com', 'pbkdf2-sha256$600000$acf0405843b0c84386af89a94245373e$d03c76d3d16a98fb274225a5fb9951ff9e8d70fc816ec78c70a7db7b3a1fcf52', '555-1018', 3),
(19, 'Karen Lewis', 'klewis@outlook.com', 'pbkdf2-sha256$600000$0a93715741c2d7f2f1a869371d7cffdf$f3e823b778bdc4d84cfe67d12995a79ac44b493234b56a589a8914c4d0b6cdc5', '555-1019', 2),
(20, 'Christopher Robinson', 'crobinson@gmail.com', 'pbkdf2-sha256$600000$b434590b45cbc25a5b7f5d70300acf2e$ed0432349a346a0bbc506b322033dad77e23ae2f7c8d03cab3ebdf693c6ec0aa', '555-1020', 1);

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


-- Additional sample data: rows 21-30 for every entity table (30 tuples each),
-- with dates from June to December 2026. Quotes 31-34 are competing bids that lost.
-- Sample customer and contractor passwords are hashes of random values; set a known one
-- with:  py Phase_3/app/server.py reset-password <customer|contractor> <email>

INSERT INTO CONTRACTOR (contractor_id, business_name, contact_name, email, password, phone_number) VALUES
(21, 'Ridgeline Hardscapes', 'Oscar Martinez', 'oscar@ridgelinehardscapes.com', 'pbkdf2-sha256$600000$7522f6c900b25f419c4386fce965bbe8$1409cd2d021f2dbc080ff3ec515c9f0a78a2aff5c0aed2bc59a6783e7f52f53c', '757-5521'),
(22, 'Coastal Greenery', 'Kelly Kapoor', 'kelly@coastalgreenery.com', 'pbkdf2-sha256$600000$56d2f38401b231e290fdc7233ed6de05$bf44af2ba2801e362d46c0dbdd9add18dddb87b148eb9aab98a1f9e5d947cbd6', '757-5522'),
(23, 'Hampton Roads Turf', 'Toby Flenderson', 'toby@hrturf.com', 'pbkdf2-sha256$600000$13d82ecf71a3b1f1d97769135858616f$64f2d78622e2d5fe163061ec88a2d63aa7a1899bbb769f0982baa3e0d51e1829', '757-5523'),
(24, 'Tidewater Tree Service', 'Meredith Palmer', 'meredith@tidewatertree.com', 'pbkdf2-sha256$600000$fa1cdbe0f6041b9efa2d471af48d6d78$efff935ba8e252a70fb37e954f9da978b892bcb9a5923abb3c3dbbf57cbd7660', '757-5524'),
(25, 'Brightpath Lighting & Landscape', 'Creed Bratton', 'creed@brightpathlandscape.com', 'pbkdf2-sha256$600000$f9b246ef8822baf5138804f59cc7f836$226ee3314bdda69b8107d2f524647fe3a3bf204fb0f6f7171b9be3c53e45a15a', '757-5525'),
(26, 'Chesapeake Irrigation Co.', 'Darryl Philbin', 'darryl@chesapeakeirrigation.com', 'pbkdf2-sha256$600000$2c842a7b7800b99b4cc1d21fb75124e4$16e8f9d0e1a9bd6c97f76c23701c42f79223ba1bd1e9a0865594382ecec62cdd', '757-5526'),
(27, 'Stonebridge Patios', 'Erin Hannon', 'erin@stonebridgepatios.com', 'pbkdf2-sha256$600000$110341fe98a7d060877de82fc160c441$7cc11b221e56d71c1338ccb04d2a48fef31290b21d67db74922e7f2b7cdac403', '757-5527'),
(28, 'Bayside Lawn & Garden', 'Gabe Lewis', 'gabe@baysidelawn.com', 'pbkdf2-sha256$600000$dd7ba5ae2c7a0af0ae23bba25be4d851$5ecc6494ee5485308b4c567b1ef4e32144189257791e71f72a2acfec5b490609', '757-5528'),
(29, 'Fernwood Native Plants', 'Holly Flax', 'holly@fernwoodnative.com', 'pbkdf2-sha256$600000$ffd25358e5306c2db816fb87c32979a3$f6e509bd2410535e8aa705a5003da08b56c85a0ad7390e5d16f908e5e4922591', '757-5529'),
(30, 'Summit Grading & Drainage', 'Andy Bernard', 'andy@summitgrading.com', 'pbkdf2-sha256$600000$b86c050593e0a59983ef4e2c2ad8e99d$eb2334fd492e17dbf5f89ceb8a40b3008a694dc2a360667bf03389a2781e4b8f', '757-5530');

INSERT INTO CUSTOMER (customer_id, name, email, password, phone_number, plan_id) VALUES
(21, 'Daniel Young', 'daniel.young@gmail.com', 'pbkdf2-sha256$600000$9f57496424b4e8be9741ba15b0f372ba$37c8f5a84b063d241054cde18b82a74ea2701543e8d0fb1f9d7fff75e5a4e64c', '757-2021', 2),
(22, 'Olivia King', 'olivia.king@outlook.com', 'pbkdf2-sha256$600000$1dbfeba90152f29b92774a825a722274$3a75f686985f4a430ebb5858993aeac05848eefcfe7c3ff2f0e1de158b7a30bc', '757-2022', 1),
(23, 'Matthew Wright', 'mwright@yahoo.com', 'pbkdf2-sha256$600000$d0a95a143ab5f4128ac7a7914b814a67$f5edce397a05a3bbf7e7de54490059a8fc53e7db9d52656598e38e6ede6dcf2a', '757-2023', 3),
(24, 'Sophia Lopez', 'sophia.lopez@gmail.com', 'pbkdf2-sha256$600000$cfa3bc0eb698adce0db981068fb543b6$f30e597c8ce722f80fdc39070b73c92fbfc732780b32985dbd392fc4debc8b1a', '757-2024', 2),
(25, 'Anthony Hill', 'ahill@outlook.com', 'pbkdf2-sha256$600000$1d1a1509457b74bfce2f5b6d77420a95$97109defc7d497ed81c5335e6fb3114b512dbf704cb769cb1b99f7edb4c0215f', '757-2025', 1),
(26, 'Isabella Scott', 'isabella.scott@gmail.com', 'pbkdf2-sha256$600000$835d9f491e5c0c365a906073de06cd53$119d4fcf8ad877c1ffa744fbc323a8edcd47fd608f2a533bcce521b037e5f208', '757-2026', 3),
(27, 'Mark Green', 'mark.green@yahoo.com', 'pbkdf2-sha256$600000$f94f11f714c2033ca1dd8604e38933fe$0c4bd2f3a19f39b92819db92393c83d664fda7ff90a810daf4d7094ee6a0d67d', '757-2027', 2),
(28, 'Ava Adams', 'ava.adams@gmail.com', 'pbkdf2-sha256$600000$dd7b9a0a50ddfba5913a3892aa666be7$8733ea1ab05125a1cb260e006b59f169e5770b1b22bf30b1fb1ca541ef78c488', '757-2028', 1),
(29, 'Steven Baker', 'sbaker@outlook.com', 'pbkdf2-sha256$600000$b9acd1d177326a44944436c83d611139$92a4b44346db6c564214777eae2fff6fec349e13d1a6c40a7d48c0f525101572', '757-2029', 3),
(30, 'Mia Nelson', 'mia.nelson@gmail.com', 'pbkdf2-sha256$600000$14cdc46e6fc42e6550a972d21ffadcfb$8b3e9176850753d7382dc0fdd3e781f16b3a3db40530dc6f7601b29af8db8fe7', '757-2030', 2);

INSERT INTO PROPERTY (property_id, address, sqft, customer_id) VALUES
(21, '1301 Atlantic Ave, Virginia Beach', 8200, 21),
(22, '2417 Shore Dr, Virginia Beach', 5600, 22),
(23, '88 Lynnhaven Pkwy, Virginia Beach', 13400, 23),
(24, '515 Granby St, Norfolk', 4300, 24),
(25, '3920 Holland Rd, Virginia Beach', 9700, 25),
(26, '72 Battlefield Blvd, Chesapeake', 21000, 26),
(27, '640 Great Neck Rd, Virginia Beach', 11800, 27),
(28, '1150 Mercury Blvd, Hampton', 6100, 28),
(29, '27 Kempsville Rd, Norfolk', 7400, 29),
(30, '905 Princess Anne Rd, Virginia Beach', 15600, 30);

INSERT INTO PROJECT_REQUEST (request_id, description, status, customer_id, property_id) VALUES
(21, 'Paver patio with built-in fire pit and seating wall.', 'Completed', 21, 21),
(22, 'Replace front lawn with drought-tolerant native beds.', 'Completed', 22, 22),
(23, 'Full backyard sod and sprinkler system installation.', 'Completed', 23, 23),
(24, 'Remove two storm-damaged pines and grind stumps.', 'Completed', 24, 24),
(25, 'Low-voltage landscape lighting for driveway and garden.', 'In Progress', 25, 25),
(26, 'Regrade side yard and install French drain to stop pooling.', 'In Progress', 26, 26),
(27, 'Flagstone walkway from driveway to back gate.', 'Approved', 27, 27),
(28, 'Raised vegetable garden beds with drip irrigation.', 'Completed', 28, 28),
(29, 'Fall cleanup, aeration and overseeding.', 'Completed', 29, 29),
(30, 'Backyard pergola area with gravel patio and plantings.', 'Approved', 30, 30);

INSERT INTO PHOTO (photo_id, file_type, file_url, request_id) VALUES
(21, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req21_before.jpg', 21),
(22, 'image/png', 'https://storage.landscapingtool.com/photos/req22_before.png', 22),
(23, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req23_before.jpg', 23),
(24, 'image/png', 'https://storage.landscapingtool.com/photos/req24_before.png', 24),
(25, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req25_before.jpg', 25),
(26, 'image/png', 'https://storage.landscapingtool.com/photos/req26_before.png', 26),
(27, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req27_before.jpg', 27),
(28, 'image/png', 'https://storage.landscapingtool.com/photos/req28_before.png', 28),
(29, 'image/jpeg', 'https://storage.landscapingtool.com/photos/req29_before.jpg', 29),
(30, 'image/png', 'https://storage.landscapingtool.com/photos/req30_before.png', 30);

INSERT INTO AI_ESTIMATE (ai_id, estimated_price, estimated_prop_size, ideas_generated, request_id) VALUES
(21, 6800.00, 8200, 'Herringbone travertine pavers, round fire pit, 18-inch seat wall.', 21),
(22, 3200.00, 5600, 'Switchgrass, coneflower and black-eyed Susan beds with pine straw.', 22),
(23, 9400.00, 13400, 'Zoysia sod with a 6-zone smart irrigation controller.', 23),
(24, 1900.00, 4300, 'Crane-assisted removal of two 60-foot pines plus stump grinding.', 24),
(25, 2600.00, 9700, '14 warm-white LED path and up-lights on two timer zones.', 25),
(26, 5200.00, 21000, '120-foot French drain to a pop-up emitter with yard regrading.', 26),
(27, 3800.00, 11800, 'Irregular bluestone flagstone path with polymeric sand joints.', 27),
(28, 1400.00, 6100, 'Four cedar raised beds with drip lines on a battery timer.', 28),
(29, 650.00, 7400, 'Leaf removal, core aeration and tall fescue overseed.', 29),
(30, 8700.00, 15600, 'Cedar pergola over pea-gravel patio with climbing jasmine.', 30);

INSERT INTO CONTRACTOR_QUOTE (quote_id, scope, final_price, status, contractor_id, ai_id) VALUES
(21, 'Excavation, base, pavers, fire pit kit and seat wall.', 7150.00, 'Accepted', 21, 21),
(22, 'Sod removal, soil amendment, native plantings and pine straw.', 2980.00, 'Accepted', 22, 22),
(23, 'Grading, 6-zone irrigation, Zoysia sod and first mow.', 9900.00, 'Accepted', 23, 23),
(24, 'Tree removal, stump grinding and debris haul-away.', 2100.00, 'Accepted', 24, 24),
(25, 'Fixtures, transformer, trenching and timer setup.', 2450.00, 'Accepted', 25, 25),
(26, 'Regrading, trenching, perforated pipe, gravel and emitter.', 5600.00, 'Accepted', 26, 26),
(27, 'Base prep, bluestone flagstone and polymeric sand.', 3650.00, 'Accepted', 27, 27),
(28, 'Four cedar beds, soil fill and drip irrigation kit.', 1350.00, 'Accepted', 28, 28),
(29, 'Leaf cleanup, core aeration and overseeding.', 620.00, 'Accepted', 29, 29),
(30, 'Pergola build, gravel patio and border plantings.', 8950.00, 'Accepted', 30, 30),
(31, 'Alternative bid: excavation, base, pavers, fire pit kit and seat wall.', 7400.00, 'Rejected', 6, 21),
(32, 'Alternative bid: grading, 6-zone irrigation, Zoysia sod and first mow.', 10400.00, 'Rejected', 15, 23),
(33, 'Alternative bid: regrading, trenching, perforated pipe, gravel and emitter.', 5900.00, 'Rejected', 8, 26),
(34, 'Alternative bid: pergola build, gravel patio and border plantings.', 9600.00, 'Rejected', 10, 30);

INSERT INTO APPOINTMENT (appointment_id, scheduled, status, customer_id, contractor_id, request_id) VALUES
(21, '2026-05-27 09:00:00', 'Completed', 21, 21, 21),
(22, '2026-06-10 10:30:00', 'Completed', 22, 22, 22),
(23, '2026-06-29 08:00:00', 'Completed', 23, 23, 23),
(24, '2026-07-17 13:00:00', 'Completed', 24, 24, 24),
(25, '2026-08-04 15:00:00', 'Completed', 25, 25, 25),
(26, '2026-09-01 09:30:00', 'Completed', 26, 26, 26),
(27, '2026-11-05 11:00:00', 'Confirmed', 27, 27, 27),
(28, '2026-09-30 14:00:00', 'Completed', 28, 28, 28),
(29, '2026-10-14 10:00:00', 'Completed', 29, 29, 29),
(30, '2026-11-11 09:00:00', 'Confirmed', 30, 30, 30);

INSERT INTO JOB (job_id, status, start_date, end_date, revenue, expenses, quote_id, contractor_id) VALUES
(21, 'Completed', '2026-06-02', '2026-06-09', 7150.00, 4100.00, 21, 21),
(22, 'Completed', '2026-06-16', '2026-06-19', 2980.00, 1500.00, 22, 22),
(23, 'Completed', '2026-07-06', '2026-07-14', 9900.00, 6200.00, 23, 23),
(24, 'Completed', '2026-07-21', '2026-07-22', 2100.00, 900.00, 24, 24),
(25, 'Completed', '2026-08-10', '2026-08-12', 2450.00, 1100.00, 25, 25),
(26, 'In Progress', '2026-09-08', NULL, 5600.00, 2800.00, 26, 26),
(27, 'Scheduled', '2026-11-30', NULL, 3650.00, 1900.00, 27, 27),
(28, 'Completed', '2026-10-05', '2026-10-07', 1350.00, 600.00, 28, 28),
(29, 'Completed', '2026-10-19', '2026-10-19', 620.00, 220.00, 29, 29),
(30, 'Scheduled', '2026-12-07', NULL, 8950.00, 5100.00, 30, 30);

INSERT INTO INVOICE (invoice_id, amount_due, issued, due_date, status, job_id) VALUES
(21, 7150.00, '2026-06-10', '2026-07-10', 'Paid', 21),
(22, 2980.00, '2026-06-20', '2026-07-20', 'Paid', 22),
(23, 9900.00, '2026-07-15', '2026-08-15', 'Paid', 23),
(24, 2100.00, '2026-07-23', '2026-08-23', 'Paid', 24),
(25, 2450.00, '2026-08-13', '2026-09-13', 'Pending', 25),
(26, 5600.00, '2026-09-15', '2026-10-15', 'Issued', 26),
(27, 3650.00, '2026-11-10', '2026-12-10', 'Issued', 27),
(28, 1350.00, '2026-10-08', '2026-11-08', 'Paid', 28),
(29, 620.00, '2026-10-20', '2026-11-19', 'Overdue', 29),
(30, 8950.00, '2026-11-16', '2026-12-16', 'Issued', 30);

INSERT INTO PAYMENT (payment_id, amount, payment_date, status, payment_method, invoice_id) VALUES
(21, 7150.00, '2026-06-20', 'Completed', 'Credit Card', 21),
(22, 2980.00, '2026-07-01', 'Completed', 'Debit Card', 22),
(23, 9900.00, '2026-07-30', 'Completed', 'Bank Transfer', 23),
(24, 2100.00, '2026-08-05', 'Completed', 'PayPal', 24),
(25, 1200.00, '2026-08-25', 'Completed', 'Credit Card', 25),
(26, 2000.00, '2026-09-28', 'Completed', 'Bank Transfer', 26),
(27, 3650.00, '2026-11-12', 'Pending', 'Credit Card', 27),
(28, 1350.00, '2026-10-20', 'Completed', 'Debit Card', 28),
(29, 300.00, '2026-11-01', 'Failed', 'PayPal', 29),
(30, 4475.00, '2026-11-18', 'Pending', 'Bank Transfer', 30);

-- ==============================================================================
-- VIEWS, TRIGGERS & INDEXES
-- Written in syntax that runs on both MariaDB and the SQLite copy used by app/server.py.
-- ==============================================================================

-- View 1: one row per job with the customer, property and contractor behind it.
-- Path: JOB -> CONTRACTOR_QUOTE -> AI_ESTIMATE -> PROJECT_REQUEST -> PROPERTY / CUSTOMER
CREATE OR REPLACE VIEW v_job_summary AS
SELECT j.job_id,
       c.name             AS customer_name,
       pr.address         AS property_address,
       k.business_name    AS contractor,
       j.status           AS job_status,
       j.start_date,
       e.estimated_price  AS ai_estimate,
       q.final_price      AS quoted_price,
       j.revenue,
       j.expenses,
       j.revenue - j.expenses AS profit
FROM JOB j
JOIN CONTRACTOR k        ON k.contractor_id = j.contractor_id
JOIN CONTRACTOR_QUOTE q  ON q.quote_id      = j.quote_id
JOIN AI_ESTIMATE e       ON e.ai_id         = q.ai_id
JOIN PROJECT_REQUEST r   ON r.request_id    = e.request_id
JOIN PROPERTY pr         ON pr.property_id  = r.property_id
JOIN CUSTOMER c          ON c.customer_id   = r.customer_id;

-- View 2: each invoice with how much has actually been paid (Completed payments only).
CREATE OR REPLACE VIEW v_invoice_balance AS
SELECT i.invoice_id,
       i.job_id,
       c.name AS customer_name,
       i.amount_due,
       COALESCE(SUM(CASE WHEN p.status = 'Completed' THEN p.amount END), 0) AS amount_paid,
       i.amount_due - COALESCE(SUM(CASE WHEN p.status = 'Completed' THEN p.amount END), 0) AS balance_due,
       i.due_date,
       i.status
FROM INVOICE i
JOIN JOB j               ON j.job_id     = i.job_id
JOIN CONTRACTOR_QUOTE q  ON q.quote_id   = j.quote_id
JOIN AI_ESTIMATE e       ON e.ai_id      = q.ai_id
JOIN PROJECT_REQUEST r   ON r.request_id = e.request_id
JOIN CUSTOMER c          ON c.customer_id = r.customer_id
LEFT JOIN PAYMENT p      ON p.invoice_id = i.invoice_id
GROUP BY i.invoice_id, i.job_id, c.name, i.amount_due, i.due_date, i.status;

-- Triggers: when Completed payments cover an invoice's amount_due, mark the invoice 'Paid'.
-- (Single-statement triggers, so phpMyAdmin imports them without a DELIMITER change.)
CREATE TRIGGER trg_payment_insert_mark_paid
AFTER INSERT ON PAYMENT
FOR EACH ROW
UPDATE INVOICE
SET status = 'Paid'
WHERE invoice_id = NEW.invoice_id
  AND (SELECT COALESCE(SUM(amount), 0) FROM PAYMENT
       WHERE invoice_id = NEW.invoice_id AND status = 'Completed') >= amount_due;

CREATE TRIGGER trg_payment_update_mark_paid
AFTER UPDATE ON PAYMENT
FOR EACH ROW
UPDATE INVOICE
SET status = 'Paid'
WHERE invoice_id = NEW.invoice_id
  AND (SELECT COALESCE(SUM(amount), 0) FROM PAYMENT
       WHERE invoice_id = NEW.invoice_id AND status = 'Completed') >= amount_due;

-- Indexes on the columns the GUI searches and the reports filter on.
-- (InnoDB already indexes every foreign key column automatically.)
CREATE INDEX idx_customer_name         ON CUSTOMER(name);
CREATE INDEX idx_property_address      ON PROPERTY(address);
CREATE INDEX idx_request_status        ON PROJECT_REQUEST(status);
CREATE INDEX idx_job_status            ON JOB(status);
CREATE INDEX idx_invoice_status_due    ON INVOICE(status, due_date);
CREATE INDEX idx_payment_invoice_status ON PAYMENT(invoice_id, status);
