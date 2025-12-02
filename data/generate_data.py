import csv
import random
from datetime import datetime, timedelta
import os

# Configuration
random.seed(42)  # For reproducibility

# Hospitals
HOSPITALS = ["UnityPoint Des Moines", "UnityPoint Cedar Rapids", "UnityPoint Waterloo", "UnityPoint Council Bluffs", "UnityPoint Sioux City"]

# Diagnoses (realistic ICD-10 codes)
DIAGNOSES = [
    "Pneumonia", "Sepsis", "Acute kidney injury", "Congestive heart failure",
    "COPD exacerbation", "Stroke", "Myocardial infarction", "Dehydration",
    "Urinary tract infection", "Acute coronary syndrome", "Hypertensive urgency",
    "Diabetic ketoacidosis", "Cellulitis", "Pneumonia (aspiration)", "Fall with fracture"
]

# Generate encounters data with some intentional bad records
def generate_encounters(num_records=500):
    """Generate synthetic patient encounter data with ~10% bad records"""
    encounters = []
    base_date = datetime(2023, 1, 1)
    
    for i in range(num_records):
        patient_mrn = f"MRN{str(random.randint(1000, 5000)).zfill(5)}"
        encounter_id = f"ENC{str(i+1).zfill(6)}"
        
        # Generate date range
        days_offset = random.randint(0, 365)
        admission_date = base_date + timedelta(days=days_offset)
        
        # ~90% good records: discharge > admission
        # ~10% bad records: discharge < admission (data quality issue)
        if random.random() < 0.9:
            los = random.randint(1, 14)
            discharge_date = admission_date + timedelta(days=los)
        else:
            # Bad record: discharge before admission
            discharge_date = admission_date - timedelta(days=random.randint(1, 5))
        
        hospital = random.choice(HOSPITALS)
        diagnosis = random.choice(DIAGNOSES)
        provider = f"Dr. {random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones'])}"
        
        # ~5% records have missing required fields
        if random.random() < 0.05:
            patient_mrn = None if random.random() < 0.5 else patient_mrn
            diagnosis = None if random.random() < 0.3 else diagnosis
        
        encounters.append({
            'patient_mrn': patient_mrn,
            'encounter_id': encounter_id,
            'admission_date': admission_date.strftime('%Y-%m-%d'),
            'discharge_date': discharge_date.strftime('%Y-%m-%d'),
            'diagnosis': diagnosis,
            'hospital': hospital,
            'primary_provider': provider
        })
    
    return encounters

# Generate lab results data
def generate_labs(num_records=500):
    """Generate synthetic lab result data"""
    labs = []
    lab_tests = ["WBC", "RBC", "Hemoglobin", "Platelets", "Creatinine", "BUN", "Glucose", "Sodium", "Potassium"]
    reference_ranges = {
        "WBC": "4.5-11.0",
        "RBC": "4.5-5.9",
        "Hemoglobin": "13.5-17.5",
        "Platelets": "150-400",
        "Creatinine": "0.7-1.3",
        "BUN": "7-20",
        "Glucose": "70-100",
        "Sodium": "136-145",
        "Potassium": "3.5-5.0"
    }
    
    base_date = datetime(2023, 1, 1)
    
    for i in range(num_records):
        encounter_id = f"ENC{str(random.randint(1, 500)).zfill(6)}"
        lab_id = f"LAB{str(i+1).zfill(6)}"
        
        days_offset = random.randint(0, 365)
        test_date = base_date + timedelta(days=days_offset)
        
        test_name = random.choice(lab_tests)
        result_value = round(random.uniform(1, 20), 2)
        
        labs.append({
            'lab_id': lab_id,
            'encounter_id': encounter_id,
            'test_name': test_name,
            'result_value': result_value,
            'reference_range': reference_ranges[test_name],
            'test_date': test_date.strftime('%Y-%m-%d')
        })
    
    return labs

# Generate readmissions reference data
def generate_readmissions(num_records=500):
    """Generate synthetic readmission flag data"""
    readmissions = []
    
    for i in range(num_records):
        encounter_id = f"ENC{str(i+1).zfill(6)}"
        readmitted_30d = random.randint(0, 1) if random.random() < 0.25 else 0  # ~25% readmission rate
        
        readmissions.append({
            'encounter_id': encounter_id,
            'readmitted_30d': readmitted_30d
        })
    
    return readmissions

# Write CSV files
def write_csv_files(output_dir):
    """Generate and write all sample data files"""
    
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate encounters
    print("Generating encounters data...")
    encounters = generate_encounters(500)
    with open(os.path.join(output_dir, 'encounters.csv'), 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['patient_mrn', 'encounter_id', 'admission_date', 'discharge_date', 'diagnosis', 'hospital', 'primary_provider'])
        writer.writeheader()
        writer.writerows(encounters)
    print(f"  ✅ Created encounters.csv with {len(encounters)} records")
    
    # Generate labs
    print("Generating lab results data...")
    labs = generate_labs(500)
    with open(os.path.join(output_dir, 'labs.csv'), 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['lab_id', 'encounter_id', 'test_name', 'result_value', 'reference_range', 'test_date'])
        writer.writeheader()
        writer.writerows(labs)
    print(f"  ✅ Created labs.csv with {len(labs)} records")
    
    # Generate readmissions
    print("Generating readmissions data...")
    readmissions = generate_readmissions(500)
    with open(os.path.join(output_dir, 'readmissions.csv'), 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['encounter_id', 'readmitted_30d'])
        writer.writeheader()
        writer.writerows(readmissions)
    print(f"  ✅ Created readmissions.csv with {len(readmissions)} records")
    
    print("\n✅ All sample data files generated successfully!")
    print(f"\nData Summary:")
    print(f"  - {len(encounters)} patient encounters (~10% with data quality issues)")
    print(f"  - {len(labs)} lab results")
    print(f"  - {len(readmissions)} readmission flags (~25% readmission rate)")

if __name__ == "__main__":
    output_dir = os.path.dirname(os.path.abspath(__file__))
    write_csv_files(output_dir)
