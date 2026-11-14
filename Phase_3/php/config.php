<?php
/**
 * Database Configuration & Connection Handler
 * Project: Landscaping AI Estimator
 * Course: CS 4604 - Introduction to Database Systems
 * Group: 6 (Zachary Brosius, Saveer Pande, Benny He, Ahmad Abu Harb)
 * DBMS: MariaDB 10.x / MySQL
 * Database: landscaping_db
 */

// Database credentials. Put your real Discovery values in config.local.php
// (copy config.local.example.php). That file is git-ignored so the password
// never gets committed. Environment variables also work.
if (file_exists(__DIR__ . '/config.local.php')) {
    require __DIR__ . '/config.local.php';
}
$db_host = $db_host ?? (getenv('DB_HOST') ?: '127.0.0.1');
$db_port = $db_port ?? (getenv('DB_PORT') ?: '3306');
$db_name = $db_name ?? (getenv('DB_NAME') ?: 'landscaping_db');
$db_user = $db_user ?? (getenv('DB_USER') ?: 'landscaping_user');
$db_pass = $db_pass ?? (getenv('DB_PASS') ?: '');

$pdo = null;
$db_connected = false;
$connection_error = '';

try {
    $dsn = "mysql:host={$db_host};port={$db_port};dbname={$db_name};charset=utf8mb4";
    $options = [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ];
    $pdo = new PDO($dsn, $db_user, $db_pass, $options);
    $db_connected = true;
} catch (PDOException $e) {
    // If MariaDB is not running or credentials differ, fallback gracefully for UI preview
    $connection_error = $e->getMessage();
    $db_connected = false;
}

/**
 * Helper to get table count
 */
function get_table_count($pdo, $table_name) {
    if (!$pdo) return 20; // fallback sample count
    try {
        $stmt = $pdo->query("SELECT COUNT(*) as cnt FROM `{$table_name}`");
        $row = $stmt->fetch();
        return $row ? (int)$row['cnt'] : 0;
    } catch (Exception $e) {
        return 0;
    }
}
?>
