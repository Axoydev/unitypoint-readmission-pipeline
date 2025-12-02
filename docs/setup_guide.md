# Setup Guide - UnityPoint Readmission Pipeline

## Quick Start (5 Minutes)

### Prerequisites
- Databricks account (Community Edition is free)
- PySpark 3.0+
- Python 3.8+
- Git

### Step 1: Clone Repository
```bash
git clone https://github.com/yourusername/unitypoint-readmission-pipeline.git
cd unitypoint-readmission-pipeline
```

### Step 2: Set Up Databricks Cluster

1. Log in to Databricks: https://databricks.com/product/faq/community-edition
2. Create a new cluster with these settings:
   - **Name**: readmission-cluster
   - **Spark Version**: 13.3.x-scala2.12
   - **Node Type**: Single node (4GB+ memory)
   - **Python**: 3.9+
   - **Timeout**: 120 minutes

### Step 3: Upload Sample Data

1. In Databricks, go to **Data** → **Create Table**
2. Upload CSV files from `data/` folder:
   - `encounters.csv`
   - `labs.csv`
   - `readmissions.csv`
3. Create external location for data storage

### Step 4: Import Notebooks

**Option A: Using Databricks UI**
1. Go to **Workspace** in Databricks
2. Click **Import** → **File**
3. Select each `.py` file from `notebooks/` folder
4. Files will be imported with `.scala` extension (OK for this project)

**Option B: Using Databricks CLI**
```bash
# Install CLI
pip install databricks-cli

# Configure credentials
databricks configure --token

# Import notebooks
databricks workspace import-dir notebooks/ /Users/your_email/readmission-pipeline
```

### Step 5: Update Configuration

1. Edit `config/pipeline_config.yaml`:
   ```yaml
   sources:
     gcs_bucket: "YOUR_GCS_BUCKET_PATH"
   
   resources:
     cluster:
       name: "readmission-cluster"  # Match your cluster name
   ```

2. Update file paths in notebooks if using local data:
   ```python
   BRONZE_PATH = "/dbfs/data/bronze/encounters"  # Or your DBFS path
   ```

### Step 6: Run Notebooks in Order

1. **Bronze Layer** (2 min)
   - Open `01_bronze_ingestion.py`
   - Click **Run All**
   - Monitor execution

2. **Silver Layer** (3 min)
   - Open `02_silver_transformation.py`
   - Click **Run All**
   - Check data quality metrics

3. **Gold Layer** (2 min)
   - Open `03_gold_aggregation.py`
   - Click **Run All**
   - Verify readmission metrics

4. **Optimization** (5 min)
   - Open `04_optimization.py`
   - Click **Run All**
   - Review performance improvements

---

## Local Development (Without Databricks)

### Prerequisites
```bash
# Install PySpark
pip install pyspark pandas

# Or install from requirements.txt
pip install -r requirements.txt
```

### Running Notebooks Locally

```bash
# Set up Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run Bronze layer
python notebooks/01_bronze_ingestion.py

# Run Silver layer
python notebooks/02_silver_transformation.py

# Run Gold layer
python notebooks/03_gold_aggregation.py
```

**Note**: Delta Lake MERGE and Unity Catalog features only work on Databricks.

---

## Data Validation

### Check Data Quality
```sql
-- Run in Databricks SQL
SELECT COUNT(*) as total_records FROM silver.encounters;
SELECT COUNT(DISTINCT patient_mrn) as unique_patients FROM gold.readmission_metrics;
```

### View Sample Data
```sql
SELECT * FROM silver.encounters LIMIT 10;
SELECT * FROM gold.readmission_metrics LIMIT 5;
```

### Run Quality Checks
```bash
# All queries in: sql/data_quality_checks.sql
# Run manually or schedule as a SQL alert
```

---

## Troubleshooting

### Issue: "Table not found" error
**Solution**: Ensure notebooks ran in order (Bronze → Silver → Gold)

### Issue: "Permission denied" on GCS bucket
**Solution**: 
- Check service account credentials
- Verify bucket name in `pipeline_config.yaml`
- Test connection: `dbutils.fs.ls("gs://bucket-name")`

### Issue: "Duplicate encounter_id" warnings
**Solution**: Expected behavior - demonstrates MERGE idempotency. This is a feature, not a bug.

### Issue: Slow query performance
**Solution**: Run `04_optimization.py` to enable Z-ordering and compaction

### Issue: Out of memory
**Solution**: 
- Increase cluster size (go to Cluster → Edit → Max Workers)
- Or reduce dataset size in `generate_data.py`

---

## Customization

### Modify Sample Data
Edit `data/generate_data.py`:
```python
# Change number of records
encounters = generate_encounters(num_records=1000)  # Default: 500

# Add new diagnoses
DIAGNOSES = [
    "Pneumonia",
    "Custom Diagnosis",  # Add here
]
```

Then regenerate:
```bash
python data/generate_data.py
```

### Add New Validation Rule
Edit `notebooks/02_silver_transformation.py`:
```python
def validate_custom_rule(df):
    """Your custom validation"""
    df_valid = df.filter(col("your_column") > 0)
    df_invalid = df.filter(col("your_column") <= 0)
    return df_valid, df_invalid
```

### Schedule Jobs
In Databricks:
1. **Workflows** → **Create Job**
2. Select notebook and cluster
3. Set schedule: `0 2 * * *` (2 AM daily)
4. Add alert if job fails

---

## Performance Tuning

### Optimize for your cluster size:

**For single-node cluster (2-4GB)**:
- Reduce sample data to 100 records
- Disable Z-ordering
- Skip optimization step

**For 2-4 node cluster (8GB+)**:
- Use default 500 records
- Enable Z-ordering
- Run optimization daily

**For 5+ node cluster (16GB+)**:
- Increase sample data to 1000+ records
- Enable all optimizations
- Run dashboards in real-time

---

## Production Deployment

### Before going live:

- [ ] Test with production data volume
- [ ] Configure monitoring alerts
- [ ] Set up automated backups
- [ ] Enable audit logging
- [ ] Schedule daily jobs
- [ ] Document operational runbooks
- [ ] Train clinical users
- [ ] Set up dashboard access controls

### Typical production setup:
```yaml
schedule: "0 2 * * *"        # 2 AM UTC daily
timeout_minutes: 60          # Abort if > 60 min
max_concurrent_runs: 1       # No overlapping runs
notifications: "email"       # Alert on failure
retention_days: 90           # Archive after 90 days
```

---

## Support & Documentation

- **Databricks Docs**: https://docs.databricks.com/
- **PySpark Guide**: https://spark.apache.org/docs/latest/api/python/
- **Delta Lake**: https://docs.delta.io/
- **SQL Reference**: https://spark.apache.org/docs/latest/sql-ref.html

---

## Next Steps

1. **Add more data sources**: Labs, medications, diagnosis codes
2. **Implement ML model**: Predictive readmission scoring
3. **Create dashboards**: Tableau or Looker integration
4. **Set up alerts**: Real-time notifications for high-risk patients
5. **Expand to other hospitals**: Scale to multi-hospital network

---

## Questions?

Open an issue on GitHub or contact the Data Engineering team.

**Happy analyzing! 🚀**
