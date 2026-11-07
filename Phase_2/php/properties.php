<?php
session_start();
require_once __DIR__ . '/header.php';

if (!isset($_SESSION['sample_properties'])) {
    $_SESSION['sample_properties'] = [
        ['property_id' => 1, 'address' => '123 Elm St, Springfield', 'sqft' => 7500, 'customer_id' => 1],
        ['property_id' => 2, 'address' => '456 Oak Ave, Springfield', 'sqft' => 10200, 'customer_id' => 2],
        ['property_id' => 3, 'address' => '789 Pine Rd, Shelbyville', 'sqft' => 15000, 'customer_id' => 3],
        ['property_id' => 4, 'address' => '321 Maple Dr, Springfield', 'sqft' => 5400, 'customer_id' => 4],
        ['property_id' => 5, 'address' => '654 Cedar Ln, Shelbyville', 'sqft' => 8900, 'customer_id' => 5],
        ['property_id' => 6, 'address' => '987 Birch Blvd, Capital City', 'sqft' => 6200, 'customer_id' => 6],
        ['property_id' => 7, 'address' => '111 Spruce Ct, Springfield', 'sqft' => 12500, 'customer_id' => 7],
        ['property_id' => 8, 'address' => '222 Walnut Way, Shelbyville', 'sqft' => 9100, 'customer_id' => 8],
        ['property_id' => 9, 'address' => '333 Ash Pl, Capital City', 'sqft' => 4800, 'customer_id' => 9],
        ['property_id' => 10, 'address' => '444 Cherry St, Springfield', 'sqft' => 18000, 'customer_id' => 10],
        ['property_id' => 11, 'address' => '555 Beech Dr, Shelbyville', 'sqft' => 7300, 'customer_id' => 11],
        ['property_id' => 12, 'address' => '666 Chestnut Ave, Capital City', 'sqft' => 6700, 'customer_id' => 12],
        ['property_id' => 13, 'address' => '777 Redwood Rd, Springfield', 'sqft' => 11000, 'customer_id' => 13],
        ['property_id' => 14, 'address' => '888 Willow Ln, Shelbyville', 'sqft' => 14200, 'customer_id' => 14],
        ['property_id' => 15, 'address' => '999 Cypress Ct, Capital City', 'sqft' => 5900, 'customer_id' => 15],
        ['property_id' => 16, 'address' => '124 Sycamore St, Springfield', 'sqft' => 8300, 'customer_id' => 16],
        ['property_id' => 17, 'address' => '235 Magnolia Way, Shelbyville', 'sqft' => 9500, 'customer_id' => 17],
        ['property_id' => 18, 'address' => '346 Poplar Pl, Capital City', 'sqft' => 16000, 'customer_id' => 18],
        ['property_id' => 19, 'address' => '457 Hickory Dr, Springfield', 'sqft' => 7800, 'customer_id' => 19],
        ['property_id' => 20, 'address' => '568 Alder Rd, Shelbyville', 'sqft' => 6900, 'customer_id' => 20]
    ];
}

$message = '';
$message_type = '';
$executed_sql = '';
$new_id = null;

// INSERT PROPERTY
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action']) && $_POST['action'] === 'insert') {
    $address = trim($_POST['address'] ?? '');
    $sqft = intval($_POST['sqft'] ?? 0);
    $customer_id = intval($_POST['customer_id'] ?? 1);

    if (!empty($address) && $sqft > 0) {
        if ($pdo) {
            try {
                $stmt = $pdo->prepare("INSERT INTO PROPERTY (address, sqft, customer_id) VALUES (?, ?, ?)");
                $stmt->execute([$address, $sqft, $customer_id]);
                $new_id = $pdo->lastInsertId();
                $message = "Property successfully added to database! [PropertyID: #{$new_id}]";
                $message_type = "success";
                $executed_sql = "INSERT INTO PROPERTY (address, sqft, customer_id)\nVALUES ('" . addslashes($address) . "', {$sqft}, {$customer_id});\n-- Query OK, 1 row affected";
            } catch (Exception $e) {
                $message = "Insert Error: " . $e->getMessage();
                $message_type = "danger";
            }
        } else {
            $max_id = max(array_column($_SESSION['sample_properties'], 'property_id'));
            $new_id = $max_id + 1;
            $_SESSION['sample_properties'][] = [
                'property_id' => $new_id,
                'address' => $address,
                'sqft' => $sqft,
                'customer_id' => $customer_id
            ];
            $message = "DEMO MODE: property #{$new_id} added to temporary demo data only (no database connected).";
            $message_type = "warning";
            $executed_sql = "INSERT INTO PROPERTY (address, sqft, customer_id)\nVALUES ('" . addslashes($address) . "', {$sqft}, {$customer_id});\n-- DEMO MODE: no database connected, nothing was saved";
        }
    } else {
        $message = "Please enter valid property address and square footage.";
        $message_type = "danger";
    }
}

// DELETE PROPERTY
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action']) && $_POST['action'] === 'delete') {
    $delete_id = intval($_POST['property_id'] ?? 0);
    if ($delete_id > 0) {
        if ($pdo) {
            try {
                $stmt = $pdo->prepare("DELETE FROM PROPERTY WHERE property_id = ?");
                $stmt->execute([$delete_id]);
                $affected = $stmt->rowCount();
                $message = $affected ? "Property #{$delete_id} successfully deleted from database." : "No PROPERTY row with ID #{$delete_id} was found.";
                $message_type = $affected ? "success" : "warning";
                $executed_sql = "DELETE FROM PROPERTY WHERE property_id = {$delete_id};\n-- Query OK, {$affected} row(s) affected";
            } catch (Exception $e) {
                $message = "Delete Error: " . $e->getMessage();
                $message_type = "danger";
            }
        } else {
            $_SESSION['sample_properties'] = array_values(array_filter($_SESSION['sample_properties'], function($p) use ($delete_id) {
                return $p['property_id'] != $delete_id;
            }));
            $message = "DEMO MODE: property #{$delete_id} removed from temporary demo data only (no database connected).";
            $message_type = "warning";
            $executed_sql = "DELETE FROM PROPERTY WHERE property_id = {$delete_id};\n-- DEMO MODE: no database connected, nothing was saved";
        }
    }
}

$properties = [];
if ($pdo) {
    try {
        $stmt = $pdo->query("SELECT * FROM PROPERTY ORDER BY property_id ASC");
        $properties = $stmt->fetchAll();
    } catch (Exception $e) {
        $message = "Could not read PROPERTY table: " . $e->getMessage();
        $message_type = "danger";
    }
} else {
    $properties = $_SESSION['sample_properties'];
}
?>

<div class="page-header">
    <div class="page-title">
        <h1>🏡 Property Management (Major Table)</h1>
        <p>Demonstrating GUI Insert and Delete Functionality connected to <code>PROPERTY</code> table</p>
    </div>
    <div>
        <button class="btn btn-primary" onclick="openInsertModal()">+ Insert New Property</button>
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
            <span style="color: #94a3b8; font-size: 0.8rem;">Database: landscaping_db &bull; Table: PROPERTY</span>
        </div>
        <pre class="sql-code"><code><?= htmlspecialchars($executed_sql) ?></code></pre>
    </div>
<?php endif; ?>

<div class="table-card">
    <div class="table-header-bar">
        <div class="table-title">PROPERTY Table Tuples</div>
        <span class="table-count-badge"><?= count($properties) ?> Tuples in Database</span>
    </div>

    <div style="overflow-x: auto;">
        <table class="data-table">
            <thead>
                <tr>
                    <th>property_id (PK)</th>
                    <th>address</th>
                    <th>sqft</th>
                    <th>customer_id (FK)</th>
                    <th style="text-align: right;">Action</th>
                </tr>
            </thead>
            <tbody>
                <?php foreach ($properties as $row): ?>
                <tr class="<?= ($new_id && $row['property_id'] == $new_id) ? 'highlight-new' : '' ?>">
                    <td><strong>#<?= htmlspecialchars($row['property_id']) ?></strong></td>
                    <td><?= htmlspecialchars($row['address']) ?></td>
                    <td><?= number_format($row['sqft']) ?> sq ft</td>
                    <td>Customer #<?= htmlspecialchars($row['customer_id']) ?></td>
                    <td style="text-align: right;">
                        <form method="POST" action="properties.php" style="display: inline;" onsubmit="return confirm('Delete property #<?= $row['property_id'] ?>?');">
                            <input type="hidden" name="action" value="delete">
                            <input type="hidden" name="property_id" value="<?= $row['property_id'] ?>">
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
            <h2 class="modal-title">➕ Insert New Property into Database</h2>
            <button class="btn btn-outline btn-sm" onclick="closeInsertModal()" style="padding: 0.2rem 0.5rem;">✕</button>
        </div>
        <form method="POST" action="properties.php">
            <div class="modal-body">
                <input type="hidden" name="action" value="insert">
                <div class="form-grid">
                    <div class="form-group" style="grid-column: 1 / -1;">
                        <label for="address">Street Address, City *</label>
                        <input type="text" id="address" name="address" class="form-control" placeholder="e.g. 742 Evergreen Terrace, Springfield" required>
                    </div>
                    <div class="form-group">
                        <label for="sqft">Lot Size (Sq Ft) *</label>
                        <input type="number" id="sqft" name="sqft" class="form-control" placeholder="e.g. 8500" required>
                    </div>
                    <div class="form-group">
                        <label for="customer_id">Associated Customer ID (FK)</label>
                        <input type="number" id="customer_id" name="customer_id" class="form-control" value="1" required>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeInsertModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Add Property to Database</button>
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
