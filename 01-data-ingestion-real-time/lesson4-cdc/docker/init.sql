CREATE SCHEMA bde_module3_lesson4;

CREATE TYPE device_types AS ENUM ('tablet', 'smartphone', 'pc');

CREATE TABLE bde_module3_lesson4.visits_new (
  visit_id VARCHAR(40) NOT NULL,
  user_id INTEGER NOT NULL,
  visited_page VARCHAR(20) NOT NULL,
  visit_time TIMESTAMP NOT NULL,
  device_type device_types NOT NULL,
  device_os VARCHAR(100) NOT NULL,
  PRIMARY KEY (visit_id, visit_time)
);

ALTER TABLE bde_module3_lesson4.visits_new REPLICA IDENTITY FULL;


