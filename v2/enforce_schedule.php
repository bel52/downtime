<?php
$statusFile = '/var/www/html/timelimits/status.json';
$scheduleFile = '/var/www/html/timelimits/schedule.json';
$clientIpFile = '/var/www/html/timelimits/client_ip.json';

if (!file_exists($statusFile) || !file_exists($scheduleFile)) {
    error_log("Error: Required files not found.");
    exit;
}

$status = json_decode(file_get_contents($statusFile), true);
$schedule = json_decode(file_get_contents($scheduleFile), true);
$clients = file_exists($clientIpFile) ? json_decode(file_get_contents($clientIpFile), true) : [];

$currentTime = date("H:i");
$disableTime = $schedule['disable_time'];
$enableTime = $schedule['enable_time'];

$shouldPause = $disableTime <= $currentTime && $currentTime < $enableTime;

if (isset($status['manual']) && $status['manual']) {
    error_log("Manual mode is active. Skipping schedule enforcement.");
    exit;
}

$newStatus = $shouldPause ? "pause" : "unpause";

if ($status['status'] !== $newStatus) {
    $status['status'] = $newStatus;
    file_put_contents($statusFile, json_encode($status));

    foreach ($clients as $client) {
        $clientIp = $client['client_ip'];
        $socket = @socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
        if (!$socket || !@socket_connect($socket, $clientIp, 65432)) {
            error_log("Failed to connect to client at $clientIp.");
            continue;
        }
        socket_write($socket, $newStatus, strlen($newStatus));
        socket_close($socket);
    }
}
?>
