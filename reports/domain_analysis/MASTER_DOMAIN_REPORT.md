# MASTER DOMAIN ANALYSIS REPORT

## Australian Legal Corpus - Complete Classification

**Generated**: 2025-11-25 11:38:55

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Documents** | 18,076 |
| **Legal Domains** | 14 |
| **Corpus Size** | ~8.8 GB |

This report provides cross-domain analysis of the Australian Legal Corpus,
identifying patterns, overlaps, and recommendations for GSW processing.

---

## 1. Domain Distribution

| Domain | Documents | % of Corpus | Primary Type | Date Range |
|--------|-----------|-------------|--------------|------------|
| Administrative | 9,368 | 51.8% | decision | 1951-12-06 - 2024-09-11 |
| Legislation_Other | 7,097 | 39.3% | secondary_legislation | 1830-01-18 - 2024-09-13 |
| Commercial | 315 | 1.7% | decision | 1981-11-13 - 2024-08-09 |
| Criminal | 277 | 1.5% | decision | 1982-08-13 - 2024-09-13 |
| Property | 229 | 1.3% | decision | 1922-06-23 - 2024-08-20 |
| Industrial | 187 | 1.0% | decision | 1967-12-19 - 2024-09-01 |
| Tax | 168 | 0.9% | decision | 1979-06-12 - 2024-09-06 |
| Procedural | 157 | 0.9% | decision | 1979-07-04 - 2024-09-13 |
| Torts | 134 | 0.7% | decision | 1995-08-03 - 2024-07-01 |
| Family | 54 | 0.3% | decision | 1997-07-17 - 2024-07-30 |
| Equity | 50 | 0.3% | decision | 1967-09-11 - 2024-06-05 |
| Specialized | 26 | 0.1% | primary_legislation | 1994-12-12 - 2024-09-01 |
| Constitutional | 14 | 0.1% | decision | 2008-10-02 - 2024-08-21 |
| Unclassified | 0 | 0.0% | N/A | N/A - N/A |

### Domain Size Visualization

```
Administrative       ████████████████████████████████████████ 9,368
Legislation_Other    ██████████████████████████████ 7,097
Commercial           █ 315
Criminal             █ 277
Property              229
Industrial            187
Tax                   168
Procedural            157
Torts                 134
Family                54
```

---

## 2. Classification Quality Analysis

*Note: Run domain extraction to generate overlap statistics.*


---

## 3. GSW Processing Priority Ranking

Based on: existing infrastructure, legal importance, volume, and data quality.

| Rank | Domain | Priority Score | Rationale |
|------|--------|----------------|-----------|
| 1 | Criminal | 16 | Existing ontology, High legal importance, Small volume - quick to process, Good temporal coverage |
| 2 | Family | 16 | Existing ontology, High legal importance, Small volume - quick to process, Good temporal coverage |
| 3 | Administrative | 7 | Manageable volume, High court decisions, Good temporal coverage |
| 4 | Constitutional | 7 | High legal importance, Small volume - quick to process, Good temporal coverage |
| 5 | Legislation_Other | 5 | Manageable volume, Good temporal coverage |
| 6 | Commercial | 3 | Small volume - quick to process, Good temporal coverage |
| 7 | Equity | 3 | Small volume - quick to process, Good temporal coverage |
| 8 | Industrial | 3 | Small volume - quick to process, Good temporal coverage |
| 9 | Procedural | 3 | Small volume - quick to process, Good temporal coverage |
| 10 | Property | 3 | Small volume - quick to process, Good temporal coverage |
| 11 | Specialized | 3 | Small volume - quick to process, Good temporal coverage |
| 12 | Tax | 3 | Small volume - quick to process, Good temporal coverage |
| 13 | Torts | 3 | Small volume - quick to process, Good temporal coverage |
| 14 | Unclassified | 2 | Small volume - quick to process |

---

## 4. Processing Recommendations

### Phase 1: Priority Domains (Immediate)

Focus on domains with existing infrastructure and high legal value:

1. **Family Law**
   - Existing ontology and schema
   - High social importance
   - Well-defined entity types (parties, children, assets)
   - Run full GSW pipeline with Reflexion

2. **Criminal Law**
   - Large volume but well-structured
   - Clear actor types (accused, victim, judge)
   - Track sentencing outcomes
   - Consider sub-domain splitting (Violence, Drugs, etc.)

### Phase 2: High-Volume Domains

3. **Administrative Law**
   - Largest domain - requires batch processing
   - Split into sub-domains (Migration, Social Security, etc.)
   - Migration cases have distinct patterns

4. **Tax Law**
   - Technical but structured
   - Track ATO rulings and tribunal decisions

### Phase 3: Specialized Domains

5. **Commercial/Property/Torts**
   - Moderate complexity
   - Focus on contract and negligence patterns

6. **Other Domains**
   - Constitutional, Procedural, Specialized
   - Lower priority due to volume or specificity

### Technical Recommendations

**Batch Size Recommendations**:
- Small domains (<5,000 docs): Process in single batch
- Medium domains (5,000-50,000): Batch size of 100-500
- Large domains (>50,000): Batch size of 50-100 with checkpoints

**API Cost Estimation**:
- Estimated total tokens: ~36,152,000
- Estimated API cost: ~$36.15 (at $1/1M tokens)

---

## 5. Next Steps

1. [ ] Run domain extraction on full corpus
2. [ ] Review per-domain reports for anomalies
3. [ ] Configure domain-specific ontology seeds
4. [ ] Begin Phase 1 GSW processing (Family, Criminal)
5. [ ] Establish evaluation benchmarks
6. [ ] Monitor extraction quality metrics

---

*Generated by Legal GSW Domain Analysis System*
