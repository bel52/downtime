<?php
// File paths
$scheduleFile = '/var/www/html/timelimits/schedule.json'; // Schedule file
$client_ip_file = '/var/www/html/timelimits/client_ip.json'; // Client IP storage
$statusFile = '/var/www/html/timelimits/status.json'; // Status file
$overrideFile = '/var/www/html/timelimits/override.json'; // Override file

// Fetch the client IP dynamically
$client_data = file_exists($client_ip_file) ? json_decode(file_get_contents($client_ip_file), true) : [];
$client_ip = $client_data['client_ip'] ?? 'Not registered'; // Default to fallback message
$client_port = 65432; // Port used by the client

// Function to convert time to 12-hour format
function formatTime12Hour($time) {
    return date("g:i A", strtotime($time));
}

// Function to send commands to the client
function sendCommand($command) {
    global $client_ip, $client_port, $statusFile, $overrideFile;

    $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
    if (!$socket) {
        error_log("Socket creation failed: " . socket_strerror(socket_last_error()));
        return "Socket creation failed.";
    }

    if (!@socket_connect($socket, $client_ip, $client_port)) {
        error_log("Socket connection failed to $client_ip:$client_port - " . socket_strerror(socket_last_error()));
        return "Failed to connect to client at $client_ip:$client_port.";
    }

    socket_write($socket, $command, strlen($command));
    $response = socket_read($socket, 1024);
    socket_close($socket);

    if ($command === "pause" || $command === "unpause") {
        file_put_contents($statusFile, json_encode(['status' => $command]));
        if ($command === "unpause") {
            file_put_contents($overrideFile, json_encode(['override' => true]));
        } else {
            if (file_exists($overrideFile)) unlink($overrideFile);
        }
    }

    return $response;
}

// Determine the current internet status
function getCurrentStatus() {
    global $scheduleFile, $statusFile, $overrideFile;

    $currentStatus = 'unpaused'; // Default status

    if (file_exists($overrideFile)) {
        $overrideData = json_decode(file_get_contents($overrideFile), true);
        if (!empty($overrideData['override'])) {
            return 'unpaused';
        }
    }

    if (file_exists($statusFile)) {
        $statusData = json_decode(file_get_contents($statusFile), true);
        $currentStatus = $statusData['status'] ?? 'unpaused';
    }

    if (file_exists($scheduleFile)) {
        $schedule = json_decode(file_get_contents($scheduleFile), true);
        $disableTime = $schedule['disable_time'] ?? '22:00';
        $enableTime = $schedule['enable_time'] ?? '06:00';

        $currentTime = date('H:i');
        if ($disableTime < $enableTime) {
            if ($currentTime >= $disableTime && $currentTime < $enableTime) {
                $currentStatus = 'downtime';
            }
        } else {
            if ($currentTime >= $disableTime || $currentTime < $enableTime) {
                $currentStatus = 'downtime';
            }
        }

        if ($currentStatus === 'downtime' && file_exists($overrideFile)) {
            unlink($overrideFile);
        }
    }

    return $currentStatus;
}

// Handle commands and form submissions
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_POST['command'])) {
        $command = $_POST['command'];
        $response = sendCommand($command);
        echo "<p>Response: $response</p>";
    } elseif (isset($_POST['schedule'])) {
        $schedule = [
            'disable_time' => $_POST['disable_time'],
            'enable_time' => $_POST['enable_time']
        ];
        if (file_put_contents($scheduleFile, json_encode($schedule))) {
            echo "<p>Schedule updated successfully.</p>";
        } else {
            echo "<p>Failed to update schedule. Please check file permissions.</p>";
        }

        $disableTime = explode(':', $_POST['disable_time']);
        $enableTime = explode(':', $_POST['enable_time']);

        $cronJobs = [
            "{$disableTime[1]} {$disableTime[0]} * * * php /var/www/html/timelimits/send_command.php pause",
            "{$enableTime[1]} {$enableTime[0]} * * * php /var/www/html/timelimits/send_command.php unpause"
        ];

        file_put_contents('/tmp/www-data-crontab', implode("\n", $cronJobs) . "\n");
        exec('crontab -u www-data /tmp/www-data-crontab', $output, $return_var);
        unlink('/tmp/www-data-crontab');

        if ($return_var === 0) {
            echo "<p>Crontab updated successfully.</p>";
        } else {
            echo "<p>Failed to update crontab. Check permissions.</p>";
        }
    }
}

$schedule = file_exists($scheduleFile) ? json_decode(file_get_contents($scheduleFile), true) : ['disable_time' => '22:00', 'enable_time' => '06:00'];
$currentStatus = getCurrentStatus();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jack-Attack Has Game (or Not)</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
        }
        .container {
            max-width: 600px;
            width: 90%;
            padding: 10px;
            box-sizing: border-box;
            text-align: center;
        }
        h1 {
            text-align: center;
            font-size: 24px;
            margin-bottom: 20px;
        }
        button, input[type="time"] {
            width: 70%;
            padding: 10px;
            font-size: 16px;
            margin: 10px auto;
            display: block;
        }
        .status-box {
            border: 2px solid #000;
            padding: 20px;
            margin-bottom: 20px;
            width: 100%;
            text-align: center;
            font-size: 18px;
        }
        .current-schedule {
            margin-bottom: 20px;
            font-size: 16px;
        }
        form {
            margin-bottom: 20px;
        }
        label {
            font-size: 18px;
            margin-bottom: 10px;
            display: inline-block;
            width: 100%;
        }
        .status-paused {
            color: red;
        }
        .status-unpaused {
            color: green;
        }
        .status-downtime {
            color: orange;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Jack-Attack Has Game (or Not)</h1>

        <!-- Internet Status -->
        <div class="status-box">
            <h3>Current Status: 
                <?php if ($currentStatus === 'paused'): ?>
                    <span class="status-paused">Paused (manually)</span>
                <?php elseif ($currentStatus === 'unpaused'): ?>
                    <span class="status-unpaused">Unpaused</span>
                <?php elseif ($currentStatus === 'downtime'): ?>
                    <span class="status-downtime">Downtime (scheduled)</span>
                <?php endif; ?>
            </h3>
        </div>

        <!-- Pause and Unpause Internet -->
        <form method="post">
            <button type="submit" name="command" value="pause">Pause Internet</button>
            <button type="submit" name="command" value="unpause">Unpause Internet</button>
        </form>

        <!-- Schedule Internet Downtime -->
        <h2>Schedule Internet Downtime</h2>
        <div class="current-schedule">
            <strong>Current Schedule:</strong> 
            Disable at <em><?= formatTime12Hour($schedule['disable_time']) ?></em>, 
            Enable at <em><?= formatTime12Hour($schedule['enable_time']) ?></em>
        </div>
        <form method="post">
            <label for="disable_time">Disable Time:</label>
            <input type="time" id="disable_time" name="disable_time" value="<?= $schedule['disable_time'] ?>">
            <label for="enable_time">Enable Time:</label>
            <input type="time" id="enable_time" name="enable_time" value="<?= $schedule['enable_time'] ?>">
            <button type="submit" name="schedule" value="1">Set Schedule</button>
        </form>

        <!-- Client IP Address -->
        <div class="status-box">
            <h3>Client Machine IP: <span style="color: blue;"><?= htmlspecialchars($client_ip) ?></span></h3>
        </div>
    </div>
</body>
</html>
