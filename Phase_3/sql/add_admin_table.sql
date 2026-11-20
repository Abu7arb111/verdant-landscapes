-- Adds the ADMIN table to a landscaping_db that was created before user accounts existed.
-- The server creates this table itself on startup; run this file in phpMyAdmin only if the
-- app's database account is not allowed to CREATE tables.
-- No admin row is inserted. Create the first administrator with:
--   py Phase_3/app/server.py create-admin <username>
CREATE TABLE IF NOT EXISTS ADMIN (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_admin_creator FOREIGN KEY (created_by)
        REFERENCES ADMIN(admin_id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;
