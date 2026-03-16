import os
from pathlib import Path

from pyspark.sql import SparkSession, functions, DataFrame
from pyspark.sql.types import StructType, StructField, StringType, LongType

LESSON_ROOT = Path(os.environ.get('LESSON3_DATA_DIR', Path(__file__).resolve().parent / 'data' / 'lesson3'))
FALLBACK_TOPIC_DIRECTORY = LESSON_ROOT / 'fallback' / 'topic=cities'
CHECKPOINT_DIRECTORY = LESSON_ROOT / 'checkpoint'
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:29092')

spark = SparkSession.builder.master("local[*]") \
    .appName('Fallback ingestion for cities topic') \
    .config('spark.jars.packages', 'org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0') \
    .getOrCreate()

input_directory = (FALLBACK_TOPIC_DIRECTORY / '*').as_posix()
input_data_schema = StructType([
    StructField("key", StringType()), StructField("value", StringType())
])
value_json_schema = StructType([
    StructField("time", LongType())
])

input_data = spark.readStream \
    .schema(input_data_schema) \
    .option("latestFirst", False)\
    .option("maxFilesPerTrigger", 100)\
    .json(input_directory) \
    .withColumn('visit_data', functions.from_json("value", value_json_schema)) \
    .select('key', functions.col('visit_data.time').alias('visit_time'), 'value')

input_data_repartitioned_by_key = input_data.repartition(20, 'key')


def write_sorted_data_to_kafka(dataset_repartitioned_by_key: DataFrame, batch_number: int):
    input_data_sorted_events = dataset_repartitioned_by_key.sortWithinPartitions('key', 'visit_time')

    input_data_sorted_events.select(functions.col("key"), functions.col("value")) \
        .write \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("topic", "cities")\
        .save()


write_data_stream = input_data_repartitioned_by_key \
    .writeStream \
    .option("checkpointLocation", CHECKPOINT_DIRECTORY.as_posix()) \
    .trigger(availableNow=True) \
    .foreachBatch(write_sorted_data_to_kafka)

write_data_stream.start().awaitTermination()
