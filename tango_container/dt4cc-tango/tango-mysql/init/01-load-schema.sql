USE tango;

/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19-11.7.2-MariaDB, for osx10.20 (arm64)
--
-- Host: localhost    Database: tango
-- ------------------------------------------------------
-- Server version	11.7.2-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

--
-- Table structure for table `access_address`
--

DROP TABLE IF EXISTS `access_address`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `access_address` (
  `user` varchar(255) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `netmask` varchar(255) DEFAULT 'FF.FF.FF.FF',
  `updated` timestamp NOT NULL,
  `accessed` timestamp NOT NULL DEFAULT '2000-01-01 06:00:00'
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `access_device`
--

DROP TABLE IF EXISTS `access_device`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `access_device` (
  `user` varchar(255) DEFAULT NULL,
  `device` varchar(255) DEFAULT NULL,
  `rights` varchar(255) DEFAULT NULL,
  `updated` timestamp NOT NULL,
  `accessed` timestamp NOT NULL DEFAULT '2000-01-01 06:00:00'
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `attribute_alias`
--

DROP TABLE IF EXISTS `attribute_alias`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `attribute_alias` (
  `alias` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL DEFAULT '',
  `device` varchar(255) NOT NULL DEFAULT '',
  `attribute` varchar(255) NOT NULL DEFAULT '',
  `updated` timestamp NOT NULL,
  `accessed` timestamp NOT NULL DEFAULT '2000-01-01 06:00:00',
  `comment` text DEFAULT NULL,
  KEY `index_attribute_alias` (`alias`(64),`name`(64))
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `attribute_class`
--

DROP TABLE IF EXISTS `attribute_class`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `attribute_class` (
  `class` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL DEFAULT '',
  `updated` timestamp NOT NULL,
  `accessed` timestamp NOT NULL DEFAULT '2000-01-01 06:00:00',
  `comment` text DEFAULT NULL,
  KEY `index_attribute_class` (`class`(64),`name`(64))
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `class_attribute_history_id`
--

DROP TABLE IF EXISTS `class_attribute_history_id`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `class_attribute_history_id` (
  `id` bigint(20) unsigned NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `class_history_id`
--

DROP TABLE IF EXISTS `class_history_id`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `class_history_id` (
  `id` bigint(20) unsigned NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `class_pipe_history_id`
--

DROP TABLE IF EXISTS `class_pipe_history_id`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `class_pipe_history_id` (
  `id` bigint(20) unsigned NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `device`
--

DROP TABLE IF EXISTS `device`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `device` (
  `name` varchar(255) NOT NULL DEFAULT 'nada',
  `alias` varchar(255) DEFAULT NULL,
  `domain` varchar(85) NOT NULL DEFAULT 'nada',
  `family` varchar(85) NOT NULL DEFAULT 'nada',
  `member` varchar(85) NOT NULL DEFAULT 'nada',
  `exported` int(11) DEFAULT 0,
  `ior` text DEFAULT NULL,
  `host` varchar(255) NOT NULL DEFAULT 'nada',
  `server` varchar(255) NOT NULL DEFAULT 'nada',
  `pid` int(11) DEFAULT 0,
  `class` varchar(255) NOT NULL DEFAULT 'nada',
  `version` varchar(8) NOT NULL DEFAULT 'nada',
  `started` datetime DEFAULT NULL,
  `stopped` datetime DEFAULT NULL,
  `comment` text DEFAULT NULL,
  KEY `name` (`name`(64),`alias`(64))
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `device_attribute_history_id`
--

DROP TABLE IF EXISTS `device_attribute_history_id`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `device_attribute_history_id` (
  `id` bigint(20) unsigned NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `device_history_id`
--

DROP TABLE IF EXISTS `device_history_id`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `device_history_id` (
  `id` bigint(20) unsigned NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `device_pipe_history_id`
--

DROP TABLE IF EXISTS `device_pipe_history_id`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `device_pipe_history_id` (
  `id` bigint(20) unsigned NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `event`
--

DROP TABLE IF EXISTS `event`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `event` (
  `name` varchar(255) DEFAULT NULL,
  `exported` int(11) DEFAULT NULL,
  `ior` text DEFAULT NULL,
  `host` varchar(255) DEFAULT NULL,
  `server` varchar(255) DEFAULT NULL,
  `pid` int(11) DEFAULT NULL,
  `version` varchar(8) DEFAULT NULL,
  `started` datetime DEFAULT NULL,
  `stopped` datetime DEFAULT NULL,
  KEY `index_name` (`name`(64))
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `object_history_id`
--

DROP TABLE IF EXISTS `object_history_id`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `object_history_id` (
  `id` bigint(20) unsigned NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `property`
--

DROP TABLE IF EXISTS `property`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `property` (
  `object` varchar(255) DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `count` int(11) DEFAULT NULL,
  `value` text DEFAULT NULL,
  `updated` timestamp NOT NULL,
  `accessed` timestamp NOT NULL DEFAULT '2000-01-01 06:00:00',
  `comment` text DEFAULT NULL,
  KEY `index_name` (`object`(64),`name`(64))
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `property_attribute_class`
--

DROP TABLE IF EXISTS `property_attribute_class`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_attribute_class` (
  `class` varchar(255) NOT NULL DEFAULT '',
  `attribute` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL DEFAULT '',
  `count` int(11) NOT NULL DEFAULT 0,
  `value` text DEFAULT NULL,
  `updated` timestamp NOT NULL,
  `accessed` timestamp NOT NULL DEFAULT '2000-01-01 06:00:00',
  `comment` text DEFAULT NULL,
  KEY `index_property_attribute_class` (`class`(64),`attribute`(64),`name`(64),`count`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `property_attribute_class_hist`
--

DROP TABLE IF EXISTS `property_attribute_class_hist`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_attribute_class_hist` (
  `id` bigint(20) unsigned NOT NULL DEFAULT 0,
  `date` timestamp NOT NULL,
  `class` varchar(255) NOT NULL DEFAULT '',
  `attribute` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL DEFAULT '',
  `count` int(11) NOT NULL DEFAULT 0,
  `value` text DEFAULT NULL,
  PRIMARY KEY (`id`,`count`),
  KEY `class_attribute_name` (`class`,`attribute`,`name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `property_attribute_device`
--

DROP TABLE IF EXISTS `property_attribute_device`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_attribute_device` (
  `device` varchar(255) NOT NULL DEFAULT '',
  `attribute` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL DEFAULT '',
  `count` int(11) NOT NULL DEFAULT 0,
  `value` text DEFAULT NULL,
  `updated` timestamp NOT NULL,
  `accessed` timestamp NOT NULL DEFAULT '2000-01-01 06:00:00',
  `comment` text DEFAULT NULL,
  KEY `index_property_attribute_device` (`device`(64),`attribute`(64),`name`(64),`count`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `property_attribute_device_hist`
--

DROP TABLE IF EXISTS `property_attribute_device_hist`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_attribute_device_hist` (
  `id` bigint(20) unsigned NOT NULL DEFAULT 0,
  `count` int(11) NOT NULL DEFAULT 0,
  `date` timestamp NOT NULL,
  `device` varchar(255) NOT NULL DEFAULT '',
  `attribute` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL DEFAULT '',
  `value` text DEFAULT NULL,
  PRIMARY KEY (`id`,`count`),
  KEY `device_attribute_name` (`device`,`attribute`,`name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `property_class`
--

DROP TABLE IF EXISTS `property_class`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_class` (
  `class` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL DEFAULT '',
  `count` int(11) NOT NULL DEFAULT 0,
  `value` text DEFAULT NULL,
  `updated` timestamp NOT NULL,
  `accessed` timestamp NOT NULL DEFAULT '2000-01-01 06:00:00',
  `comment` text DEFAULT NULL,
  KEY `index_property` (`class`(64),`name`(64),`count`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `property_class_hist`
--

DROP TABLE IF EXISTS `property_class_hist`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_class_hist` (
  `id` bigint(20) unsigned NOT NULL DEFAULT 0,
  `date` timestamp NOT NULL,
  `class` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL DEFAULT '',
  `count` int(11) NOT NULL DEFAULT 0,
  `value` text DEFAULT NULL,
  PRIMARY KEY (`id`,`count`),
  KEY `class_name` (`class`,`name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `property_device`
--

DROP TABLE IF EXISTS `property_device`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_device` (
  `device` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL DEFAULT '',
  `domain` varchar(255) NOT NULL DEFAULT '',
  `family` varchar(255) NOT NULL DEFAULT '',
  `member` varchar(255) NOT NULL DEFAULT '',
  `count` int(11) NOT NULL DEFAULT 0,
  `value` text DEFAULT NULL,
  `updated` timestamp NOT NULL,
  `accessed` timestamp NOT NULL DEFAULT '2000-01-01 06:00:00',
  `comment` text DEFAULT NULL,
  KEY `index_resource` (`device`(64),`name`(64),`count`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `property_device_hist`
--

DROP TABLE IF EXISTS `property_device_hist`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_device_hist` (
  `id` bigint(20) unsigned NOT NULL DEFAULT 0,
  `date` timestamp NULL DEFAULT current_timestamp(),
  `device` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL DEFAULT '',
  `count` int(11) NOT NULL DEFAULT 0,
  `value` text DEFAULT NULL,
  PRIMARY KEY (`id`,`count`),
  KEY `device_name` (`device`,`name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `property_hist`
--

DROP TABLE IF EXISTS `property_hist`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_hist` (
  `id` bigint(20) unsigned NOT NULL DEFAULT 0,
  `date` timestamp NOT NULL,
  `object` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL DEFAULT '',
  `count` int(11) NOT NULL DEFAULT 0,
  `value` text DEFAULT NULL,
  PRIMARY KEY (`id`,`count`),
  KEY `object_name` (`object`,`name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `property_pipe_class`
--

DROP TABLE IF EXISTS `property_pipe_class`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_pipe_class` (
  `class` varchar(255) NOT NULL DEFAULT '',
  `pipe` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL DEFAULT '',
  `count` int(11) NOT NULL DEFAULT 0,
  `value` text DEFAULT NULL,
  `updated` timestamp NOT NULL,
  `accessed` timestamp NOT NULL DEFAULT '2000-01-01 06:00:00',
  `comment` text DEFAULT NULL,
  KEY `index_property_pipe_class` (`class`(64),`pipe`(64),`name`(64),`count`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `property_pipe_class_hist`
--

DROP TABLE IF EXISTS `property_pipe_class_hist`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_pipe_class_hist` (
  `id` bigint(20) unsigned NOT NULL DEFAULT 0,
  `date` timestamp NOT NULL,
  `class` varchar(255) NOT NULL DEFAULT '',
  `pipe` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL DEFAULT '',
  `count` int(11) NOT NULL DEFAULT 0,
  `value` text DEFAULT NULL,
  PRIMARY KEY (`id`,`count`),
  KEY `class_pipe_name` (`class`,`pipe`,`name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `property_pipe_device`
--

DROP TABLE IF EXISTS `property_pipe_device`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_pipe_device` (
  `device` varchar(255) NOT NULL DEFAULT '',
  `pipe` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL DEFAULT '',
  `count` int(11) NOT NULL DEFAULT 0,
  `value` text DEFAULT NULL,
  `updated` timestamp NOT NULL,
  `accessed` timestamp NOT NULL DEFAULT '2000-01-01 06:00:00',
  `comment` text DEFAULT NULL,
  KEY `index_property_pipe_device` (`device`(64),`pipe`(64),`name`(64),`count`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `property_pipe_device_hist`
--

DROP TABLE IF EXISTS `property_pipe_device_hist`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_pipe_device_hist` (
  `id` bigint(20) unsigned NOT NULL DEFAULT 0,
  `date` timestamp NOT NULL,
  `device` varchar(255) NOT NULL DEFAULT '',
  `pipe` varchar(255) NOT NULL DEFAULT '',
  `name` varchar(255) NOT NULL DEFAULT '',
  `count` int(11) NOT NULL DEFAULT 0,
  `value` text DEFAULT NULL,
  PRIMARY KEY (`id`,`count`),
  KEY `device_pipe_name` (`device`,`pipe`,`name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `server`
--

DROP TABLE IF EXISTS `server`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `server` (
  `name` varchar(255) NOT NULL DEFAULT '',
  `host` varchar(255) NOT NULL DEFAULT '',
  `mode` int(11) DEFAULT 0,
  `level` int(11) DEFAULT 0,
  KEY `index_name` (`name`(64))
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

-- Dump completed on 2025-08-08  5:15:27
