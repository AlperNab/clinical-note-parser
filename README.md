# clinical-note-parser

> **Unstructured clinical notes → FHIR-compatible structured data.** Extracts diagnoses (ICD-10), medications (RxNorm), vitals, allergies, procedures, lab results. HIPAA-safe — never stores patient data.

[![PyPI](https://img.shields.io/pypi/v/clinical-note-parser?style=flat)](https://pypi.org/project/clinical-note-parser/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

⚠️ **Clinical use disclaimer:** This tool is for informational and workflow automation purposes only. Never use as a substitute for clinical judgment. Always verify extracted data with source documents.

## Quickstart

```bash
pip install clinical-note-parser
python -m clinical_note_parser note.txt
echo "Patient presents with HTN, DM2, on Metformin 1000mg BID" | python -m clinical_note_parser -
```

## What it extracts

- **Diagnoses** with ICD-10 codes and status (active / resolved / chronic)
- **Medications** with dose, frequency, route, RxNorm codes
- **Vitals** — BP, HR, temp, SpO2, weight, height, BMI
- **Allergies** with reaction and severity
- **Lab results** with LOINC codes and flags
- **Procedures** with CPT codes

## License
MIT © [Alper Nabil Gabra Zakher](https://github.com/AlperNab)
