import os

from pyspark.sql import SparkSession, functions
from pyspark.sql.types import StructType, StructField, StringType

bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
topic_name = os.getenv("KAFKA_TOPIC", "bde.bde_module3_lesson4.visits_new")
checkpoint_location = os.getenv(
    "CHECKPOINT_LOCATION",
    "/opt/app/checkpoint/new_rows_by_device_type_and_os_counter"
)

spark = SparkSession.builder.master("local[*]") \
    .appName("lesson4-cdc-new-rows-counter") \
    .getOrCreate()

input_data_schema = StructType([
    StructField("payload", StructType([
        StructField("op", StringType()),
        StructField("after", StructType([
            StructField("device_type", StringType()),
            StructField("device_os", StringType())
        ]))
    ]))
])

input_data_stream = spark.readStream \
    .option("kafka.bootstrap.servers", bootstrap_servers) \
    .option("client.id", "module3_lesson4") \
    .option("subscribe", topic_name) \
    .option("startingOffsets", "EARLIEST") \
    .format("kafka").load()

created_rows_with_schema = input_data_stream.selectExpr("CAST(value AS STRING) AS stringifiedValue") \
    .select(functions.from_json(functions.col("stringifiedValue"), input_data_schema).alias("visit")) \
    .filter("visit.payload.op = 'c'") \
    .select("visit.payload.after.*")

data_count_by_device_type_and_os = created_rows_with_schema.groupBy("device_type", "device_os").count()

write_data_stream = data_count_by_device_type_and_os.writeStream\
    .format("console") \
    .outputMode("update") \
    .option("truncate", "false") \
    .option("checkpointLocation", checkpoint_location)

write_data_stream.start().awaitTermination()
