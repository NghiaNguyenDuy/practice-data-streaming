1. Start Docker containers `docker-compose down --volumes; docker-compose up`
2. Present `init.sql`
   * We have a `bde_module3_lesson4.visits_new` table that will be streamed by Debezium to an Apache Kafka topic
   * All new rows are processed by the [NewRowsByDeviceTypeAndOsCounterApp.scala](src%2Fmain%2Fscala%2Fcom%2Fbecomedataengineer%2FNewRowsByDeviceTypeAndOsCounterApp.scala)
3. Register the Debezium connector:
```
curl -i -X POST -H "Accept:application/json" -H  "Content-Type:application/json" http://localhost:8083/connectors/ -d @register-postgresql-connector.json
``` 
ℹ️ On Window you may need to call `curl.exe`

4. Start the [NewRowsByDeviceTypeAndOsCounterApp.scala](src%2Fmain%2Fscala%2Fcom%2Fbecomedataengineer%2FNewRowsByDeviceTypeAndOsCounterApp.scala) 
   to consume new messages:
   * The code only keeps the created rows (`visit.payload.op = 'c'`) and counts the number of rows for each
     (device_type, device_os) pair
5. Insert new rows:
    * `docker exec -ti docker_postgres_1 psql -U postgres -d postgres`
    * 
   ```
    INSERT INTO bde_module3_lesson4.visits_new VALUES
    ('visit3', 1, 'home.html', NOW() + '1 second', 'smartphone', 'iOS 11'),
    ('visit3', 1, 'articles.html', NOW() + '2 seconds', 'smartphone', 'iOS 11'),
    ('visit3', 1, 'contact.html', NOW() + '3 seconds', 'smartphone', 'iOS 11'),
    
    ('visit4', 2, 'home.html', NOW() + '2 seconds', 'smartphone', 'Android 9.0'),
    ('visit4', 2, 'about.html', NOW()+ '3 seconds', 'smartphone', 'Android 9.0'),
    ('visit4', 2, 'contact.html', NOW()+ '4 seconds', 'smartphone', 'Android 9.0'),
    
    ('visit5', 2, 'home.html', NOW()+ '2 seconds', 'tablet', 'Android 9.0'),
    ('visit5', 2, 'about.html', NOW()+ '3 seconds', 'tablet', 'Android 9.0'),
    ('visit5', 2, 'contact.html', NOW()+ '4 seconds', 'tablet', 'Android 9.0');
      ```
6. Check the Spark job outcome.
7. Start the Kafka console consumer
```
docker exec -ti docker_kafka_1 kafka-console-consumer.sh \
    --bootstrap-server kafka:9092 \
    --from-beginning \
    --property print.key=true \
    --topic bde.bde_module3_lesson4.visits_new
```
    * `"op":"c"` stands for the create event
8. Return to the PostgreSQL console and perform an update
```
UPDATE bde_module3_lesson4.visits_new SET device_type = 'pc' WHERE visit_id = 'visit3';
```
  * We're keeping only the create events in Spark job, so we don't take these updates into account
  * However, they're correctly present in the stream; you can see it in the Kafka console consumer
  * The operation is possible thanks to the `REPLICA IDENTITY FULL`, as per [documentation](https://debezium.io/documentation/reference/stable/connectors/postgresql.html#postgresql-replica-identity)
>A published table must have a "replica identity" configured in order to be able to replicate UPDATE and DELETE operations, so that appropriate rows to update or delete can be identified on the subscriber side. By default, this is the primary key, if there is one. Another unique index (with certain additional requirements) can also be set to be the replica identity. If the table does not have any suitable key, then it can be set to replica identity "full", which means the entire row becomes the key. This, however, is very inefficient and should only be used as a fallback if no other solution is possible. If a replica identity other than "full" is set on the publisher side, a replica identity comprising the same or fewer columns must also be set on the subscriber side. See REPLICA IDENTITY for details on how to set the replica identity. If a table without a replica identity is added to a publication that replicates UPDATE or DELETE operations then subsequent UPDATE or DELETE operations will cause an error on the publisher. INSERT operations can proceed regardless of any replica identity

9. Return to the PostgreSQL console and perform a delete
```
DELETE FROM bde_module3_lesson4.visits_new WHERE visit_id = 'visit3';
```
  * In the pushed rows you can now see a defined (_before_) and an empty (_after_) parts
  * You may also notice the presence of an extra message of the `Event Key` type
    * It's a tombstone message for Kafka so that Kafka topic can remove the records associated with the deleted primary key. It'll do that because of the null payload which in Kafka nomenclature means "delete tombstone"
      Tombstone events: [https://debezium.io/documentation/reference/stable/connectors/postgresql.html#postgresql-update-events ](https://debezium.io/documentation/reference/stable/connectors/postgresql.html#postgresql-update-events)
      > When a row is deleted, the delete event value still works with log compaction, because Kafka can remove all earlier messages that have that same key. However, for Kafka to remove all messages that have that same key, the message value must be null. To make this possible, the PostgreSQL connector follows a delete event with a special tombstone event that has the same key but a null value.
