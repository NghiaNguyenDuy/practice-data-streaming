**Open the project components (fallback-pipeline and web-service) in 2 different PyCharm windows.**
 
1. Start the Docker containers `docker-compose down --volumes; docker-compose up`
2. Go to [http://localhost:803/](http://localhost:803/) and check if it opens correctly. The goal of the exercise
   is to navigate the site and observe the tracking information delivered to our web service.
3. Start the web service from [webservice](web-service%2Fwebservice)
4. Open Kafka console `docker exec -ti docker_kafka_1  kafka-console-consumer.sh --bootstrap-server localhost:29092 --topic cities`
5. Explain the [endpoint_data_ingestion.py](web-service%2Fwebservice%2Fendpoint_data_ingestion.py)
   * It creates a new Kafka producer and an in-memory status holder 
   * By default, each message has the delivery status set to false
   * Whenever we get a success callback, we update the status to true 
   * We remove the list of unsuccessfully delivered messages in the `callback_data_holder.get_failed_deliveries()`
   * When there are some failures, the JavaScript code puts them to the browser local storage for retries
6. Visit at least 5 different pages to produce some data.
7. Change the `INGESTION_ENDPOINT` in the `collect_clicks.js` file. It should point to 'http://localhost:8080/dataingestionfallback/ingest/cities'
8. Navigate the website to see the new endpoint called (e.g. from Developer Tools > Network)
9. Stop the Kafka broker `docker stop docker_kafka_1`
10. From now on, any request reaching the fallback endpoint should write the data to files. 
   * Visit few pages to start the delivery
   * Check the written directory:
   ```
   tree /tmp/bde-snippets-3/lesson3/fallback/
   less /tmp/bde-snippets-3/lesson3/fallback/* 
   ```
11. Restart the Kafka broker `docker start docker_kafka_1`
12. Go to the **fallback-pipeline** project
13. Explain the [ingestion_pipeline.py](fallback-pipeline%2Fingestion_pipeline.py)
   * `trigger(availableNow=True)` with the `checkpointLocation` to ensure not processing the same files again
   * `repartition` with the `sortWithinPartitions` to deliver data in order for each key
14. Restart the cities console consumer `docker exec -ti docker_kafka_1  kafka-console-consumer.sh --bootstrap-server localhost:29092 --topic cities`
15. Start the job and switch to the console. You should see data from the fallback storage coming in.
