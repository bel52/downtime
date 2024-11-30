<?php
// Path to client_ip.json
$clientIpFile = '/var/www/html/timelimits/client_ip.json';

// Read the raw POST data
$rawData = file_get_contents('php://input');
$data = json_decode($rawData, true);

// Validate the incoming data
if (!isset($data['client_ip'])) {
    http_response_code(400);
    echo "Invalid data: Missing client_ip.";
    exit;
}

// Update the client_ip.json file
$clientData = [
    'client_ip' => $data['client_ip'],
    'last_seen' => $data['last_seen'] ?? time() // Use provided last_seen or current time
];

file_put_contents($clientIpFile, json_encode($clientData));
echo "Client data updated.";
?>
