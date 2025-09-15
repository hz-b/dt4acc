USE tango;

INSERT IGNORE INTO server (name, host, mode, level)
VALUES ('DataBaseds/2', 'databaseds', 0, 0);

-- Insert the two device rows (matches your device table columns)
INSERT IGNORE INTO device
  (name, alias, domain, family, member,
   exported, ior, host, server, pid,
   class, version, started, stopped, comment)
VALUES
  ('sys/database/2', NULL, 'sys', 'database', '2',
   0, NULL, 'databaseds', 'DataBaseds/2', 0,
   'DataBase', '1.0', NULL, NULL, NULL),
  ('dserver/databaseds/2', NULL, 'dserver', 'databaseds', '2',
   0, NULL, 'databaseds', 'DataBaseds/2', 0,
   'DServer', '1.0', NULL, NULL, NULL);
