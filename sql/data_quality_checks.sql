-- SQL Data Quality Checks for Healthcare ETL Pipeline
-- Purpose: Validate data integrity across Bronze, Silver, and Gold layers
-- Usage: Run these queries after each pipeline execution to ensure data quality

-- ===================================================================
-- BRONZE LAYER DATA QUALITY CHECKS
-- ===================================================================

-- [BRONZE-01] Check for duplicate encounters
SELECT 
    'DUPLICATE_ENCOUNTERS' AS check_id,
    encounter_id,
    COUNT(*) as duplicate_count
FROM bronze.encounters
GROUP BY encounter_id
HAVING COUNT(*) > 1
LIMIT 100;

-- [BRONZE-02] Check for null values in required fields
SELECT 
    'NULL_REQUIRED_FIELDS' AS check_id,
    SUM(CASE WHEN patient_mrn IS NULL THEN 1 ELSE 0 END) as null_patient_mrn,
    SUM(CASE WHEN encounter_id IS NULL THEN 1 ELSE 0 END) as null_encounter_id,
    SUM(CASE WHEN admission_date IS NULL THEN 1 ELSE 0 END) as null_admission_date,
    SUM(CASE WHEN hospital IS NULL THEN 1 ELSE 0 END) as null_hospital
FROM bronze.encounters;

-- [BRONZE-03] Check data type consistency
SELECT 
    'DATA_TYPE_CHECK' AS check_id,
    COUNT(*) as total_records,
    SUM(CASE WHEN TRY_CAST(patient_mrn AS STRING) IS NULL THEN 1 ELSE 0 END) as invalid_mrn,
    SUM(CASE WHEN TRY_CAST(admission_date AS DATE) IS NULL THEN 1 ELSE 0 END) as invalid_date
FROM bronze.encounters;

-- [BRONZE-04] Check data volume expectations
SELECT 
    'VOLUME_CHECK' AS check_id,
    COUNT(*) as total_records,
    COUNT(DISTINCT patient_mrn) as unique_patients,
    COUNT(DISTINCT hospital) as unique_hospitals,
    MIN(admission_date) as earliest_admission,
    MAX(admission_date) as latest_admission
FROM bronze.encounters;

-- ===================================================================
-- SILVER LAYER DATA QUALITY CHECKS
-- ===================================================================

-- [SILVER-01] Validate date logic (discharge >= admission)
SELECT 
    'INVALID_DATE_LOGIC' AS check_id,
    COUNT(*) as invalid_records
FROM silver.encounters
WHERE discharge_date < admission_date;

-- [SILVER-02] Check data completeness after cleaning
SELECT 
    'DATA_COMPLETENESS' AS check_id,
    COUNT(*) as total_records,
    ROUND(COUNT(*) / (
        SELECT COUNT(*) FROM bronze.encounters
    ) * 100, 2) as pass_rate_pct,
    SUM(CASE WHEN length_of_stay IS NULL THEN 1 ELSE 0 END) as null_los,
    SUM(CASE WHEN admission_date IS NULL THEN 1 ELSE 0 END) as null_admission_date
FROM silver.encounters;

-- [SILVER-03] Feature engineering validation
SELECT 
    'FEATURE_VALIDATION' AS check_id,
    COUNT(*) as total_records,
    COUNT(CASE WHEN length_of_stay >= 0 THEN 1 END) as valid_los,
    COUNT(CASE WHEN is_weekend_admission IN (0, 1) THEN 1 END) as valid_weekend_flag,
    COUNT(CASE WHEN los_category IN ('short', 'medium', 'long') THEN 1 END) as valid_category,
    MIN(length_of_stay) as min_los,
    MAX(length_of_stay) as max_los
FROM silver.encounters;

-- [SILVER-04] Quarantine records check
SELECT 
    'QUARANTINE_SUMMARY' AS check_id,
    quarantine_reason,
    COUNT(*) as quarantine_count,
    ROUND(COUNT(*) / (
        SELECT COUNT(*) FROM bronze.encounters + (
            SELECT COUNT(*) FROM quarantine.encounters
        )
    ) * 100, 2) as quarantine_rate_pct,
    MIN(quarantine_timestamp) as first_quarantine,
    MAX(quarantine_timestamp) as last_quarantine
FROM quarantine.encounters
GROUP BY quarantine_reason;

-- [SILVER-05] SCD Type 2 patient dimension validation
SELECT 
    'SCD_TYPE2_VALIDATION' AS check_id,
    COUNT(*) as total_patient_records,
    COUNT(CASE WHEN is_current = TRUE THEN 1 END) as current_records,
    COUNT(CASE WHEN is_current = FALSE THEN 1 END) as historical_records,
    COUNT(DISTINCT patient_mrn) as unique_patients,
    COUNT(CASE WHEN is_current = TRUE AND end_date IS NOT NULL THEN 1 END) as data_quality_issues
FROM silver.patients
WHERE is_current = TRUE AND end_date IS NOT NULL;

-- ===================================================================
-- GOLD LAYER DATA QUALITY CHECKS
-- ===================================================================

-- [GOLD-01] Readmission metrics validation
SELECT 
    'READMISSION_METRICS' AS check_id,
    COUNT(*) as total_records,
    SUM(readmissions_30d) as total_30d_readmissions,
    SUM(readmissions_90d) as total_90d_readmissions,
    ROUND(SUM(readmissions_30d) / COUNT(*) * 100, 2) as readmission_rate_30d_pct,
    ROUND(SUM(readmissions_90d) / COUNT(*) * 100, 2) as readmission_rate_90d_pct,
    ROUND(AVG(avg_los), 2) as avg_length_of_stay,
    ROUND(AVG(avg_risk_score), 2) as avg_risk_score
FROM gold.readmission_metrics;

-- [GOLD-02] Hospital-level metrics consistency
SELECT 
    'HOSPITAL_METRICS_CHECK' AS check_id,
    hospital,
    total_encounters,
    readmissions_30d,
    readmissions_90d,
    ROUND(readmission_rate_30d, 2) as readmission_rate_pct,
    ROUND(avg_los, 2) as avg_los,
    ROUND(avg_risk_score, 2) as avg_risk_score
FROM gold.hospital_metrics
ORDER BY readmission_rate_30d DESC
LIMIT 10;

-- [GOLD-03] Risk score distribution
SELECT 
    'RISK_SCORE_DISTRIBUTION' AS check_id,
    CASE 
        WHEN avg_risk_score < 20 THEN 'LOW'
        WHEN avg_risk_score < 40 THEN 'MEDIUM'
        ELSE 'HIGH'
    END as risk_category,
    COUNT(*) as patient_count,
    ROUND(COUNT(*) / (SELECT COUNT(*) FROM gold.readmission_metrics) * 100, 2) as percentage,
    ROUND(AVG(avg_risk_score), 2) as avg_score,
    ROUND(MIN(avg_risk_score), 2) as min_score,
    ROUND(MAX(avg_risk_score), 2) as max_score
FROM gold.readmission_metrics
GROUP BY risk_category
ORDER BY avg_score DESC;

-- [GOLD-04] Aggregate consistency check
SELECT 
    'AGGREGATE_CONSISTENCY' AS check_id,
    COUNT(*) as gold_records,
    COUNT(DISTINCT patient_mrn) as unique_patients,
    COUNT(CASE WHEN total_encounters = 0 THEN 1 END) as zero_encounters,
    COUNT(CASE WHEN readmissions_30d > total_encounters THEN 1 END) as data_integrity_issues
FROM gold.readmission_metrics;

-- [GOLD-05] Performance metrics (post-optimization)
SELECT 
    'OPTIMIZATION_METRICS' AS check_id,
    table_name,
    file_count,
    avg_file_size_mb,
    total_size_gb,
    optimization_timestamp
FROM system.table_statistics
WHERE table_name IN ('silver.encounters', 'gold.readmission_metrics', 'gold.hospital_metrics')
ORDER BY optimization_timestamp DESC;

-- ===================================================================
-- CROSS-LAYER REFERENTIAL INTEGRITY CHECKS
-- ===================================================================

-- [CROSS-LAYER-01] Validate patient references exist
SELECT 
    'MISSING_PATIENT_REFS' AS check_id,
    COUNT(DISTINCT e.patient_mrn) as encounters_with_missing_patients
FROM silver.encounters e
LEFT JOIN silver.patients p ON e.patient_mrn = p.patient_mrn AND p.is_current = TRUE
WHERE p.patient_mrn IS NULL;

-- [CROSS-LAYER-02] Validate encounter references in gold layer
SELECT 
    'MISSING_ENCOUNTER_REFS' AS check_id,
    COUNT(*) as gold_records_missing_encounters
FROM gold.readmission_metrics g
LEFT JOIN silver.encounters e ON g.patient_mrn = e.patient_mrn
WHERE e.patient_mrn IS NULL;

-- ===================================================================
-- PERFORMANCE & RESOURCE CHECKS
-- ===================================================================

-- [PERFORMANCE-01] Table size and partition analysis
SELECT 
    'TABLE_SIZE_ANALYSIS' AS check_id,
    'silver.encounters' as table_name,
    COUNT(*) as record_count,
    COUNT(DISTINCT ingestion_date) as partition_count,
    ROUND(COUNT(*) / COUNT(DISTINCT ingestion_date), 0) as records_per_partition
FROM silver.encounters
GROUP BY 1, 2
UNION ALL
SELECT 
    'TABLE_SIZE_ANALYSIS',
    'gold.readmission_metrics',
    COUNT(*),
    COUNT(DISTINCT metric_date),
    ROUND(COUNT(*) / COUNT(DISTINCT metric_date), 0)
FROM gold.readmission_metrics
GROUP BY 1, 2;

-- [PERFORMANCE-02] Query performance benchmarks
SELECT 
    'QUERY_PERFORMANCE' AS check_id,
    'patient_lookup' as query_type,
    COUNT(*) as result_count,
    APPROX_PERCENTILE(query_time_ms, 0.5) as median_time_ms,
    APPROX_PERCENTILE(query_time_ms, 0.95) as p95_time_ms,
    APPROX_PERCENTILE(query_time_ms, 0.99) as p99_time_ms
FROM system.query_logs
WHERE query_text LIKE '%WHERE patient_mrn%'
  AND execution_date > CURRENT_DATE - INTERVAL 1 DAY;

-- ===================================================================
-- GOVERNANCE & COMPLIANCE CHECKS
-- ===================================================================

-- [COMPLIANCE-01] Sensitive data tagging check
SELECT 
    'PII_TAGGING_VALIDATION' AS check_id,
    table_name,
    column_name,
    data_classification,
    COUNT(*) as records_with_classification
FROM system.column_metadata
WHERE data_classification IN ('PII', 'PHI', 'SENSITIVE')
GROUP BY table_name, column_name, data_classification;

-- [COMPLIANCE-02] Data access audit
SELECT 
    'DATA_ACCESS_AUDIT' AS check_id,
    accessed_table,
    user_name,
    access_type,
    COUNT(*) as access_count,
    MIN(access_timestamp) as first_access,
    MAX(access_timestamp) as last_access
FROM system.audit_logs
WHERE access_timestamp > CURRENT_TIMESTAMP - INTERVAL 7 DAY
  AND accessed_table LIKE 'gold.%'
GROUP BY accessed_table, user_name, access_type
ORDER BY access_count DESC;

-- ===================================================================
-- SUMMARY DASHBOARD QUERY
-- ===================================================================

-- [DASHBOARD-01] Pipeline health summary
WITH bronze_check AS (
    SELECT 
        COUNT(*) as total_records,
        COUNT(DISTINCT patient_mrn) as unique_patients
    FROM bronze.encounters
),
silver_check AS (
    SELECT 
        COUNT(*) as total_records,
        COUNT(DISTINCT patient_mrn) as unique_patients,
        ROUND(COUNT(*) / (SELECT total_records FROM bronze_check) * 100, 2) as pass_rate_pct
    FROM silver.encounters
),
gold_check AS (
    SELECT 
        COUNT(*) as total_records,
        COUNT(DISTINCT patient_mrn) as unique_patients,
        ROUND(AVG(readmission_rate_30d), 2) as avg_readmission_rate
    FROM gold.readmission_metrics
)
SELECT 
    'PIPELINE_HEALTH_SUMMARY' AS metric,
    b.total_records as bronze_records,
    b.unique_patients as bronze_patients,
    s.total_records as silver_records,
    s.unique_patients as silver_patients,
    s.pass_rate_pct as silver_pass_rate_pct,
    g.total_records as gold_records,
    g.avg_readmission_rate as gold_readmission_rate_pct
FROM bronze_check b
CROSS JOIN silver_check s
CROSS JOIN gold_check g;
