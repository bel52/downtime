<?php
function sendCommand($command) {
    // Path to the file storing the client IP
    $client_ip_file = '/var/www/html/timelimits/client_ip.json';

    // Fetch the client IP
    if (!file_exists($client_ip_file)) {
        error_log("Client IP file not found.");
        return "Client IP file not found.";
    }

    $client_data = json_decode(file_get_contents($client_ip_file), true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        error_log("Error reading client IP file: " . json_last_error_msg());
        return "Error reading client IP file.";
    }

    $client_ip = $client_data['client_ip'] ?? '192.168.86.100'; // Default fallback IP
    $client_port = 65432;

    // Debug: Show the client IP and port
    echo "[DEBUG] Client IP: $client_ip, Port: $client_port<br>";

    // Create a socket connection
    $socket = @socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
    if (!$socket) {
        error_log("Socket creation failed: " . socket_strerror(socket_last_error()));
        return "Socket creation failed.";
    }

    // Set timeouts for the socket
    socket_set_option($socket, SOL_SOCKET, SO_RCVTIMEO, ["sec" => 5, "usec" => 0]);
    socket_set_option($socket, SOL_SOCKET, SO_SNDTIMEO, ["sec" => 5, "usec" => 0]);

    // Attempt to connect to the client
    if (!@socket_connect($socket, $client_ip, $client_port)) {
        error_log("Socket connection failed to $client_ip:$client_port - " . socket_strerror(socket_last_error()));
        return "Failed to connect to client.";
    }

    echo "[DEBUG] Connected to client.<br>";

    // Send the command
    socket_write($socket, $command, strlen($command));
    echo "[DEBUG] Command sent: $command<br>";

    // Read the response
    $response = socket_read($socket, 1024);
    echo "[DEBUG] Response from client: $response<br>";

    // Close the socket
    socket_close($socket);

    return $response;
}

// Check if a command is provided via command-line arguments
if ($argc > 1) {
    $command = $argv[1]; // First argument after the script name

    // Validate the command
    $valid_commands = ['pause', 'unpause', 'schedule'];
    if (!in_array($command, $valid_commands)) {
        echo "Invalid command provided. Valid commands are: " . implode(", ", $valid_commands) . PHP_EOL;
        exit(1);
    }

    $response = sendCommand($command);
    echo $response . PHP_EOL;
} else {
    echo "No command provided." . PHP_EOL;
}
?>
