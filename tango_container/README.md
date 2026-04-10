# DT4CC Tango Container Setup and Usage Guide

This guide provides step-by-step instructions for running the DT4CC Tango containers with MySQL database and Tango DataBaseDS.

## Prerequisites

- Docker and Docker Compose installed on your system
- Local MySQL/MariaDB service should be **stopped** to avoid port conflicts

## Quick Start

### 1. Stop Local Database Services

Before starting the containers, ensure your local MySQL or MariaDB service is stopped to avoid port conflicts:

**On macOS:**
```bash
# Stop MySQL if running via Homebrew
brew services stop mysql

# Or stop MariaDB
brew services stop mariadb
```

**On Linux:**
```bash
# Stop MySQL
sudo systemctl stop mysql
# or
sudo systemctl stop mariadb
```

**On Windows:**
- Stop MySQL/MariaDB service from Services management console

### 2. Start the Database and Tango DataBaseDS

Navigate to the `tango-mysql` directory and start the database services:

```bash
cd tango-mysql
docker compose up -d
```

This will start:
- MySQL 8.0 database on port 3306
- Tango DataBaseDS on port 10000
- Both services will be connected via the `tango-net` network

Wait for the services to be healthy (check with `docker compose ps`).

### 3. Build and Start the Application Container

Return to the main directory and build the application container:

```bash
cd ..
docker compose -f docker-compose.app.yml build
docker compose -f docker-compose.app.yml up -d
```

This will:
- Build the application container with Conda environment `tangoenv1`
- Install all required Python packages and dependencies
- Clone and install the required repositories (lat2db, bact-device-models, bact-twin-architecture, dt4acc)

### 4. Start the Tango Server

Access the application container and start the Tango server:

```bash
docker exec -it tango_app bash
```

Inside the container, activate the Conda environment and start the server:

```bash
conda activate tangoenv1
cd /opt/dt4acc
python scripts/dt4acc_enhanced_tango.py
```

You should see server startup messages and confirmation that the Tango server is running.

## Testing the Setup

### Basic Device Testing

Open a **new terminal** and access the container again:

```bash
docker exec -it tango_app bash
conda activate tangoenv1
```

Test basic device connectivity:

```python
python
```

In the Python shell:

```python
from tango import DeviceProxy

# Test power converter device
dev = DeviceProxy("SimpleTangoServer/test/power_converter_Q3P2T6R")
dev.current_setpoint = 5.1

# You should see logs showing twiss and orbit calculations
```

### Using Test Scripts

Navigate to the test examples directory:

```bash
cd /opt/dt4acc/tango_tests/example
```

#### Available Test Scripts

1. **Check Device Status:**
   ```bash
   python check_device_status.py SimpleTangoServer/test/magnet_VS3M2T8R
   ```

2. **Show Device Values:**
   ```bash
   python show_device_values.py SimpleTangoServer/test/power_converter_Q3P2T1R
   ```

3. **List All Devices:**
   ```bash
   python list_all_devices.py
   ```

4. **List All Servers:**
   ```bash
   python list_all_servers.py
   ```

5. **Update Device Value:**
   ```bash
   python update_device_value.py <device_name> <attribute> <value>
   ```

6. **Check Mapped Properties:**
   ```bash
   python check_mapped_properties.py <device_name>
   ```

## Container Management

### View Running Containers
```bash
docker ps
```

### View Container Logs
```bash
# Application container logs
docker logs tango_app

# Database logs
docker logs tango-mysql-mysql-1

# DataBaseDS logs
docker logs tango-mysql-databaseds-1
```

### Stop All Services
```bash
# Stop application container
docker compose -f docker-compose.app.yml down

# Stop database services
cd tango-mysql
docker compose down
```

### Restart Services
```bash
# Restart database services
cd tango-mysql
docker compose restart

# Restart application container
cd ..
docker compose -f docker-compose.app.yml restart
```

## Troubleshooting

### Port Conflicts
If you encounter port conflicts:
- Ensure local MySQL/MariaDB is stopped
- Check if ports 3306 or 10000 are already in use: `lsof -i :3306` or `lsof -i :10000`



### Tango Server Issues
If the Tango server doesn't start:
1. Check that DataBaseDS is running and healthy
2. Verify the TANGO_HOST environment variable
3. Check the server logs for specific error messages

## Environment Details

- **Conda Environment:** `tangoenv1`
- **Database:** MySQL 8.0
- **Tango DataBaseDS:** 
- **Application:** DT4CC with enhanced Tango integration


## File Structure

```
dt4cc-tango/
├── docker-compose.yml          # Full stack (DB + App)
├── docker-compose.app.yml      # App only (requires external DB)
├── Dockerfile.app              # Application container definition
├── tango.yaml                  # Conda environment specification
├── tango-mysql/
│   ├── compose.yaml            # Database services
│   └── init/                   # SQL initialization scripts
└── README.md                   # This guide
```


