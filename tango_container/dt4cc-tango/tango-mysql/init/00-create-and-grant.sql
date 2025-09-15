CREATE DATABASE IF NOT EXISTS tango
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'tango'@'%' IDENTIFIED BY 'Tango@1234!';
GRANT ALL PRIVILEGES ON tango.* TO 'tango'@'%';

-- if you also want localhost-grants explicitly:
CREATE USER IF NOT EXISTS 'tango'@'localhost' IDENTIFIED BY 'Tango@1234!';
GRANT ALL PRIVILEGES ON tango.* TO 'tango'@'localhost';

FLUSH PRIVILEGES;
