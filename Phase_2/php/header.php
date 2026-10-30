<?php
require_once __DIR__ . '/config.php';
$current_page = basename($_SERVER['PHP_SELF']);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Landscaping AI Estimator | CS 4604 Group 6</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>

<header class="navbar">
    <div class="brand-container">
        <span class="brand-icon">🌿</span>
        <div>
            <div class="brand-title">Landscaping AI Estimator</div>
            <div class="brand-subtitle">CS 4604 Group 6 &bull; Virginia Tech Database Systems</div>
        </div>
    </div>
    
    <nav class="nav-links">
        <a href="index.php" class="nav-link <?= $current_page == 'index.php' ? 'active' : '' ?>">Dashboard</a>
        <a href="customers.php" class="nav-link <?= $current_page == 'customers.php' ? 'active' : '' ?>">Customers (Major)</a>
        <a href="properties.php" class="nav-link <?= $current_page == 'properties.php' ? 'active' : '' ?>">Properties (Major)</a>
        <a href="projects.php" class="nav-link <?= $current_page == 'projects.php' ? 'active' : '' ?>">Projects</a>
        <a href="contractors.php" class="nav-link <?= $current_page == 'contractors.php' ? 'active' : '' ?>">Contractors</a>
    </nav>

    <div class="db-status-pill">
        <span class="status-dot <?= $db_connected ? '' : 'disconnected' ?>"></span>
        <span><?= $db_connected ? 'MariaDB Connected (landscaping_db)' : 'Demo / Standalone Mode' ?></span>
    </div>
</header>
<main class="container">
