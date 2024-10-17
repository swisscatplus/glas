--
-- Table structure for table `node_states`
--

DROP TABLE IF EXISTS `node_states`;
CREATE TABLE `node_states` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `node_states`
--

LOCK TABLES `node_states` WRITE;
INSERT INTO `node_states` VALUES
(1,'AVAILABLE'),
(2,'IN USE'),
(3, 'OFFLINE'),
(4, 'RECOVERY'),
(5,'ERROR'),
(6, 'RESTARTING');
UNLOCK TABLES;

--
-- Table structure for table `nodes`
--

DROP TABLE IF EXISTS `nodes`;
CREATE TABLE `nodes` (
  `id` varchar(255) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `node_state_id` int(11) NOT NULL,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  CONSTRAINT `nodes_ibfk_1` FOREIGN KEY (`node_state_id`) REFERENCES `node_states` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `nodes`
--

LOCK TABLES `nodes` WRITE;
UNLOCK TABLES;

--
-- Table structure for table `node_properties`
--

DROP TABLE IF EXISTS `node_properties`;
CREATE TABLE `node_properties` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `node_id` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `value` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `node_properties_ibfk_1` FOREIGN KEY (`node_id`) REFERENCES `nodes` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `node_properties`
--

LOCK TABLES `node_properties` WRITE;
UNLOCK TABLES;

--
-- Table structure for table `task_states`
--

DROP TABLE IF EXISTS `task_states`;
CREATE TABLE `task_states` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `task_states`
--

LOCK TABLES `task_states` WRITE;
INSERT INTO `task_states` VALUES
(1,'PENDING'),
(2,'ACTIVE'),
(3,'PAUSED'),
(4,'FINISHED'),
(5,'ERROR'),
(6,'RESTARTING');
UNLOCK TABLES;

--
-- Table structure for table `workflows`
--

DROP TABLE IF EXISTS `workflows`;
CREATE TABLE `workflows` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `source_node_id` varchar(255) NOT NULL,
  `destination_node_id` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `source_node_id` (`source_node_id`),
  KEY `destination_node_id` (`destination_node_id`),
  CONSTRAINT `workflows_ibfk_1` FOREIGN KEY (`source_node_id`) REFERENCES `nodes` (`id`),
  CONSTRAINT `workflows_ibfk_2` FOREIGN KEY (`destination_node_id`) REFERENCES `nodes` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `workflows`
--

LOCK TABLES `workflows` WRITE;
UNLOCK TABLES;

--
-- Table structure for table `task`
--

DROP TABLE IF EXISTS `tasks`;
CREATE TABLE `tasks` (
  `id` CHAR(36) NOT NULL,
  `workflow_id` int(11) NOT NULL,
  `active_step` varchar(255) NULL,
  `task_state_id` int(11) NOT NULL,
  `args` JSON NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `task_state_id` (`task_state_id`),
  KEY `workflow_id` (`workflow_id`),
  CONSTRAINT `tasks_ibfk_1` FOREIGN KEY (`workflow_id`) REFERENCES `workflows` (`id`),
  CONSTRAINT `tasks_ibfk_2` FOREIGN KEY (`task_state_id`) REFERENCES `task_states` (`id`),
  CONSTRAINT `tasks_ibfk_3` FOREIGN KEY (`active_step`) REFERENCES `nodes` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `task`
--

LOCK TABLES `tasks` WRITE;
UNLOCK TABLES;

--
-- Table structure for table `steps`
--

DROP TABLE IF EXISTS `steps`;
CREATE TABLE `steps` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `workflow_id` int(11) NOT NULL,
  `node_id` varchar(255) NOT NULL,
  `position` int(5),
  PRIMARY KEY (`id`),
  CONSTRAINT `steps_ibfk_1` FOREIGN KEY (`node_id`) REFERENCES `nodes` (`id`),
  CONSTRAINT `steps_ibfk_2` FOREIGN KEY (`workflow_id`) REFERENCES `workflows` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `steps`
--

LOCK TABLES `steps` WRITE;
UNLOCK TABLES;

--
-- Table structure for table `node_call_records`
--

DROP TABLE IF EXISTS `node_call_records`;
CREATE TABLE `node_call_records` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `node_id` varchar(255) NOT NULL,
  `endpoint` varchar(255) NULL,
  `message` varchar(255) NULL,
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `duration` double,
  `outcome` varchar(50),
  PRIMARY KEY (`id`),
  CONSTRAINT `node_call_records_ibfk_1` FOREIGN KEY (`node_id`) REFERENCES `nodes` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `node_call_records`
--

LOCK TABLES `node_call_records` WRITE;
UNLOCK TABLES;

--
-- Table structure for table `workflow_usage_records`
--

DROP TABLE IF EXISTS `workflow_usage_records`;
CREATE TABLE `workflow_usage_records` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `workflow_id` int(11) NOT NULL,
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  CONSTRAINT `workflow_usage_records_ibfk_1` FOREIGN KEY (`workflow_id`) REFERENCES `workflows` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `workflow_usage_records`
--

LOCK TABLES `workflow_usage_records` WRITE;
UNLOCK TABLES;

--
-- Table structure for table `logs`
--

DROP TABLE IF EXISTS `logs`;
CREATE TABLE `logs` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `timestamp` TIMESTAMP(3) NOT NULL,
    `logger_name` varchar(255) NOT NULL,
    `log_level` varchar(255) NOT NULL,
    `module` varchar(255) NOT NULL,
    `caller` varchar(255) NOT NULL,
    `line` int(11) NOT NULL,
    `message` varchar(255) NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `logs`
--

LOCK TABLES `logs` WRITE;
UNLOCK TABLES;

--
-- Table structure for table `execution_logs`
--

DROP TABLE IF EXISTS `execution_logs`;
CREATE TABLE `execution_logs` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `task_id` char(36) NOT NULL,
    `workflow_id` int(11) NOT NULL,
    `name` varchar(255) NOT NULL,
    `start` TIMESTAMP(3) NOT NULL,
    `end` TIMESTAMP(3) NOT NULL,
    CONSTRAINT `execution_logs_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`),
    CONSTRAINT `execution_logs_ibfk_2` FOREIGN KEY (`workflow_id`) REFERENCES `workflows` (`id`),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `execution_logs`
--

LOCK TABLES `execution_logs` WRITE;
UNLOCK TABLES;

--
-- Table structure for table `access_logs`
--

DROP TABLE IF EXISTS `access_logs`;
CREATE TABLE `access_logs` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `host` varchar(20) NOT NULL,
    `authorized` boolean NOT NULL,
    `identifier` varchar(255) NULL,
    `path` varchar(255) NOT NULL,
    `method` varchar(10) NOT NULL,
    `timestamp` TIMESTAMP(3) NOT NULL DEFAULT NOW(3),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `access_logs`
--

LOCK TABLES `access_logs` WRITE;
UNLOCK TABLES;