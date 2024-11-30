<?php
// Enable error reporting for debugging
error_reporting(E_ALL);
ini_set('display_errors', 1);

// File paths
$scheduleFile = '/var/www/html/timelimits/schedule.json';
$statusFile = '/var/www/html/timelimits/status.json';
$clientIpFile = '/var/www/html/timelimits/client_ip.json';

// Load files
function loadFile($filePath, $default = []) {
    return file_exists($filePath) ? json_decode(file_get_contents($filePath), true) : $default;
}

$schedule = loadFile($scheduleFile, ['disable_time' => '22:00', 'enable_time' => '06:00']);
$status = loadFile($statusFile, ['status' => 'unpaused', 'manual' => false]);
$clients = loadFile($clientIpFile);

// Log messages for debugging
function logMessage($message) {
    error_log("[" . date("Y-m-d H:i:s") . "] $message\n", 3, "/var/log/timelimits.log");
}

// Send commands to the client
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

// Get current time
$currentTime = date("H:i");
$downtimeActive = false;

// Check if downtime is active
if (($schedule['disable_time'] < $schedule['enable_time'] &&
     $currentTime >= $schedule['disable_time'] &&
     $currentTime < $schedule['enable_time']) ||
    ($schedule['disable_time'] > $schedule['enable_time'] &&
     ($currentTime >= $schedule['disable_time'] || $currentTime < $schedule['enable_time']))) {
    $downtimeActive = true;
}

// Handle enforcement logic
if ($status['manual']) {
    logMessage("Manual mode is active. Skipping schedule enforcement.");
} else {
    foreach ($clients as $name => $client) {
        $clientIp = $client['client_ip'];
        if ($downtimeActive) {
            // Downtime is active, enforce pause
            sendCommand('pause', $clientIp);
            $status['status'] = 'paused';
        } else {
            // Downtime ended, enforce unpause
            sendCommand('unpause', $clientIp);
            $status['status'] = 'unpaused';
        }
    }
    file_put_contents($statusFile, json_encode($status));
    logMessage("Schedule enforcement completed. Status: " . json_encode($status));
}

// Handle client reconnect during downtime
foreach ($clients as $name => $client) {
    $clientIp = $client['client_ip'];
    if (isset($client['last_seen']) && (time() - $client['last_seen']) < 120) {
        logMessage("Client $name ($clientIp) reconnected.");
        if ($downtimeActive && $status['manual'] === false) {
            sendCommand('pause', $clientIp);
            logMessage("Downtime enforced for reconnected client $name.");
        } elseif (!$downtimeActive && $status['manual'] === false) {
            sendCommand('unpause', $clientIp);
            logMessage("Downtime ended for reconnected client $name.");
        }
    }
}
?>
