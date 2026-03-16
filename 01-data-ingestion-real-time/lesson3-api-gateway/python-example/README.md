# Lesson 3: API Gateway With Kafka Fallback

This practice demonstrates two ingestion paths for browser click events:

- primary path: website -> Flask web service -> Kafka topic `cities`
- fallback path: website -> Flask fallback endpoint -> file storage -> Spark replay -> Kafka topic `cities`

## Project Layout

- `docker/`
  - `docker-compose.yaml`: local Kafka, ZooKeeper, demo website, and optional fallback pipeline container
  - `www/collect_clicks.js`: browser-side event capture and delivery
- `python-example/web-service/`
  - Flask API with primary and fallback ingestion endpoints
- `python-example/fallback-pipeline/`
  - Spark replay job and Docker image for replaying stored fallback files into Kafka

## Prerequisites

- Docker Desktop
- Python 3.11 for the local web service

The fallback pipeline no longer requires a local Java or Hadoop installation because it runs in Docker.

## Setup

### 1. Start the base Docker stack

From `docker/`:

```powershell
docker compose up -d
```

This starts:

- `docker_zookeeper_1`
- `docker_kafka_1`
- demo website on `http://localhost:803`

### 2. Start the web service locally

From `python-example/web-service/`:

```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m webservice.api
```

On startup the service logs:

- resolved lesson data root
- resolved fallback directory

By default fallback files are written under:

```text
python-example/fallback-pipeline/data/lesson3/fallback
```

## Scenario 1: Primary Ingestion

Use this to verify normal delivery to Kafka.

### 1. Point the website to the primary endpoint

In `docker/www/collect_clicks.js`, use:

```javascript
// var INGESTION_ENDPOINT = 'http://localhost:8080/dataingestionfallback/ingest/cities';
var INGESTION_ENDPOINT = 'http://localhost:8080/dataingestion/ingest/cities';
```

### 2. Open a Kafka consumer

```powershell
docker exec -it docker_kafka_1 kafka-console-consumer --bootstrap-server localhost:29092 --topic cities --from-beginning
```

### 3. Generate click events

- open `http://localhost:803`
- hard refresh the page after changing the JavaScript file
- clear browser local storage if needed
- visit at least 5 pages because `BUFFER_SIZE = 5`

### 4. Expected result

In the web-service logs you should see:

- `Primary endpoint invoked`
- `Primary delivery result: ... success=True`

In the Kafka console you should see click payloads arriving on topic `cities`.

## Scenario 2: Fallback Capture

Use this to verify that clicks are stored on disk when Kafka is unavailable.

### 1. Point the website to the fallback endpoint

In `docker/www/collect_clicks.js`, use:

```javascript
// var INGESTION_ENDPOINT = 'http://localhost:8080/dataingestion/ingest/cities';
var INGESTION_ENDPOINT = 'http://localhost:8080/dataingestionfallback/ingest/cities';
```

### 2. Clear browser state and hard refresh

In browser devtools:

```javascript
localStorage.clear()
```

Then hard refresh the website.

### 3. Stop Kafka

```powershell
docker stop docker_kafka_1
```

### 4. Generate click events

Visit at least 5 pages on the demo website.

### 5. Expected result

In the web-service logs you should see:

- `Fallback endpoint invoked`
- `broker_reachable=False`
- `Kafka bootstrap servers are unreachable; storing batch directly to fallback storage.`
- `Fallback batch stored on disk: file=...`

The generated files should appear under:

```text
python-example/fallback-pipeline/data/lesson3/fallback/topic=cities
```

You can inspect them with:

```powershell
Get-ChildItem -Recurse .\python-example\fallback-pipeline\data\lesson3
Get-Content .\python-example\fallback-pipeline\data\lesson3\fallback\topic=cities\*
```

## Scenario 3: Replay Fallback Data To Kafka

Use this after fallback files have been written.

### 1. Restart Kafka

```powershell
docker start docker_kafka_1
```

### 2. Start the Kafka consumer

```powershell
docker exec -it docker_kafka_1 kafka-console-consumer --bootstrap-server localhost:29092 --topic cities --from-beginning
```

### 3. Run the fallback pipeline

From `docker/`:

```powershell
docker compose --profile fallback-pipeline up --build fallback_pipeline
```

For a one-shot replay container:

```powershell
docker compose --profile fallback-pipeline run --rm fallback_pipeline
```

### 4. Expected result

- the Spark job reads files from `python-example/fallback-pipeline/data/lesson3/fallback/topic=cities`
- the job republishes them to Kafka using broker `kafka:9092`
- the Kafka console shows the replayed events

## Troubleshooting

### No fallback files are written

Check these in order:

1. `collect_clicks.js` is using the fallback endpoint, not the primary endpoint.
2. The Flask app was restarted after code changes.
3. Kafka is actually stopped:

```powershell
docker ps -a
```

4. The web-service logs show `broker_reachable=False`.
5. You are checking the actual topic directory:

```text
python-example/fallback-pipeline/data/lesson3/fallback/topic=cities
```

### Kafka consumer command fails

This project now uses the Confluent Kafka image, so use:

```powershell
docker exec -it docker_kafka_1 kafka-console-consumer --bootstrap-server localhost:29092 --topic cities --from-beginning
```

not `kafka-console-consumer.sh`.

### Fallback pipeline fails on local Java/Hadoop

Do not run the Spark replay locally unless you intentionally want to manage Java and Hadoop on Windows. Use the Dockerized fallback pipeline instead.
