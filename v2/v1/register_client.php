<?php
$client_ip_file = '/var/www/html/timelimits/client_ip.json';

// Capture incoming IP address
$received_ip = file_get_contents('php://input');
if ($received_ip) {
    file_put_contents($client_ip_file, json_encode(['client_ip' => $received_ip]));
    echo "Client IP registered: $received_ip";
} else {
    echo "No IP received.";
}
?>
