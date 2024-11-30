<?php
// File paths
$scheduleFile = '/var/www/html/timelimits/schedule.json'; // Schedule file
$clientIpFile = '/var/www/html/timelimits/client_ip.json'; // Client IP storage
$statusFile = '/var/www/html/timelimits/status.json'; // Internet status
$logFile = '/var/www/html/timelimits/command_log.txt'; // Log file for commands

// Read schedule
$schedule = file_exists($scheduleFile) ? json_decode(file_get_contents($scheduleFile), true) : ['disable_time' => '22:00', 'enable_time' => '06:00'];

// Read clients
$clients = file_exists($clientIpFile) ? json_decode(file_get_contents($clientIpFile), true) : [];

// Read internet status
$status = file_exists($statusFile) ? json_decode(file_get_contents($statusFile), true) : ['status' => 'unpaused'];

// Function to format time in 12-hour format
function formatTime12Hour($time) {
    return date("g:i A", strtotime($time));
}

// Function to send commands to the client
function sendCommand($command, $clientIp) {
    global $logFile;
    $port = 65432;
    $response = '';

    try {
        $socket = @socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
        if (!$socket) {
            $error = socket_strerror(socket_last_error());
            file_put_contents($logFile, "Socket creation failed: $error\n", FILE_APPEND);
            return "Error: $error";
        }

        if (!@socket_connect($socket, $clientIp, $port)) {
            $error = socket_strerror(socket_last_error());
            file_put_contents($logFile, "Connection to $clientIp:$port failed: $error\n", FILE_APPEND);
            socket_close($socket);
            return "Error: $error";
        }

        socket_write($socket, $command, strlen($command));
        $response = @socket_read($socket, 1024);
        socket_close($socket);

        file_put_contents($logFile, "Command '$command' sent to $clientIp. Response: $response\n", FILE_APPEND);
    } catch (Exception $e) {
        file_put_contents($logFile, "Exception while sending command: " . $e->getMessage() . "\n", FILE_APPEND);
    }

    return $response ?: "No response from client.";
}

// Handle form submissions (for updating schedule and controlling clients manually)
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_POST['schedule'])) {
        $schedule = [
            'disable_time' => $_POST['disable_time'],
            'enable_time' => $_POST['enable_time'],
        ];
        file_put_contents($scheduleFile, json_encode($schedule));
        $message = "Schedule updated successfully.";
    } elseif (isset($_POST['command']) && isset($_POST['client_ip'])) {
        $command = $_POST['command'];
        $clientIp = $_POST['client_ip'];
        $response = sendCommand($command, $clientIp);
        $message = "Command '$command' sent to client $clientIp. Response: $response";
    }
    header("Location: " . $_SERVER['PHP_SELF']);
    exit;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>Downtime Central</h1>

        <!-- Display current status -->
        <div class="status">
            Current Status:
            <span style="color: <?= ($status['status'] === 'pause') ? 'red' : (($status['status'] === 'unpause') ? 'green' : 'orange') ?>">
                <?= ucfirst($status['status']) ?>
            </span>
        </div>

        <!-- Schedule -->
        <div class="box">
            <h2>Schedule</h2>
            <p><strong>Downtime On:</strong><br><?= formatTime12Hour($schedule['disable_time']) ?></p>
            <p><strong>Downtime Off:</strong><br><?= formatTime12Hour($schedule['enable_time']) ?></p>
            <form method="post">
                <label for="disable_time">Downtime On:</label>
                <input type="time" id="disable_time" name="disable_time" value="<?= $schedule['disable_time'] ?>"><br>
                <label for="enable_time">Downtime Off:</label>
                <input type="time" id="enable_time" name="enable_time" value="<?= $schedule['enable_time'] ?>"><br>
                <button class="btn-schedule" type="submit" name="schedule">Set Schedule</button>
            </form>
        </div>

        <!-- Control Internet -->
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
