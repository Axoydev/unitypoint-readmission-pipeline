# Databricks notebook source

"""
SILVER LAYER: DATA TRANSFORMATION & QUALITY
============================================
Purpose: Clean raw data, validate business logic, quarantine bad records,
         apply feature engineering, and implement SCD Type 2 for patient history.

Business Context:
- Ensure data quality before analytics use
- Handle data anomalies gracefully (quarantine vs fail)
- Track patient attribute changes over time
- Enable longitudinal analysis

Key Techniques:
- Data validation with null checks, date logic, referential integrity
- Quarantine pattern: bad records isolated, pipeline continues
- Feature engineering: length of stay, readmission flags
- SCD Type 2: Track historical patient attributes
- MERGE for upserts

Quality Metrics:
- Target pass rate: 96%+
- Quarantine rate: <5%
"""

# COMMAND ----------

from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import (
    col, 
    when, 
    datediff, 
    lit, 
    current_timestamp,
    row_number,
    max as spark_max,
    to_date,
    coalesce,
    dayofweek,
    month
)
from pyspark.sql.types import BooleanType, IntegerType, DoubleType
import logging

# Initialize Spark
spark = SparkSession.builder.appName("silver_transformation").getOrCreate()

# COMMAND ----------

# Configuration
BRONZE_ENCOUNTERS_PATH = "/mnt/data/bronze/encounters"
BRONZE_LABS_PATH = "/mnt/data/bronze/lab_results"
SILVER_ENCOUNTERS_PATH = "/mnt/data/silver/encounters"
SILVER_PATIENTS_PATH = "/mnt/data/silver/patients"
QUARANTINE_PATH = "/mnt/data/quarantine/encounters"
CURRENT_TIMESTAMP = current_timestamp()

# COMMAND ----------

def validate_encounter_dates(df):
    """
    Validates that discharge_date >= admission_date.
    
    Returns: (df_valid, df_invalid)
    - df_valid: Records with valid dates
    - df_invalid: Records with invalid dates (quarantined)
    """
    
    df_with_flag = df.withColumn(
        "date_valid",
        when(col("discharge_date") >= col("admission_date"), True)
        .otherwise(False)
    )
    
    df_valid = df_with_flag.filter(col("date_valid") == True).drop(col("date_valid"))
    df_invalid = df_with_flag.filter(col("date_valid") == False).drop(col("date_valid"))
    
    return df_valid, df_invalid

# COMMAND ----------

def validate_required_fields(df):
    """
    Validates that required fields are not null.
    
    Required fields:
    - patient_mrn: Medical record number
    - encounter_id: Unique encounter identifier
    - admission_date: When patient was admitted
    - diagnosis: Primary diagnosis
    """
    
    # Mark records with missing required fields
    df_with_flag = df.withColumn(
        "required_fields_valid",
        when(
            (col("patient_mrn").isNotNull()) &
            (col("encounter_id").isNotNull()) &
            (col("admission_date").isNotNull()) &
            (col("diagnosis").isNotNull()),
            True
        ).otherwise(False)
    )
    
    df_valid = df_with_flag.filter(col("required_fields_valid") == True).drop(col("required_fields_valid"))
    df_invalid = df_with_flag.filter(col("required_fields_valid") == False).drop(col("required_fields_valid"))
    
    return df_valid, df_invalid

# COMMAND ----------

def write_quarantine(df, reason: str) -> int:
    """
    Writes quarantined records to a separate location for investigation.
    
    Includes metadata about why the record was quarantined.
    """
    
    if df.count() == 0:
        return 0
    
    df_quarantine = df.withColumn("quarantine_reason", lit(reason)) \
                      .withColumn("quarantine_timestamp", CURRENT_TIMESTAMP)
    
    df_quarantine.write \
        .format("delta") \
        .mode("append") \
        .partitionBy("quarantine_timestamp") \
        .save(QUARANTINE_PATH)
    
    count = df_quarantine.count()
    print(f"⚠️  Quarantined {count} records - Reason: {reason}")
    return count

# COMMAND ----------

def feature_engineering(df):
    """
    Creates new features for downstream analytics.
    
    New columns:
    - length_of_stay: Days between admission and discharge
    - is_weekend_admission: Boolean flag
    - admission_month: Month of admission (seasonal analysis)
    - los_category: Bucketed length of stay (short/medium/long)
    """
    
    df_features = df.withColumn(
        "length_of_stay",
        datediff(col("discharge_date"), col("admission_date"))
    ).withColumn(
        "is_weekend_admission",
        when(dayofweek(col("admission_date")).isin([1, 7]), True).otherwise(False)
    ).withColumn(
        "admission_month",
        month(col("admission_date"))
    ).withColumn(
        "los_category",
        when(col("length_of_stay") <= 3, "short")
        .when(col("length_of_stay") <= 7, "medium")
        .otherwise("long")
    )
    
    return df_features

# COMMAND ----------

def implement_scd_type_2(df_new, target_path: str) -> None:
    """
    Implements Slowly Changing Dimension Type 2 for patient attributes.
    
    SCD Type 2 tracks historical changes by:
    - Adding effective_date (when change became active)
    - Adding end_date (when change ended / was replaced)
    - Marking current record with is_current = True
    - Keeping historical records with is_current = False
    
    Example:
    Before: Patient John Doe had insurance Plan A
    After: Patient John Doe changed to Plan B
    
    Result in table:
    | patient_id | insurance_plan | effective_date | end_date   | is_current |
    | 101        | Plan A         | 2023-01-01     | 2024-06-30 | False      |
    | 101        | Plan B         | 2024-07-01     | NULL       | True       |
    """
    
    # For this demo, we'll track patient demographics changes
    df_new_scd = df_new.withColumn("effective_date", col("ingestion_date")) \
                       .withColumn("end_date", lit(None)) \
                       .withColumn("is_current", lit(True))
    
    df_new_scd.createOrReplaceTempView("new_patients")
    
    try:
        # If table exists, mark old records as historical and insert new current record
        spark.sql(f"""
            MERGE INTO delta.`{target_path}` target
            USING new_patients source
            ON target.patient_mrn = source.patient_mrn 
               AND target.is_current = True
            WHEN MATCHED AND target.hospital != source.hospital 
            THEN UPDATE SET
                is_current = False,
                end_date = source.effective_date
            WHEN NOT MATCHED 
            THEN INSERT *
        """)
        
        # Insert new current record for changed patients
        spark.sql(f"""
            INSERT INTO delta.`{target_path}`
            SELECT 
                source.patient_mrn,
                source.hospital,
                source.effective_date,
                CAST(NULL AS DATE) as end_date,
                True as is_current
            FROM new_patients source
            WHERE NOT EXISTS (
                SELECT 1 FROM delta.`{target_path}` t 
                WHERE t.patient_mrn = source.patient_mrn 
                AND t.hospital = source.hospital
                AND t.is_current = True
            )
        """)
        
        print(f"✅ SCD Type 2 merge completed for patient dimension")
        
    except:
        # Table doesn't exist, create it
        df_new_scd.write.format("delta").mode("overwrite").save(target_path)
        print(f"✅ Created new patient dimension table with SCD Type 2")

# COMMAND ----------

def deduplicate_encounters(df):
    """
    Removes duplicate encounters, keeping the most recent record.
    
    In case of duplicates, keeps the record with:
    - Latest ingestion_timestamp
    - Lowest row number
    """
    
    window_spec = Window.partitionBy("encounter_id").orderBy(
        col("ingestion_timestamp").desc()
    )
    
    df_dedup = df.withColumn("rn", row_number().over(window_spec)) \
                 .filter(col("rn") == 1) \
                 .drop(col("rn"))
    
    initial_count = df.count()
    final_count = df_dedup.count()
    duplicates = initial_count - final_count
    
    if duplicates > 0:
        print(f"⚠️  Found and removed {duplicates} duplicate encounter records")
    
    return df_dedup

# COMMAND ----------

def transform_silver_encounters() -> None:
    """
    Main function: Execute full Silver layer transformation pipeline.
    """
    
    print("=" * 70)
    print("SILVER LAYER: DATA TRANSFORMATION & QUALITY")
    print("=" * 70)
    
    # Step 1: Read Bronze data
    print("\n[1/7] Reading Bronze layer data...")
    df_bronze = spark.read.format("delta").load(BRONZE_ENCOUNTERS_PATH)
    initial_count = df_bronze.count()
    print(f"✅ Loaded {initial_count:,} records from Bronze layer")
    
    # Step 2: Deduplicate
    print("\n[2/7] Deduplicating encounters...")
    df_dedup = deduplicate_encounters(df_bronze)
    
    # Step 3: Validate required fields
    print("\n[3/7] Validating required fields...")
    df_valid, df_quarantine_fields = validate_required_fields(df_dedup)
    quarantine_count_1 = write_quarantine(df_quarantine_fields, "missing_required_fields")
    
    # Step 4: Validate date logic
    print("\n[4/7] Validating date logic...")
    df_valid, df_quarantine_dates = validate_encounter_dates(df_valid)
    quarantine_count_2 = write_quarantine(df_quarantine_dates, "invalid_date_logic")
    
    # Step 5: Feature engineering
    print("\n[5/8] Performing feature engineering...")
    df_features = feature_engineering(df_valid)
    print(f"✅ Added features: length_of_stay, is_weekend_admission, los_category")
    
    # Step 6: Join with lab results (enrich encounters with lab data)
    print("\n[6/8] Enriching encounters with lab data...")
    try:
        df_labs = spark.read.format("delta").load(BRONZE_LABS_PATH)
        # Count abnormal labs per encounter (simple enrichment)
        df_labs_agg = df_labs.groupBy("encounter_id").agg(
            count(col("lab_id")).alias("lab_count")
        )
        df_features = df_features.join(df_labs_agg, on="encounter_id", how="left") \
            .fillna(0, subset=["lab_count"])
        print(f"✅ Joined lab data: added lab_count column")
    except Exception as e:
        print(f"⚠️  Lab data not available yet: {str(e)}. Continuing without labs.")
    
    # Step 7: Add data quality metadata
    print("\n[7/8] Adding data quality metadata...")
    df_silver = df_features.withColumn("data_quality_flag", lit("clean")) \
                            .withColumn("silver_processing_timestamp", CURRENT_TIMESTAMP)
    
    # Step 8: Write to Silver layer
    print("\n[8/8] Writing to Silver layer...")
    df_silver.write \
        .format("delta") \
        .mode("overwrite") \
        .partitionBy("admission_date") \
        .save(SILVER_ENCOUNTERS_PATH)
    print(f"✅ Written {df_silver.count():,} clean records to Silver layer")
    
    # Quality summary
    print("\n" + "=" * 70)
    print("✅ SILVER TRANSFORMATION COMPLETE")
    print("=" * 70)
    
    total_quarantine = quarantine_count_1 + quarantine_count_2
    pass_rate = (df_silver.count() / initial_count * 100)
    
    print(f"\nData Quality Summary:")
    print(f"  Initial records:        {initial_count:,}")
    print(f"  Quarantined records:    {total_quarantine:,}")
    print(f"  Clean records:          {df_silver.count():,}")
    print(f"  Pass rate:              {pass_rate:.1f}%")
    print(f"\n  Quarantine breakdown:")
    print(f"    - Missing required:   {quarantine_count_1:,}")
    print(f"    - Invalid dates:      {quarantine_count_2:,}")
    
    # Feature statistics
    print(f"\nFeature Statistics:")
    stats = df_silver.describe(["length_of_stay"]).collect()
    for row in stats:
        print(f"  {row[0]}: {row[1]}")

# COMMAND ----------

# Execute the transformation
transform_silver_encounters()

# COMMAND ----------

# SCD Type 2 for Patient Dimension (Simplified)
print("\n" + "=" * 70)
print("IMPLEMENTING SCD TYPE 2 FOR PATIENT DIMENSION")
print("=" * 70)

df_patients = spark.read.format("delta").load(SILVER_ENCOUNTERS_PATH) \
    .select("patient_mrn", "hospital", "ingestion_date") \
    .distinct()

implement_scd_type_2(df_patients, SILVER_PATIENTS_PATH)

# COMMAND ----------

# Data Quality Validation Output
print("\n📊 SILVER LAYER QUALITY REPORT:")
df_silver_check = spark.read.format("delta").load(SILVER_ENCOUNTERS_PATH)

print(f"\nMissing Values Check:")
missing_columns = []
for col_name in df_silver_check.columns:
    null_count = df_silver_check.filter(col(col_name).isNull()).count()
    if null_count > 0:
        missing_columns.append(f"  ⚠️  {col_name}: {null_count}")

if not missing_columns:
    print("  ✅ No missing values in critical fields")
else:
    for msg in missing_columns:
        print(msg)

print(f"\nFeature Distribution:")
los_dist = df_silver_check.groupBy("los_category").count().collect()
for row in los_dist:
    print(f"  Length of Stay '{row[0]}': {row[1]:,} records")

print(f"\nTable Metadata:")
print(f"  Total records: {df_silver_check.count():,}")
print(f"  Columns: {len(df_silver_check.columns)}")
print(f"  Partitions: {df_silver_check.rdd.getNumPartitions()}")
