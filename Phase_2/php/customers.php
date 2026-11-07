<?php
session_start();
require_once __DIR__ . '/header.php';

// Fallback initial sample data matching phpMyAdmin Phase 1
if (!isset($_SESSION['sample_customers'])) {
    $_SESSION['sample_customers'] = [
        ['customer_id' => 1, 'name' => 'John Smith', 'email' => 'john.smith@gmail.com', 'password' => 'cust_pass_01', 'phone_number' => '555-1001', 'plan_id' => 1],
        ['customer_id' => 2, 'name' => 'Jane Doe', 'email' => 'jane.doe@yahoo.com', 'password' => 'cust_pass_02', 'phone_number' => '555-1002', 'plan_id' => 2],
        ['customer_id' => 3, 'name' => 'Robert Johnson', 'email' => 'rjohnson@outlook.com', 'password' => 'cust_pass_03', 'phone_number' => '555-1003', 'plan_id' => 3],
        ['customer_id' => 4, 'name' => 'Emily Davis', 'email' => 'emily.davis@gmail.com', 'password' => 'cust_pass_04', 'phone_number' => '555-1004', 'plan_id' => 1],
        ['customer_id' => 5, 'name' => 'Michael Brown', 'email' => 'mbrown@yahoo.com', 'password' => 'cust_pass_05', 'phone_number' => '555-1005', 'plan_id' => 2],
        ['customer_id' => 6, 'name' => 'Jessica Wilson', 'email' => 'jwilson@gmail.com', 'password' => 'cust_pass_06', 'phone_number' => '555-1006', 'plan_id' => 1],
        ['customer_id' => 7, 'name' => 'David Martinez', 'email' => 'dmartinez@outlook.com', 'password' => 'cust_pass_07', 'phone_number' => '555-1007', 'plan_id' => 3],
        ['customer_id' => 8, 'name' => 'Sarah Anderson', 'email' => 'sanderson@gmail.com', 'password' => 'cust_pass_08', 'phone_number' => '555-1008', 'plan_id' => 2],
        ['customer_id' => 9, 'name' => 'James Taylor', 'email' => 'jtaylor@yahoo.com', 'password' => 'cust_pass_09', 'phone_number' => '555-1009', 'plan_id' => 1],
        ['customer_id' => 10, 'name' => 'Linda Thomas', 'email' => 'lthomas@gmail.com', 'password' => 'cust_pass_10', 'phone_number' => '555-1010', 'plan_id' => 3],
        ['customer_id' => 11, 'name' => 'Barbara Hernandez', 'email' => 'bhernandez@outlook.com', 'password' => 'cust_pass_11', 'phone_number' => '555-1011', 'plan_id' => 2],
        ['customer_id' => 12, 'name' => 'William Moore', 'email' => 'wmoore@gmail.com', 'password' => 'cust_pass_12', 'phone_number' => '555-1012', 'plan_id' => 1],
        ['customer_id' => 13, 'name' => 'Elizabeth Martin', 'email' => 'emartin@yahoo.com', 'password' => 'cust_pass_13', 'phone_number' => '555-1013', 'plan_id' => 2],
        ['customer_id' => 14, 'name' => 'Joseph Jackson', 'email' => 'jjackson@gmail.com', 'password' => 'cust_pass_14', 'phone_number' => '555-1014', 'plan_id' => 3],
        ['customer_id' => 15, 'name' => 'Margaret White', 'email' => 'mwhite@outlook.com', 'password' => 'cust_pass_15', 'phone_number' => '555-1015', 'plan_id' => 1],
        ['customer_id' => 16, 'name' => 'Charles Harris', 'email' => 'charris@gmail.com', 'password' => 'cust_pass_16', 'phone_number' => '555-1016', 'plan_id' => 2],
        ['customer_id' => 17, 'name' => 'Susan Clark', 'email' => 'sclark@yahoo.com', 'password' => 'cust_pass_17', 'phone_number' => '555-1017', 'plan_id' => 1],
        ['customer_id' => 18, 'name' => 'Thomas Ramirez', 'email' => 'tramirez@gmail.com', 'password' => 'cust_pass_18', 'phone_number' => '555-1018', 'plan_id' => 3],
        ['customer_id' => 19, 'name' => 'Karen Lewis', 'email' => 'klewis@outlook.com', 'password' => 'cust_pass_19', 'phone_number' => '555-1019', 'plan_id' => 2],
        ['customer_id' => 20, 'name' => 'Christopher Robinson', 'email' => 'crobinson@gmail.com', 'password' => 'cust_pass_20', 'phone_number' => '555-1020', 'plan_id' => 1]
    ];
}

$message = '';
$message_type = '';
$executed_sql = '';
$new_id = null;

// ==========================================
// HANDLE INSERT OPERATION
// ==========================================
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action']) && $_POST['action'] === 'insert') {
    $name = trim($_POST['name'] ?? '');
    $email = trim($_POST['email'] ?? '');
    $password = trim($_POST['password'] ?? '');
    $phone = trim($_POST['phone_number'] ?? '');
    $plan_id = intval($_POST['plan_id'] ?? 1);

    if (!empty($name) && !empty($email) && !empty($phone)) {
        if ($pdo) {
            try {
                $stmt = $pdo->prepare("INSERT INTO CUSTOMER (name, email, password, phone_number, plan_id) VALUES (?, ?, ?, ?, ?)");
                $stmt->execute([$name, $email, $password, $phone, $plan_id]);
                $new_id = $pdo->lastInsertId();
                $message = "Record successfully inserted into CUSTOMER! [CustomerID: #{$new_id}]";
                $message_type = "success";
                $executed_sql = "INSERT INTO CUSTOMER (name, email, password, phone_number, plan_id)\nVALUES ('" . addslashes($name) . "', '" . addslashes($email) . "', '" . addslashes($password) . "', '" . addslashes($phone) . "', {$plan_id});\n-- Query OK, 1 row affected\n-- Reflected in MariaDB table `{$db_name}.CUSTOMER`";
            } catch (Exception $e) {
                $message = "Database Insert Error: " . $e->getMessage();
                $message_type = "danger";
            }
        } else {
            // Standalone / fallback mode
            $max_id = max(array_column($_SESSION['sample_customers'], 'customer_id'));
            $new_id = $max_id + 1;
            $_SESSION['sample_customers'][] = [
                'customer_id' => $new_id,
                'name' => $name,
                'email' => $email,
                'password' => $password,
                'phone_number' => $phone,
                'plan_id' => $plan_id
            ];
            $message = "DEMO MODE: customer #{$new_id} added to temporary demo data only (no database connected).";
            $message_type = "warning";
            $executed_sql = "INSERT INTO CUSTOMER (name, email, password, phone_number, plan_id)\nVALUES ('" . addslashes($name) . "', '" . addslashes($email) . "', '" . addslashes($password) . "', '" . addslashes($phone) . "', {$plan_id});\n-- DEMO MODE: no database connected, nothing was saved";
        }
    } else {
        $message = "Please fill in all required fields (Name, Email, Phone Number).";
        $message_type = "danger";
    }
}

// ==========================================
// HANDLE DELETE OPERATION
// ==========================================
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action']) && $_POST['action'] === 'delete') {
    $delete_id = intval($_POST['customer_id'] ?? 0);
    if ($delete_id > 0) {
        if ($pdo) {
            try {
                $stmt = $pdo->prepare("DELETE FROM CUSTOMER WHERE customer_id = ?");
                $stmt->execute([$delete_id]);
                $affected = $stmt->rowCount();
                $message = $affected ? "Record successfully deleted from CUSTOMER! [CustomerID: #{$delete_id}]" : "No CUSTOMER row with ID #{$delete_id} was found.";
                $message_type = $affected ? "success" : "warning";
                $executed_sql = "DELETE FROM CUSTOMER WHERE customer_id = {$delete_id};\n-- Query OK, {$affected} row(s) affected\n-- ON DELETE CASCADE removes this customer's dependent rows.";
            } catch (Exception $e) {
                $message = "Database Delete Error: " . $e->getMessage();
                $message_type = "danger";
            }
        } else {
            // Standalone / fallback mode
            $initial_count = count($_SESSION['sample_customers']);
            $_SESSION['sample_customers'] = array_values(array_filter($_SESSION['sample_customers'], function($c) use ($delete_id) {
                return $c['customer_id'] != $delete_id;
            }));
            $message = "DEMO MODE: customer #{$delete_id} removed from temporary demo data only (no database connected).";
            $message_type = "warning";
            $executed_sql = "DELETE FROM CUSTOMER WHERE customer_id = {$delete_id};\n-- DEMO MODE: no database connected, nothing was saved";
        }
    }
}

// Fetch customers list
$customers = [];
if ($pdo) {
    try {
        $stmt = $pdo->query("SELECT * FROM CUSTOMER ORDER BY customer_id ASC");
        $customers = $stmt->fetchAll();
    } catch (Exception $e) {
        $message = "Could not read CUSTOMER table: " . $e->getMessage();
        $message_type = "danger";
    }
} else {
    $customers = $_SESSION['sample_customers'];
}
?>

<div class="page-header">
    <div class="page-title">
        <h1>👥 Customer Management (Major Table)</h1>
        <p>Demonstrating GUI Insert and Delete Functionality connected to <code>CUSTOMER</code> table</p>
    </div>
    <div>
        <button class="btn btn-primary" onclick="openInsertModal()">+ Insert New Customer</button>
    </div>
</div>

<?php if ($message): ?>
    <div class="alert alert-<?= $message_type ?>">
        <span style="font-size: 1.25rem;"><?= $message_type === 'success' ? '✅' : '⚠️' ?></span>
        <div><?= htmlspecialchars($message) ?></div>
    </div>
<?php endif; ?>

<?php if ($executed_sql): ?>
    <div class="sql-reflection-box">
        <div class="sql-header">
            <span class="sql-badge">MariaDB Query Reflection</span>
            <span style="color: #94a3b8; font-size: 0.8rem;">Database: landscaping_db &bull; Table: CUSTOMER</span>
        </div>
        <pre class="sql-code"><code><?= htmlspecialchars($executed_sql) ?></code></pre>
    </div>
<?php endif; ?>

<div class="table-card">
    <div class="table-header-bar">
        <div class="table-title">CUSTOMER Table Tuples</div>
        <span class="table-count-badge"><?= count($customers) ?> Tuples in Database</span>
    </div>

    <div style="overflow-x: auto;">
        <table class="data-table">
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
            <tbody>
                <?php foreach ($customers as $row): ?>
                <tr class="<?= ($new_id && $row['customer_id'] == $new_id) ? 'highlight-new' : '' ?>">
                    <td><strong>#<?= htmlspecialchars($row['customer_id']) ?></strong></td>
                    <td><?= htmlspecialchars($row['name']) ?></td>
                    <td><?= htmlspecialchars($row['email']) ?></td>
                    <td><?= htmlspecialchars($row['phone_number']) ?></td>
                    <td>
                        <span style="background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.75rem;">
                            Plan #<?= htmlspecialchars($row['plan_id'] ?? 1) ?>
                        </span>
                    </td>
                    <td style="text-align: right;">
                        <form method="POST" action="customers.php" style="display: inline;" onsubmit="return confirm('Are you sure you want to DELETE Customer #<?= $row['customer_id'] ?> (<?= htmlspecialchars($row['name']) ?>) from the database?');">
                            <input type="hidden" name="action" value="delete">
                            <input type="hidden" name="customer_id" value="<?= $row['customer_id'] ?>">
                            <button type="submit" class="btn btn-danger btn-sm">Delete</button>
                        </form>
                    </td>
                </tr>
                <?php endforeach; ?>
            </tbody>
        </table>
    </div>
</div>

<!-- INSERT MODAL -->
<div class="modal-backdrop" id="insertModal">
    <div class="modal-box">
        <div class="modal-header">
            <h2 class="modal-title">➕ Insert New Customer into Database</h2>
            <button class="btn btn-outline btn-sm" onclick="closeInsertModal()" style="padding: 0.2rem 0.5rem;">✕</button>
        </div>
        <form method="POST" action="customers.php">
            <div class="modal-body">
                <input type="hidden" name="action" value="insert">
                <div class="form-grid">
                    <div class="form-group">
                        <label for="name">Customer Name *</label>
                        <input type="text" id="name" name="name" class="form-control" placeholder="e.g. Michael Scott" required>
                    </div>
                    <div class="form-group">
                        <label for="email">Email Address *</label>
                        <input type="email" id="email" name="email" class="form-control" placeholder="m.scott@dundermifflin.com" required>
                    </div>
                    <div class="form-group">
                        <label for="phone_number">Phone Number *</label>
                        <input type="tel" id="phone_number" name="phone_number" class="form-control" placeholder="555-0199" required>
                    </div>
                    <div class="form-group">
                        <label for="plan_id">Subscription Plan (FK)</label>
                        <select id="plan_id" name="plan_id" class="form-control">
                            <option value="1">Plan 1 - Basic Homeowner ($19.99/mo)</option>
                            <option value="2">Plan 2 - Pro Landscaper ($49.99/mo)</option>
                            <option value="3">Plan 3 - Enterprise Contractor ($99.99/mo)</option>
                        </select>
                    </div>
                    <div class="form-group" style="grid-column: 1 / -1;">
                        <label for="password">Account Password</label>
                        <input type="password" id="password" name="password" class="form-control" value="SecurePass2026!" required>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeInsertModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Add Customer to Database</button>
            </div>
        </form>
    </div>
</div>

<script>
function openInsertModal() {
    document.getElementById('insertModal').classList.add('open');
}
function closeInsertModal() {
    document.getElementById('insertModal').classList.remove('open');
}
</script>

<?php require_once __DIR__ . '/footer.php'; ?>
