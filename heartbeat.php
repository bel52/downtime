<?php
// File path to store client information
$client_ip_file = '/var/www/html/timelimits/client_ip.json';

// Read and decode incoming data
$data = json_decode(file_get_contents("php://input"), true);

// Log received data
error_log("Heartbeat received: " . json_encode($data));

// Validate incoming data
if (isset($data['client_ip']) && filter_var($data['client_ip'], FILTER_VALIDATE_IP) && isset($data['name'])) {
    // Load existing client data if the file exists
    $clients = file_exists($client_ip_file) ? json_decode(file_get_contents($client_ip_file), true) : [];
    
    // Update or add the client information
    $clients[$data['name']] = [
        'client_ip' => $data['client_ip'],
        'last_seen' => time(),
    ];

    // Save updated client data back to the JSON file
    if (file_put_contents($client_ip_file, json_encode($clients, JSON_PRETTY_PRINT))) {
        echo "Client IP updated.";
    } else {
        http_response_code(500);
        echo "Failed to update client IP.";
    }
} else {
    // Invalid data received
    error_log("Invalid client data structure: " . json_encode($data));
    http_response_code(400);
    echo "Invalid client data.";
}
?>
