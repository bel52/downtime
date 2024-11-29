<?php
function sendCommand($command) {
    // Path to the file storing the client IP
    $client_ip_file = '/var/www/html/timelimits/client_ip.json';

    // Fetch the client IP
    $client_data = file_exists($client_ip_file) ? json_decode(file_get_contents($client_ip_file), true) : [];
    $client_ip = $client_data['client_ip'] ?? '192.168.86.100'; // Default fallback IP
    $client_port = 65432;

    // Create a socket connection
    $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
    if (!$socket) {
        error_log("Socket creation failed: " . socket_strerror(socket_last_error()));
        return "Socket creation failed.";
    }

    if (!@socket_connect($socket, $client_ip, $client_port)) {
        error_log("Socket connection failed to $client_ip:$client_port - " . socket_strerror(socket_last_error()));
        return "Failed to connect to client.";
    }

    // Send the command
    socket_write($socket, $command, strlen($command));
    $response = socket_read($socket, 1024);
    socket_close($socket);

    return $response;
}

// Check if a command is provided via command-line arguments
if ($argc > 1) {
    $command = $argv[1]; // First argument after the script name
    $response = sendCommand($command);
    echo $response . PHP_EOL;
} else {
    echo "No command provided." . PHP_EOL;
}
?>
