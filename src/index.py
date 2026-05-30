#!/usr/bin/env python3
"""
clinical-note-parser — unstructured clinical notes → FHIR-compatible structured data
Extracts: diagnoses (ICD-10), medications (RxNorm), vitals, allergies, procedures, lab results
HIPAA-safe: never stores or logs patient data
"""
import anthropic
import json
import re
import sys
from pathlib import Path


SYSTEM = """You are a clinical informatics specialist and medical NLP expert.
Parse unstructured clinical notes into structured, FHIR-compatible JSON.

IMPORTANT: Extract only what is explicitly stated. Do NOT infer or assume.
Map conditions to ICD-10 codes and medications to RxNorm where confident.

Return ONLY valid JSON — no markdown, no explanation.

Format:
{
  "note_type": "progress_note|discharge_summary|admission|consultation|lab_report|radiology|other",
  "note_date": "YYYY-MM-DD or null",
  "patient_demographics": {
    "age": number or null,
    "gender": "male|female|other|null",
    "note": "never include name, DOB, MRN, SSN, or any PII"
  },
  "chief_complaint": "string or null",
  "diagnoses": [
    {
      "description": "string",
      "icd10_code": "string or null",
      "icd10_display": "string or null",
      "status": "active|resolved|chronic|suspected|ruled_out",
      "onset_date": "YYYY-MM-DD or null",
      "severity": "mild|moderate|severe|null"
    }
  ],
  "medications": [
    {
      "name": "string",
      "generic_name": "string or null",
      "rxnorm_code": "string or null",
      "dose": "string or null",
      "frequency": "string or null",
      "route": "oral|IV|IM|topical|inhaled|null",
      "status": "active|discontinued|as_needed",
      "indication": "string or null"
    }
  ],
  "allergies": [
    {
      "substance": "string",
      "reaction": "string or null",
      "severity": "mild|moderate|severe|life_threatening|null",
      "type": "drug|food|environmental|other"
    }
  ],
  "vitals": {
    "blood_pressure_systolic": number or null,
    "blood_pressure_diastolic": number or null,
    "heart_rate": number or null,
    "temperature_celsius": number or null,
    "respiratory_rate": number or null,
    "oxygen_saturation": number or null,
    "weight_kg": number or null,
    "height_cm": number or null,
    "bmi": number or null
  },
  "lab_results": [
    {
      "test_name": "string",
      "loinc_code": "string or null",
      "value": "string",
      "unit": "string or null",
      "reference_range": "string or null",
      "flag": "normal|high|low|critical|null",
      "date": "YYYY-MM-DD or null"
    }
  ],
  "procedures": [
    {
      "description": "string",
      "cpt_code": "string or null",
      "date": "YYYY-MM-DD or null",
      "status": "completed|planned|cancelled"
    }
  ],
  "assessment_plan": "string or null",
  "follow_up": "string or null",
  "referring_specialty": "string or null",
  "extraction_confidence": 0.0,
  "warnings": ["list of ambiguities or low-confidence extractions"]
}"""


def parse_note(text: str) -> dict:
    """Parse a clinical note from plain text."""
    client = anthropic.Anthropic()

    # Truncate if very long
    if len(text) > 50000:
        text = text[:50000] + "\n[note truncated]"

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"Parse this clinical note:\n\n{text}"}]
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)
    return json.loads(raw)


def parse_file(file_path: str) -> dict:
    """Parse clinical note from a text file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Not found: {file_path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_note(text)


def print_summary(result: dict):
    print(f"\n{'─'*55}")
    print(f"  Clinical Note Parsed — {result.get('note_type','unknown').upper()}")
    print(f"{'─'*55}")
    cc = result.get("chief_complaint")
    if cc:
        print(f"  Chief complaint: {cc}")

    dx = result.get("diagnoses", [])
    if dx:
        print(f"\n  Diagnoses ({len(dx)}):")
        for d in dx:
            code = f" [{d.get('icd10_code','')}]" if d.get('icd10_code') else ""
            print(f"    • {d.get('description','?')}{code} — {d.get('status','?')}")

    meds = result.get("medications", [])
    if meds:
        print(f"\n  Medications ({len(meds)}):")
        for m in meds:
            dose = f" {m.get('dose','')}" if m.get('dose') else ""
            freq = f" {m.get('frequency','')}" if m.get('frequency') else ""
            print(f"    • {m.get('name','?')}{dose}{freq}")

    vitals = {k: v for k, v in result.get("vitals", {}).items() if v is not None}
    if vitals:
        print(f"\n  Vitals:")
        if result["vitals"].get("blood_pressure_systolic"):
            print(f"    BP: {result['vitals']['blood_pressure_systolic']}/{result['vitals'].get('blood_pressure_diastolic','?')}")
        if result["vitals"].get("heart_rate"):
            print(f"    HR: {result['vitals']['heart_rate']} bpm")
        if result["vitals"].get("temperature_celsius"):
            print(f"    Temp: {result['vitals']['temperature_celsius']}°C")
        if result["vitals"].get("oxygen_saturation"):
            print(f"    SpO2: {result['vitals']['oxygen_saturation']}%")

    allergies = result.get("allergies", [])
    if allergies:
        print(f"\n  Allergies: {', '.join(a.get('substance','?') for a in allergies)}")

    labs = result.get("lab_results", [])
    if labs:
        print(f"\n  Lab results ({len(labs)}):")
        for lab in labs[:5]:
            flag = f" ⚠ {lab.get('flag','').upper()}" if lab.get('flag') and lab.get('flag') != 'normal' else ""
            print(f"    • {lab.get('test_name','?')}: {lab.get('value','?')} {lab.get('unit','')}{flag}")

    warnings = result.get("warnings", [])
    if warnings:
        print(f"\n  Warnings:")
        for w in warnings:
            print(f"    ⚠ {w}")

    print(f"\n  Confidence: {int(result.get('extraction_confidence', 0) * 100)}%")
    print(f"{'─'*55}\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: python -m clinical_note_parser <note.txt> [--json]")
        print("       echo 'Patient presents with...' | python -m clinical_note_parser -")
        sys.exit(0)

    if args[0] == "-":
        text = sys.stdin.read()
        result = parse_note(text)
    else:
        result = parse_file(args[0])

    if "--json" in args:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_summary(result)
