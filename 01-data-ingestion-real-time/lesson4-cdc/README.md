# Lesson 4: Change Data Capture with Debezium, PostgreSQL, Kafka, and Spark on Windows

## Overview

This practice demonstrates a simple CDC pipeline:

1. PostgreSQL stores page-visit rows in `bde_module3_lesson4.visits_new`.
2. Debezium captures row-level changes from PostgreSQL logical replication.
3. Kafka Connect publishes those changes to a Kafka topic.
4. A Spark Structured Streaming job reads the CDC topic and keeps only newly created rows.
5. The Spark job aggregates created rows by `(device_type, device_os)` and prints the running counts.

This lesson is intentionally small and local. It is useful for understanding CDC event flow, Debezium payload structure, and the difference between `INSERT`, `UPDATE`, and `DELETE` events.

The project is now aligned for this workflow:

- Docker Desktop runs PostgreSQL, Kafka, Zookeeper, Kafka Connect, and the Python Spark consumer
- the Python Spark consumer runs inside Docker and connects to Kafka over the Docker network
- the Scala Spark job still runs on your Windows host and connects to Kafka on `localhost:29092`

## Architecture

Flow:

`PostgreSQL -> Debezium PostgreSQL Connector -> Kafka topic -> Spark Structured Streaming consumer -> console output`

Runtime components from [docker/docker-compose.yaml](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/docker/docker-compose.yaml):

- `postgres`: source database with logical replication enabled through the Debezium example image
- `connect`: Kafka Connect worker running the Debezium PostgreSQL connector
- `kafka`: broker receiving CDC messages
- `zookeeper`: Kafka dependency for this local setup
- `spark-python-consumer`: containerized PySpark streaming job

## What The Practice Does

The source table is created in [docker/init.sql](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/docker/init.sql).

Important details:

- Schema: `bde_module3_lesson4`
- Table: `visits_new`
- Primary key: `(visit_id, visit_time)`
- `device_type` is an enum: `tablet`, `smartphone`, `pc`
- `REPLICA IDENTITY FULL` is enabled so PostgreSQL can emit enough row information for `UPDATE` and `DELETE` CDC events

The connector definition in [docker/register-postgresql-connector.json](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/docker/register-postgresql-connector.json) captures that schema and publishes events with topic prefix `bde`.

The resulting Kafka topic for the table is:

`bde.bde_module3_lesson4.visits_new`

## Repository Structure

- [docker/](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/docker): local infrastructure, connector config, SQL scripts
- [python-example/new_rows_by_device_type_and_os_counter_app.py](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/python-example/new_rows_by_device_type_and_os_counter_app.py): PySpark consumer
- [scala-example/src/main/scala/com/becomedataengineer/NewRowsByDeviceTypeAndOsCounterApp.scala](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/scala-example/src/main/scala/com/becomedataengineer/NewRowsByDeviceTypeAndOsCounterApp.scala): Scala Spark consumer
- [docker/visits_to_insert.sql](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/docker/visits_to_insert.sql): example insert, update, and delete statements

## Event Semantics

Debezium wraps each row change in a JSON envelope. This lesson only uses a small part of it:

- `payload.op = "c"`: create/insert
- `payload.op = "u"`: update
- `payload.op = "d"`: delete

Both Spark examples filter to:

`visit.payload.op = 'c'`

That means:

- inserts affect the aggregation
- updates are visible in Kafka but ignored by the Spark job
- deletes are visible in Kafka but ignored by the Spark job

This is the key teaching point of the practice: CDC streams contain all change types, but your consumer logic decides which events matter.

## Prerequisites

You need:

- Docker Desktop with Compose enabled
- Java 8+ for Scala/Spark
- Maven for the Scala example
- PowerShell

Recommended on Windows:

- use PowerShell, not Git Bash, for the commands in this README
- keep Docker Desktop running before starting the lesson
- use the containerized Python consumer unless you specifically want to work on the Scala example

## Start The Environment

From [docker/](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/docker):

```powershell
docker compose down --volumes
docker compose up -d zookeeper kafka postgres connect
```

Check the containers:

```powershell
docker ps
```

Expected exposed ports:

- PostgreSQL: `5432`
- Kafka Connect REST API: `8083`
- Kafka internal listener: `9092`
- Kafka host listener: `29092`

## Validated Run

The pipeline was validated on this repository with the current files in this lesson. The successful sequence was:

1. `docker compose down --volumes --remove-orphans`
2. `docker compose up -d zookeeper kafka postgres connect`
3. `.\register-postgresql-connector.ps1`
4. `docker compose up -d spark-python-consumer`
5. `Get-Content .\visits_to_insert.sql -Raw | docker exec -i docker_postgres_1 psql -U postgres -d postgres`

Observed results:

- Kafka Connect connector `visits-connector` reached `RUNNING`
- Kafka topic `bde.bde_module3_lesson4.visits_new` was created
- the Python Spark consumer stayed up and consumed the topic
- the console sink printed the expected insert-only counts

Expected console output from the validated run:

```text
+-----------+-----------+-----+
|device_type|device_os  |count|
+-----------+-----------+-----+
|smartphone |iOS 11     |3    |
|smartphone |Android 9.0|3    |
|tablet     |Android 9.0|3    |
+-----------+-----------+-----+
```

## Register The Debezium Connector

From [docker/](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/docker):

```powershell
.\register-postgresql-connector.ps1
```

Check the connector status:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8083/connectors/visits-connector/status" | ConvertTo-Json -Depth 5
```

You should see the connector and its task in `RUNNING` state.

If you need to delete and recreate the connector:

```powershell
Invoke-RestMethod -Method Delete -Uri "http://localhost:8083/connectors/visits-connector"
.\register-postgresql-connector.ps1
```

## Run The Consumer

Choose one consumer implementation.

### Option 1: Python Consumer In Docker

The Python consumer is now part of the Compose stack. It connects to:

- Kafka bootstrap server `kafka:9092`
- checkpoint directory `/opt/app/checkpoint/new_rows_by_device_type_and_os_counter`

To start it:

```powershell
docker compose up -d spark-python-consumer
```

To watch its output:

```powershell
docker compose logs -f spark-python-consumer
```

The checkpoint is persisted on your machine under:

`python-example/checkpoint`

If you want to replay the topic from `EARLIEST`, stop the container and remove that checkpoint folder first.

Recommended order:

1. start infrastructure services
2. register the Debezium connector
3. start `spark-python-consumer`

This order avoids the initial `UnknownTopicOrPartitionException` that happens if Spark starts before Debezium creates the CDC topic.

### Option 2: Scala / Spark

From [scala-example/](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/scala-example):

```powershell
mvn clean package
mvn exec:java -Dexec.mainClass="com.becomedataengineer.NewRowsByDeviceTypeAndOsCounterApp"
```

The Scala example now uses:

- Kafka bootstrap server `localhost:29092`
- local checkpoint directory `scala-example/checkpoint/scala/new_rows_by_device_type_and_os_counter`

This is the correct host-side setup for Windows + Docker Desktop.

## Produce Source Changes In PostgreSQL

Open a PostgreSQL shell:

```powershell
docker exec -it docker_postgres_1 psql -U postgres -d postgres
```

Run the statements from [docker/visits_to_insert.sql](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/docker/visits_to_insert.sql).

The script performs:

1. inserts for visits on `smartphone` and `tablet`
2. an update changing `visit3` to `pc`
3. a delete removing `visit3`

You can also run the SQL file directly from PowerShell:

```powershell
Get-Content .\visits_to_insert.sql -Raw | docker exec -i docker_postgres_1 psql -U postgres -d postgres
```

## Expected Spark Output

Because the consumer keeps only `op = 'c'` events, the aggregation should reflect only the inserted rows.

Expected created-row counts from the insert block:

- `smartphone + iOS 11` -> `3`
- `smartphone + Android 9.0` -> `3`
- `tablet + Android 9.0` -> `3`

The later `UPDATE` and `DELETE` should not change these counts in the current implementation.

## Inspect Raw Kafka CDC Events

To inspect the raw Debezium payloads:

```powershell
docker exec -it docker_kafka_1 kafka-console-consumer.sh `
  --bootstrap-server kafka:9092 `
  --from-beginning `
  --property print.key=true `
  --topic bde.bde_module3_lesson4.visits_new
```

What to look for:

- insert events with `op = "c"` and populated `after`
- update events with `op = "u"` and both `before` and `after`
- delete events with `op = "d"` and empty `after`
- a tombstone message after delete, where the key is present and the value is null

The tombstone exists so Kafka log-compacted topics can eventually remove older values for the same key.

## Why `REPLICA IDENTITY FULL` Matters

The table is configured with:

```sql
ALTER TABLE bde_module3_lesson4.visits_new REPLICA IDENTITY FULL;
```

This is useful here because it allows PostgreSQL and Debezium to emit enough information for updates and deletes even when a full row image is needed.

For a teaching example, this is fine.

For production, be careful:

- `REPLICA IDENTITY FULL` can increase WAL volume
- it is more expensive than relying on a compact primary key or a better replica identity strategy

## What Was Aligned For Windows

The practice was adjusted so it is easier to run by hand on Windows with Docker Desktop:

- the Scala consumer now reads Kafka from `localhost:29092`
- the Python consumer now runs as a Docker container instead of requiring local PySpark on Windows
- the Python consumer now uses `spark-submit` with Kafka package version `3.5.7`
- both consumers now write checkpoints to local persistent directories
- connector registration now has a PowerShell script in [register-postgresql-connector.ps1](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/docker/register-postgresql-connector.ps1)
- the setup and validation commands now use PowerShell-friendly syntax
- the sample SQL file now uses PostgreSQL comment syntax instead of shell-style `#` comments

## Test Notes

The main runtime issues found during validation were:

- the original Bitnami Kafka and Zookeeper image references were no longer usable for this lesson, so the stack was moved to Debezium images
- a custom Python image based on `python:slim` failed during `apt-get`, so the Python consumer now uses the official Spark image and `spark-submit`
- the Spark container needed a writable Ivy cache path because the image defaulted to `HOME=/nonexistent`
- starting the Spark consumer before the Debezium connector created the topic caused `UnknownTopicOrPartitionException`; the documented startup order now avoids that
- PostgreSQL rejected `#` comments in the sample SQL file, so the file was corrected to use `--`

## Recommended Next Improvements

If you want to evolve this practice beyond the current demo:

1. Add a second consumer that handles `u` and `d` events to build a current-state aggregate instead of an insert-only metric.
2. Add documentation for expected Debezium envelope fields such as `before`, `after`, `source`, `ts_ms`, and `op`.
3. Externalize Kafka bootstrap servers and checkpoint paths into environment variables or config files.
4. Add a reset script that removes local checkpoints when you want to replay from `EARLIEST`.

## Troubleshooting

If the connector does not start:

- verify containers are running
- check `http://localhost:8083/connectors/visits-connector/status`
- inspect `docker logs docker_connect_1`

If the Spark job cannot reach Kafka:

- use `localhost:29092` from host-based applications
- verify Kafka is up with `docker logs docker_kafka_1`
- if you changed the code and want to replay everything, delete the local `checkpoint` folder for that app first

If the Python consumer container exits:

- inspect `docker compose logs spark-python-consumer`
- confirm the connector is already running before expecting CDC records
- restart with `docker compose up -d spark-python-consumer` after changing files

If PowerShell script execution is blocked:

- run `powershell -ExecutionPolicy Bypass -File .\register-postgresql-connector.ps1`

If no messages appear in Kafka:

- confirm the connector is registered
- confirm you inserted rows into `bde_module3_lesson4.visits_new`
- confirm you are reading topic `bde.bde_module3_lesson4.visits_new`

## Files To Read First

If you want to understand the practice quickly, start with these files:

1. [docker/init.sql](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/docker/init.sql)
2. [docker/register-postgresql-connector.json](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/docker/register-postgresql-connector.json)
3. [python-example/new_rows_by_device_type_and_os_counter_app.py](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/python-example/new_rows_by_device_type_and_os_counter_app.py)
4. [scala-example/src/main/scala/com/becomedataengineer/NewRowsByDeviceTypeAndOsCounterApp.scala](/d:/STUDY/PRACTICE/practice-data-streaming/01-data-ingestion-real-time/lesson4-cdc/scala-example/src/main/scala/com/becomedataengineer/NewRowsByDeviceTypeAndOsCounterApp.scala)
