from pyspark.sql import SparkSession, functions, DataFrame
from pyspark.sql.types import StructType, StructField, StringType, LongType

spark = SparkSession.builder.master("local[*]") \
    .appName('Fallback ingestion for cities topic') \
    .config('spark.jars.packages', 'org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.1') \
    .getOrCreate()

input_directory = "/tmp/bde-snippets-3/lesson3/fallback/topic=cities/*"
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
        .option("kafka.bootstrap.servers", "localhost:29092") \
        .option("topic", "cities")\
        .save()


write_data_stream = input_data_repartitioned_by_key \
    .writeStream \
    .option("checkpointLocation", "/tmp/bde-snippets-3/lesson3/checkpoint") \
    .trigger(availableNow=True) \
    .foreachBatch(write_sorted_data_to_kafka)

write_data_stream.start().awaitTermination()
