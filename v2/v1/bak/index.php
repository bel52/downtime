<?php
// File paths
$scheduleFile = '/var/www/html/timelimits/schedule.json'; // Schedule file
$client_ip_file = '/var/www/html/timelimits/client_ip.json'; // Client IP storage

// Fetch the client IP dynamically
$client_data = file_exists($client_ip_file) ? json_decode(file_get_contents($client_ip_file), true) : [];
$client_ip = $client_data['client_ip'] ?? '192.168.86.100'; // Default to fallback IP
$client_port = 65432; // Port used by the client

// Function to send commands to the client
function sendCommand($command) {
    global $client_ip, $client_port;

    $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
    if (!$socket) {
        error_log("Socket creation failed: " . socket_strerror(socket_last_error()));
        return "Socket creation failed.";
    }

    if (!@socket_connect($socket, $client_ip, $client_port)) {
        error_log("Socket connection failed to $client_ip:$client_port - " . socket_strerror(socket_last_error()));
        return "Failed to connect to client.";
    }

    socket_write($socket, $command, strlen($command));
    $response = socket_read($socket, 1024);
    socket_close($socket);
    return $response;
}

// Handle commands and form submissions
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_POST['command'])) {
        // Handle pause or unpause commands
        $command = $_POST['command'];
        $response = sendCommand($command);
        echo "<p>Response: $response</p>";
    } elseif (isset($_POST['schedule'])) {
        // Handle schedule updates
        $schedule = [
            'disable_time' => $_POST['disable_time'],
            'enable_time' => $_POST['enable_time']
        ];
        if (file_put_contents($scheduleFile, json_encode($schedule))) {
            echo "<p>Schedule updated successfully.</p>";
        } else {
            echo "<p>Failed to update schedule. Please check file permissions.</p>";
        }

        // Update crontab with new schedule
        $disableTime = explode(':', $_POST['disable_time']);
        $enableTime = explode(':', $_POST['enable_time']);

        // Define the cron jobs
        $cronJobs = [
            "{$disableTime[1]} {$disableTime[0]} * * * php /var/www/html/timelimits/send_command.php pause",
            "{$enableTime[1]} {$enableTime[0]} * * * php /var/www/html/timelimits/send_command.php unpause"
        ];

        // Write the cron jobs to a temporary file
        file_put_contents('/tmp/www-data-crontab', implode("\n", $cronJobs) . "\n");

        // Install the new crontab for www-data
        exec('crontab -u www-data /tmp/www-data-crontab', $output, $return_var);
        unlink('/tmp/www-data-crontab'); // Clean up temporary file

        if ($return_var === 0) {
            echo "<p>Crontab updated successfully.</p>";
        } else {
            echo "<p>Failed to update crontab. Check permissions.</p>";
        }
    }
}

// Load the current schedule for display
$schedule = file_exists($scheduleFile) ? json_decode(file_get_contents($scheduleFile), true) : ['disable_time' => '22:00', 'enable_time' => '06:00'];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Internet Control</title>
</head>
<body>
    <h1>Internet Control</h1>

    <!-- Pause and Unpause Internet -->
    <form method="post">
        <button type="submit" name="command" value="pause">Pause Internet</button>
        <button type="submit" name="command" value="unpause">Unpause Internet</button>
    </form>

    <!-- Schedule Internet Downtime -->
    <h2>Schedule Internet Downtime</h2>
    <form method="post">
        <label for="disable_time">Disable Time:</label>
        <input type="time" id="disable_time" name="disable_time" value="<?= htmlspecialchars($schedule['disable_time'] ?? '22:00') ?>">
        <br>
        <label for="enable_time">Enable Time:</label>
        <input type="time" id="enable_time" name="enable_time" value="<?= htmlspecialchars($schedule['enable_time'] ?? '06:00') ?>">
        <br><br>
        <button type="submit" name="schedule" value="1">Set Schedule</button>
    </form>
</body>
</html>
