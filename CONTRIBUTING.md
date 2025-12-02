# Contributing to UnityPoint Readmission Pipeline

Thank you for your interest in contributing! This guide explains how to work on this project.

## Code of Conduct

- Be respectful and professional
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/unitypoint-readmission-pipeline.git
   cd unitypoint-readmission-pipeline
   ```
3. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Before making changes:
```bash
# Test the existing pipeline
python data/generate_data.py
python notebooks/01_bronze_ingestion.py
```

### Make your changes:
- Edit notebook files in `notebooks/` folder
- Update SQL queries in `sql/` folder
- Modify configuration in `config/` folder

### Test your changes:
```bash
# Validate Python syntax
python -m py_compile notebooks/your_notebook.py

# Run updated notebook
python notebooks/your_notebook.py
```

## Code Standards

### Python Style
- Follow PEP 8 conventions
- Use type hints where possible
- Write docstrings for functions
- Keep lines under 100 characters

**Good Example**:
```python
def validate_data(df) -> tuple:
    """
    Validates data quality and separates clean/invalid records.
    
    Args:
        df: PySpark DataFrame with encounter data
        
    Returns:
        Tuple of (valid_df, invalid_df)
    """
    df_valid = df.filter(col("discharge_date") >= col("admission_date"))
    df_invalid = df.filter(col("discharge_date") < col("admission_date"))
    return df_valid, df_invalid
```

### SQL Style
- Use uppercase for keywords (SELECT, FROM, WHERE)
- Use descriptive aliases
- Add comments for complex logic
- Include expected row counts

**Good Example**:
```sql
-- Count patients with 30-day readmissions
SELECT 
    patient_mrn,
    COUNT(*) as readmission_count
FROM encounters
WHERE days_to_next_admission <= 30
GROUP BY patient_mrn
ORDER BY readmission_count DESC;
```

## Contribution Areas

### High Priority
- [ ] Add more data validation rules
- [ ] Implement SCD Type 2 for more dimensions
- [ ] Add performance benchmarks
- [ ] Create monitoring dashboard

### Medium Priority
- [ ] Add support for additional data sources
- [ ] Improve error handling and logging
- [ ] Write integration tests
- [ ] Create deployment guide

### Low Priority
- [ ] Documentation improvements
- [ ] Code refactoring
- [ ] Example notebooks
- [ ] Tutorial videos

## Submitting Changes

### Before submitting a PR:

1. **Update documentation**:
   ```bash
   # If you added a new feature, update README.md
   # If you changed configuration, update config/pipeline_config.yaml
   ```

2. **Test thoroughly**:
   - Run all notebooks in sequence
   - Check data quality metrics
   - Verify performance metrics

3. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

   Use commit message format:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `refactor:` for code cleanup
   - `perf:` for performance improvements

4. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request**:
   - Go to GitHub
   - Click "Compare & Pull Request"
   - Fill out PR template
   - Request reviewers

### PR Checklist
- [ ] Code follows style guidelines
- [ ] All notebooks run without errors
- [ ] Data quality metrics are acceptable (>96% pass rate)
- [ ] Documentation is updated
- [ ] No hardcoded paths or credentials
- [ ] Commit messages are descriptive

## Review Process

1. **Automated checks**:
   - Python syntax validation
   - File size limits
   - Credential scanning

2. **Manual review**:
   - Code quality assessment
   - Business logic validation
   - Performance impact analysis

3. **Approval**:
   - Requires 2 approvals from maintainers
   - All checks must pass
   - No conflicts with main branch

## Common Issues & Solutions

### Issue: "My notebook won't run"
- Check file paths are correct
- Verify sample data exists
- Ensure PySpark is installed

### Issue: "Data quality metrics are low"
- Review quarantine records
- Check validation rules
- Consider data source issues

### Issue: "Permission denied" error
- Verify file permissions
- Check cluster access
- Review credential configuration

## Performance Considerations

When adding new features, consider:
- **Query performance**: Will additional transformations slow down the pipeline?
- **Data volume**: Can the cluster handle the data volume?
- **Storage**: Are we adding unnecessary columns?
- **Latency**: Can we meet the 90-minute SLA?

Test with both sample data (500 rows) and larger datasets (1000+ rows).

## Documentation

### When to update docs:
- Adding a new feature
- Changing pipeline behavior
- Fixing a known issue
- Improving clarity

### Documentation files to update:
- `README.md` - Project overview
- `docs/setup_guide.md` - Setup instructions
- `config/pipeline_config.yaml` - Configuration options
- Notebook comments - Implementation details

## Questions?

- **Create an issue** for bugs and feature requests
- **Start a discussion** for questions
- **Check existing issues** before asking

## Recognition

Contributors will be recognized in:
- README.md contributors section
- GitHub commit history
- Release notes

---

## Project Roadmap

### Q1 2025
- [ ] Add ML-based risk scoring
- [ ] Implement multi-hospital rollup
- [ ] Create Tableau dashboards

### Q2 2025
- [ ] Add real-time streaming
- [ ] Integrate pharmacy data
- [ ] Implement cost analysis

### Q3 2025
- [ ] Scale to enterprise
- [ ] Add predictive modeling
- [ ] Implement automated interventions

---

**Thank you for contributing to UnityPoint's mission of improving patient outcomes!** 🏥

Last Updated: December 2024
