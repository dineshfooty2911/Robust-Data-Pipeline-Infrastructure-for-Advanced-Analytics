import findspark
findspark.init()

from pyspark.sql import SparkSession

# Create a Spark session
spark = SparkSession.builder \
    .appName("Simple Spark Test") \
    .config("spark.ui.port", "4050") \
    .getOrCreate()

# Create a simple DataFrame
data = [("Alice", 29), ("Bob", 31), ("Cathy", 28)]
columns = ["Name", "Age"]

df = spark.createDataFrame(data, columns)

# Show the DataFrame content
df.show()

# Print the DataFrame schema
df.printSchema()

# Perform a simple operation
df.select("Name").show()

# Stop the Spark session
spark.stop()
