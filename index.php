<?php
// File paths
$scheduleFile = '/var/www/html/timelimits/schedule.json'; // Schedule file
$clientIpFile = '/var/www/html/timelimits/client_ip.json'; // Client IP storage
$statusFile = '/var/www/html/timelimits/status.json'; // Internet status

// Read schedule
$schedule = file_exists($scheduleFile) ? json_decode(file_get_contents($scheduleFile), true) : ['disable_time' => '22:00', 'enable_time' => '06:00'];

// Read clients
$clients = file_exists($clientIpFile) ? json_decode(file_get_contents($clientIpFile), true) : [];

// Read internet status
$status = file_exists($statusFile) ? json_decode(file_get_contents($statusFile), true) : ['status' => 'unpaused', 'manual' => false];

// Function to log messages for debugging
function logMessage($message) {
    error_log("[" . date("Y-m-d H:i:s") . "] $message\n", 3, "/var/log/timelimits.log");
}

// Function to send commands
function sendCommand($command, $clientIp) {
    $socket = @socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
    if (!$socket) {
        logMessage("Socket creation failed for $clientIp.");
        return false;
    }

    if (!@socket_connect($socket, $clientIp, 65432)) {
        logMessage("Failed to connect to client at $clientIp.");
        socket_close($socket);
        return false;
    }

    socket_write($socket, $command, strlen($command));
    $response = @socket_read($socket, 1024);
    socket_close($socket);

    logMessage("Command '$command' sent to $clientIp. Response: $response");
    return $response ?: "No response from client.";
}

// Handle form submissions
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_POST['schedule'])) {
        $schedule = [
            'disable_time' => $_POST['disable_time'],
            'enable_time' => $_POST['enable_time'],
        ];
        file_put_contents($scheduleFile, json_encode($schedule));
        logMessage("Schedule updated to: " . json_encode($schedule));
    } elseif (isset($_POST['command']) && isset($_POST['client_ip'])) {
        $command = $_POST['command'];
        $clientIp = $_POST['client_ip'];
        sendCommand($command, $clientIp);

        if ($command === 'pause' || $command === 'unpause') {
            $status['status'] = $command === 'pause' ? 'paused' : 'unpaused';
            $status['manual'] = $command === 'pause';
            file_put_contents($statusFile, json_encode($status));
            logMessage("Manual override: Status updated to: " . json_encode($status));
        }
    }
    header("Location: " . $_SERVER['PHP_SELF']);
    exit;
}

// Enforce downtime schedule only if no manual override
$current_time = date('H:i');
if (!$status['manual']) {
    if ($current_time >= $schedule['disable_time'] && $current_time < $schedule['enable_time']) {
        foreach ($clients as $name => $client) {
            sendCommand('pause', $client['client_ip']);
        }
        $status['status'] = 'paused';
    } else {
        foreach ($clients as $name => $client) {
            sendCommand('unpause', $client['client_ip']);
        }
        $status['status'] = 'unpaused';
    }
    file_put_contents($statusFile, json_encode($status));
    logMessage("Schedule enforced. Status updated to: " . json_encode($status));
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Downtime Central</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background-color: #f8f9fa;
        }
        .container {
            max-width: 400px;
            width: 100%;
            padding: 20px;
            box-sizing: border-box;
            text-align: center;
        }
        h1 {
            font-size: 24px;
            margin-bottom: 20px;
        }
        .box {
            border: 2px solid #ccc;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            background: white;
        }
        .status {
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 20px;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            margin: 10px 0;
        }
        .btn-schedule {
            background-color: #007bff;
            color: white;
        }
        .btn-pause {
            background-color: #dc3545;
            color: white;
        }
        .btn-unpause {
            background-color: #28a745;
            color: white;
        }
        select {
            padding: 10px;
            font-size: 16px;
            margin: 10px 0;
            border: 1px solid #ccc;
            border-radius: 5px;
            width: 100%;
        }
        @media screen and (max-width: 480px) {
            h1 {
                font-size: 20px;
            }
            .status {
                font-size: 16px;
            }
            button {
                font-size: 14px;
            }
            select, input[type="time"] {
                font-size: 14px;
                padding: 8px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Downtime Central</h1>
        <div class="status">
            Current Status:
            <span style="color: <?= ($status['status'] === 'paused') ? 'red' : (($status['status'] === 'unpaused') ? 'green' : 'orange') ?>">
                <?= ucfirst($status['status']) ?>
            </span>
        </div>
        <div class="box">
            <h2>Schedule</h2>
            <p><strong>Downtime On:</strong><br><?= $schedule['disable_time'] ?></p>
            <p><strong>Downtime Off:</strong><br><?= $schedule['enable_time'] ?></p>
            <form method="post">
                <label for="disable_time">Downtime On:</label>
                <input type="time" id="disable_time" name="disable_time" value="<?= $schedule['disable_time'] ?>"><br>
                <label for="enable_time">Downtime Off:</label>
                <input type="time" id="enable_time" name="enable_time" value="<?= $schedule['enable_time'] ?>"><br>
                <button class="btn-schedule" type="submit" name="schedule">Set Schedule</button>
            </form>
        </div>
        <div class="box">
            <h2>Control Internet</h2>
            <form method="post">
                <label for="client_ip">Select Client:</label>
                <select id="client_ip" name="client_ip">
                    <?php foreach ($clients as $name => $client): ?>
                        <option value="<?= htmlspecialchars($client['client_ip']) ?>"><?= htmlspecialchars($name) ?> (<?= htmlspecialchars($client['client_ip']) ?>)</option>
                    <?php endforeach; ?>
                </select><br>
                <button class="btn-pause" type="submit" name="command" value="pause">Pause Internet</button>
                <button class="btn-unpause" type="submit" name="command" value="unpause">Unpause Internet</button>
            </form>
        </div>
    </div>
</body>
</html>
