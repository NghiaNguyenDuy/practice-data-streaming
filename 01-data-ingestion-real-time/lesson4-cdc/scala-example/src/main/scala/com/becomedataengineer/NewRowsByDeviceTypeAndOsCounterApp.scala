package com.becomedataengineer

import org.apache.spark.sql.streaming.OutputMode
import org.apache.spark.sql.types.{StringType, StructField, StructType}
import org.apache.spark.sql.{SparkSession, functions}

object NewRowsByDeviceTypeAndOsCounterApp {

  def main(args: Array[String]): Unit = {
    val sparkSession = SparkSession.builder()
      .appName("lesson4-cdc-new-rows-counter")
      .master("local[*]")
      .getOrCreate()

    val inputDataSchema = StructType(Seq(
      StructField("payload", StructType(Seq(
        StructField("op", StringType),
        StructField("after", StructType(Seq(
          StructField("device_type", StringType),
          StructField("device_os", StringType),
        )
        )))
      ))
    ))

    val inputDataStream = sparkSession.readStream
      .option("kafka.bootstrap.servers", "localhost:29092")
      .option("client.id", "module3_lesson4")
      .option("subscribe", "bde.bde_module3_lesson4.visits_new")
      .option("startingOffsets", "EARLIEST")
      .format("kafka").load()

    import sparkSession.implicits._
    val dataWithSchema = inputDataStream.selectExpr("CAST(value AS STRING) AS stringifiedValue")
      .select(functions.from_json($"stringifiedValue", inputDataSchema).as("visit"))
      // Keep only inserts, we want to know the new rows only
      .filter("visit.payload.op = 'c'")
      .select("visit.payload.after.*")

    val dataCountByDeviceTypeAndOs = dataWithSchema.groupBy("device_type", "device_os")
      .count()

    val writeDataStream = dataCountByDeviceTypeAndOs
      .writeStream
      .format("console")
      .outputMode(OutputMode.Update())
      .option("truncate", "false")
      .option("checkpointLocation", "checkpoint/scala/new_rows_by_device_type_and_os_counter")

    val writeQuery = writeDataStream.start()
    writeQuery.awaitTermination()
  }

}
