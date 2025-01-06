# Downtime Monitoring Application

This repository contains a Downtime Monitoring Application developed using PHP, Python, and Shell scripts. The application is designed to track the availability of various services and notify users of any downtime. It follows a server-client architecture meant to manage the downtime and internet access for Windows PCs. The functionality allows the user to set schedules for downtime and to manually pause and unpause the internet.

## Features

- **Service Monitoring**: Monitor the uptime and downtime of various services.
- **Notification System**: Notify users via email or other communication channels when a service goes down.
- **Logging**: Maintain logs of service availability for analysis and reporting.
- **Dashboard**: Provide a web interface for viewing the status of monitored services.
- **Downtime Management**: Set schedules for downtime and manage internet access for Windows PCs.
- **Manual Control**: Manually pause and unpause the internet.

## Technologies Used

- **PHP**: 72.1% - Backend for the web interface and service monitoring.
- **Python**: 27.5% - Scripts for monitoring and notifications.
- **Shell**: 0.4% - Automation scripts for deployment and maintenance.

## Installation

Follow these steps to set up the application on your local machine.

### Prerequisites

- PHP 7.x or later
- Python 3.x
- Composer (for PHP dependencies)
- pip (Python package installer)
- Web server (e.g., Apache, Nginx)
- MySQL or other supported databases

### Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/bel52/downtime.git
   cd downtime
