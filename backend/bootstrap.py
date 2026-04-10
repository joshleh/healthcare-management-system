from __future__ import annotations

import csv
import hashlib
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


FACILITIES = [
    {
        "id": 1,
        "name": "St. Catherine Medical Center",
        "type": "Flagship Hospital",
        "city": "San Francisco",
        "state": "CA",
        "region": "West",
        "beds": 412,
    },
    {
        "id": 2,
        "name": "Harborview Women's Pavilion",
        "type": "Women's & Family Care",
        "city": "Oakland",
        "state": "CA",
        "region": "West",
        "beds": 186,
    },
    {
        "id": 3,
        "name": "Riverside Cancer Institute",
        "type": "Oncology Center",
        "city": "San Jose",
        "state": "CA",
        "region": "West",
        "beds": 144,
    },
    {
        "id": 4,
        "name": "Westbrook Specialty Clinic",
        "type": "Ambulatory Specialty Clinic",
        "city": "Berkeley",
        "state": "CA",
        "region": "West",
        "beds": 62,
    },
    {
        "id": 5,
        "name": "Northgate Community Hospital",
        "type": "Community Hospital",
        "city": "Walnut Creek",
        "state": "CA",
        "region": "West",
        "beds": 228,
    },
    {
        "id": 6,
        "name": "Summit Diagnostic Center",
        "type": "Diagnostics & Imaging",
        "city": "Palo Alto",
        "state": "CA",
        "region": "West",
        "beds": 40,
    },
]


INSURANCE_PLANS = [
    {"id": 1, "payer": "NorthStar Commercial", "plan": "Premier PPO", "type": "Commercial", "coverage": 0.82},
    {"id": 2, "payer": "Blue Horizon Health", "plan": "Choice HMO", "type": "Commercial", "coverage": 0.78},
    {"id": 3, "payer": "Federal Care Select", "plan": "Standard Advantage", "type": "Government", "coverage": 0.88},
    {"id": 4, "payer": "Everwell Senior", "plan": "Gold Medicare", "type": "Government", "coverage": 0.91},
    {"id": 5, "payer": "ValleyCare Plus", "plan": "Employer EPO", "type": "Commercial", "coverage": 0.75},
]


MEDICATIONS = [
    {"id": 1, "name": "Atorvastatin", "category": "Cardiovascular", "form": "Tablet", "unit_cost": 48},
    {"id": 2, "name": "Metoprolol", "category": "Cardiovascular", "form": "Tablet", "unit_cost": 28},
    {"id": 3, "name": "Lisinopril", "category": "Cardiovascular", "form": "Tablet", "unit_cost": 24},
    {"id": 4, "name": "Ondansetron", "category": "Oncology Support", "form": "Tablet", "unit_cost": 62},
    {"id": 5, "name": "Prednisone", "category": "Inflammation", "form": "Tablet", "unit_cost": 18},
    {"id": 6, "name": "Amoxicillin", "category": "Anti-Infective", "form": "Capsule", "unit_cost": 16},
    {"id": 7, "name": "Albuterol", "category": "Respiratory", "form": "Inhaler", "unit_cost": 54},
    {"id": 8, "name": "Gabapentin", "category": "Neurology", "form": "Capsule", "unit_cost": 34},
    {"id": 9, "name": "Insulin Aspart", "category": "Endocrinology", "form": "Injection", "unit_cost": 76},
    {"id": 10, "name": "Levothyroxine", "category": "Endocrinology", "form": "Tablet", "unit_cost": 22},
    {"id": 11, "name": "Sertraline", "category": "Behavioral Health", "form": "Tablet", "unit_cost": 26},
    {"id": 12, "name": "Acetaminophen", "category": "Post-Procedure", "form": "Tablet", "unit_cost": 12},
]


PATIENT_LOCATIONS = [
    ("San Francisco", "CA"),
    ("Oakland", "CA"),
    ("San Jose", "CA"),
    ("Berkeley", "CA"),
    ("Palo Alto", "CA"),
    ("Walnut Creek", "CA"),
    ("Daly City", "CA"),
    ("Fremont", "CA"),
]


LAB_TESTS = {
    "cardiology": [
        {"name": "Troponin I", "category": "Cardiac", "unit": "ng/mL", "low": 0.0, "high": 0.04},
        {"name": "BNP", "category": "Cardiac", "unit": "pg/mL", "low": 0.0, "high": 100.0},
    ],
    "oncology": [
        {"name": "CBC with Differential", "category": "Hematology", "unit": "x10^3/uL", "low": 4.0, "high": 11.0},
        {"name": "Comprehensive Metabolic Panel", "category": "Chemistry", "unit": "mg/dL", "low": 65.0, "high": 105.0},
    ],
    "respiratory": [
        {"name": "Arterial Blood Gas", "category": "Respiratory", "unit": "mmHg", "low": 80.0, "high": 100.0},
        {"name": "Respiratory Viral Panel", "category": "Infectious Disease", "unit": "index", "low": 0.0, "high": 1.0},
    ],
    "renal": [
        {"name": "Creatinine", "category": "Renal", "unit": "mg/dL", "low": 0.6, "high": 1.3},
        {"name": "Electrolyte Panel", "category": "Chemistry", "unit": "mmol/L", "low": 135.0, "high": 145.0},
    ],
    "women": [
        {"name": "Hemoglobin", "category": "Hematology", "unit": "g/dL", "low": 12.0, "high": 15.5},
        {"name": "Thyroid Stimulating Hormone", "category": "Endocrinology", "unit": "uIU/mL", "low": 0.4, "high": 4.0},
    ],
    "default": [
        {"name": "Basic Metabolic Panel", "category": "Chemistry", "unit": "mg/dL", "low": 70.0, "high": 110.0},
        {"name": "C-Reactive Protein", "category": "Inflammation", "unit": "mg/L", "low": 0.0, "high": 5.0},
    ],
}


@dataclass
class AppointmentMeta:
    appointment_id: int
    patient_id: int
    doctor_id: int
    facility_id: int
    appointment_date: str
    appointment_time: str
    status: str
    visit_type: str


def build_demo_database(db_path: Path, data_dir: Path, reference_date: date) -> None:
    db_path.parent.mkdir(exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript((ROOT / "schema.sql").read_text())

        patient_rows = read_csv(data_dir / "Patient.csv")
        doctor_rows = read_csv(data_dir / "Doctor.csv")
        appointment_rows = read_csv(data_dir / "Appointment.csv")
        procedure_rows = read_csv(data_dir / "Medical Procedure.csv")
        billing_rows = read_csv(data_dir / "Billing.csv")
        required_patient_ids = {
            int(row["PatientID"])
            for row in appointment_rows + billing_rows
            if row.get("PatientID")
        }
        required_doctor_ids = {
            int(row["DoctorID"])
            for row in appointment_rows
            if row.get("DoctorID")
        }

        seed_static_tables(connection)
        coverage_by_patient = seed_patients_and_coverage(connection, patient_rows, required_patient_ids)
        doctor_facilities, specialties = seed_doctors(connection, doctor_rows, required_doctor_ids)
        appointments_by_id, appointments_by_patient, next_appointment_id = seed_appointments(
            connection,
            appointment_rows,
            set(coverage_by_patient),
            doctor_facilities,
            specialties,
            reference_date,
        )
        next_appointment_id = seed_future_appointments(
            connection,
            next_appointment_id,
            appointments_by_id,
            appointments_by_patient,
            doctor_facilities,
            specialties,
            list(sorted(coverage_by_patient)),
            reference_date,
        )
        procedures_by_appointment, next_procedure_id = seed_procedures(
            connection,
            procedure_rows,
            appointments_by_id,
        )
        prescriptions_by_appointment = seed_prescriptions(connection, appointments_by_id, specialties, reference_date)
        labs_by_appointment = seed_lab_results(connection, appointments_by_id, specialties, reference_date)
        seed_invoices(
            connection,
            billing_rows,
            appointments_by_id,
            appointments_by_patient,
            procedures_by_appointment,
            prescriptions_by_appointment,
            labs_by_appointment,
            coverage_by_patient,
            doctor_facilities,
            specialties,
            next_appointment_id,
            next_procedure_id,
            reference_date,
        )
        connection.commit()
    finally:
        connection.close()


def seed_static_tables(connection: sqlite3.Connection) -> None:
    connection.executemany(
        """
        INSERT INTO Facilities (FacilityID, FacilityName, FacilityType, City, StateCode, Region, BedCapacity)
        VALUES (:id, :name, :type, :city, :state, :region, :beds)
        """,
        FACILITIES,
    )
    connection.executemany(
        """
        INSERT INTO InsurancePlans (InsuranceID, PayerName, PlanName, PlanType, CoverageRate)
        VALUES (:id, :payer, :plan, :type, :coverage)
        """,
        INSURANCE_PLANS,
    )
    connection.executemany(
        """
        INSERT INTO Medications (MedicationID, MedicationName, Category, Form, UnitCost)
        VALUES (:id, :name, :category, :form, :unit_cost)
        """,
        MEDICATIONS,
    )


def seed_patients_and_coverage(
    connection: sqlite3.Connection,
    rows: list[dict],
    required_patient_ids: set[int],
) -> dict[int, int]:
    coverage_by_patient: dict[int, int] = {}
    seen_ids: set[int] = set()

    for row in rows:
        patient_id = int(row["PatientID"])
        if patient_id in seen_ids:
            continue
        seen_ids.add(patient_id)
        city, state = PATIENT_LOCATIONS[stable_index(f"city:{patient_id}", len(PATIENT_LOCATIONS))]
        dob = synthetic_date(1946, 2008, f"dob:{patient_id}")
        sex = ["Female", "Male", "Non-binary"][stable_index(f"sex:{patient_id}", 3)]

        connection.execute(
            """
            INSERT INTO Patients (PatientID, FirstName, LastName, Email, DateOfBirth, Sex, City, StateCode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id,
                row["firstname"].strip(),
                row["lastname"].strip(),
                row["email"].strip(),
                dob,
                sex,
                city,
                state,
            ),
        )

        insurance = INSURANCE_PLANS[stable_index(f"insurance:{patient_id}", len(INSURANCE_PLANS))]
        coverage_by_patient[patient_id] = insurance["id"]

        connection.execute(
            """
            INSERT INTO PatientCoverage (
                PatientID,
                InsuranceID,
                MemberNumber,
                GroupNumber,
                EffectiveDate,
                CoverageStatus,
                IsPrimary
            )
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                patient_id,
                insurance["id"],
                f"MBR-{patient_id:06d}",
                f"GRP-{1000 + stable_index(f'group:{patient_id}', 8000)}",
                synthetic_date(2018, 2024, f"coverage:{patient_id}"),
                "Pending Verification" if stable_index(f"coverage-status:{patient_id}", 10) == 0 else "Active",
            ),
        )

    missing_ids = sorted(required_patient_ids - seen_ids)
    for patient_id in missing_ids:
        first_name = synthetic_first_name(patient_id)
        last_name = synthetic_last_name(patient_id)
        city, state = PATIENT_LOCATIONS[stable_index(f"city:{patient_id}", len(PATIENT_LOCATIONS))]
        dob = synthetic_date(1946, 2008, f"dob:{patient_id}")
        sex = ["Female", "Male", "Non-binary"][stable_index(f"sex:{patient_id}", 3)]

        connection.execute(
            """
            INSERT INTO Patients (PatientID, FirstName, LastName, Email, DateOfBirth, Sex, City, StateCode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id,
                first_name,
                last_name,
                f"{first_name.lower()}.{last_name.lower()}{patient_id}@demo.local",
                dob,
                sex,
                city,
                state,
            ),
        )

        insurance = INSURANCE_PLANS[stable_index(f"insurance:{patient_id}", len(INSURANCE_PLANS))]
        coverage_by_patient[patient_id] = insurance["id"]
        connection.execute(
            """
            INSERT INTO PatientCoverage (
                PatientID,
                InsuranceID,
                MemberNumber,
                GroupNumber,
                EffectiveDate,
                CoverageStatus,
                IsPrimary
            )
            VALUES (?, ?, ?, ?, ?, 'Active', 1)
            """,
            (
                patient_id,
                insurance["id"],
                f"MBR-{patient_id:06d}",
                f"GRP-{1000 + stable_index(f'group:{patient_id}', 8000)}",
                synthetic_date(2018, 2024, f"coverage:{patient_id}"),
            ),
        )

    return coverage_by_patient


def seed_doctors(
    connection: sqlite3.Connection,
    rows: list[dict],
    required_doctor_ids: set[int],
) -> tuple[dict[int, int], dict[int, str]]:
    doctor_facilities: dict[int, int] = {}
    specialties: dict[int, str] = {}
    seen_ids: set[int] = set()

    for row in rows:
        doctor_id = int(row["DoctorID"])
        if doctor_id in seen_ids:
            continue
        seen_ids.add(doctor_id)
        specialty = row["Specialization"].strip()
        facility_id = facility_for_specialty(specialty, doctor_id)
        phone = f"(415) 55{doctor_id % 10}-{doctor_id:04d}"

        connection.execute(
            """
            INSERT INTO Doctors (DoctorID, DoctorName, Specialization, DoctorContact, FacilityID)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                doctor_id,
                row["DoctorName"].strip(),
                specialty,
                phone,
                facility_id,
            ),
        )
        doctor_facilities[doctor_id] = facility_id
        specialties[doctor_id] = specialty

    specialty_pool = sorted({row["Specialization"].strip() for row in rows})
    missing_ids = sorted(required_doctor_ids - seen_ids)
    for doctor_id in missing_ids:
        specialty = specialty_pool[stable_index(f"specialty:{doctor_id}", len(specialty_pool))]
        facility_id = facility_for_specialty(specialty, doctor_id)
        connection.execute(
            """
            INSERT INTO Doctors (DoctorID, DoctorName, Specialization, DoctorContact, FacilityID)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                doctor_id,
                f"{synthetic_first_name(doctor_id)} {synthetic_last_name(doctor_id)}",
                specialty,
                f"(415) 55{doctor_id % 10}-{doctor_id:04d}",
                facility_id,
            ),
        )
        doctor_facilities[doctor_id] = facility_id
        specialties[doctor_id] = specialty

    return doctor_facilities, specialties


def seed_appointments(
    connection: sqlite3.Connection,
    rows: list[dict],
    patient_ids: set[int],
    doctor_facilities: dict[int, int],
    specialties: dict[int, str],
    reference_date: date,
) -> tuple[dict[int, AppointmentMeta], dict[int, list[AppointmentMeta]], int]:
    appointments_by_id: dict[int, AppointmentMeta] = {}
    appointments_by_patient: dict[int, list[AppointmentMeta]] = defaultdict(list)
    next_id = 1
    seen_ids: set[int] = set()

    for row in rows:
        appointment_id = int(row["AppointmentID"])
        if appointment_id in seen_ids:
            continue
        seen_ids.add(appointment_id)
        patient_id = int(row["PatientID"])
        doctor_id = int(row["DoctorID"])
        if patient_id not in patient_ids:
            continue
        facility_id = doctor_facilities.get(doctor_id)
        if not facility_id:
            continue

        appointment_date = row["Date"]
        appointment_time = parse_time(row["Time"])
        specialty = specialties[doctor_id]
        status = historical_status(appointment_id, appointment_date, reference_date)
        visit_type = visit_type_for_specialty(specialty)
        encounter_channel = encounter_channel_for_specialty(specialty)

        connection.execute(
            """
            INSERT INTO Appointments (
                AppointmentID,
                AppointmentDate,
                AppointmentTime,
                PatientID,
                DoctorID,
                FacilityID,
                VisitType,
                AppointmentStatus,
                EncounterChannel
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                appointment_id,
                appointment_date,
                appointment_time,
                patient_id,
                doctor_id,
                facility_id,
                visit_type,
                status,
                encounter_channel,
            ),
        )

        meta = AppointmentMeta(
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            facility_id=facility_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status=status,
            visit_type=visit_type,
        )
        appointments_by_id[appointment_id] = meta
        appointments_by_patient[patient_id].append(meta)
        next_id = max(next_id, appointment_id + 1)

    for items in appointments_by_patient.values():
        items.sort(key=lambda item: (item.appointment_date, item.appointment_time))

    return appointments_by_id, appointments_by_patient, next_id


def seed_future_appointments(
    connection: sqlite3.Connection,
    next_appointment_id: int,
    appointments_by_id: dict[int, AppointmentMeta],
    appointments_by_patient: dict[int, list[AppointmentMeta]],
    doctor_facilities: dict[int, int],
    specialties: dict[int, str],
    patient_ids: list[int],
    reference_date: date,
) -> int:
    doctor_ids = sorted(doctor_facilities)

    for offset in range(1, 25):
        appointment_id = next_appointment_id
        next_appointment_id += 1
        patient_id = patient_ids[(offset * 29) % len(patient_ids)]
        doctor_id = doctor_ids[(offset * 31) % len(doctor_ids)]
        facility_id = doctor_facilities[doctor_id]
        specialty = specialties[doctor_id]
        appointment_date = (reference_date + timedelta(days=offset)).isoformat()
        appointment_time = f"{8 + (offset % 9):02d}:{'30' if offset % 2 else '00'}"
        status = "Confirmed" if offset < 4 else "Scheduled"
        visit_type = visit_type_for_specialty(specialty)
        encounter_channel = "Outpatient"

        connection.execute(
            """
            INSERT INTO Appointments (
                AppointmentID,
                AppointmentDate,
                AppointmentTime,
                PatientID,
                DoctorID,
                FacilityID,
                VisitType,
                AppointmentStatus,
                EncounterChannel
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                appointment_id,
                appointment_date,
                appointment_time,
                patient_id,
                doctor_id,
                facility_id,
                visit_type,
                status,
                encounter_channel,
            ),
        )

        meta = AppointmentMeta(
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            facility_id=facility_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status=status,
            visit_type=visit_type,
        )
        appointments_by_id[appointment_id] = meta
        appointments_by_patient[patient_id].append(meta)

    for items in appointments_by_patient.values():
        items.sort(key=lambda item: (item.appointment_date, item.appointment_time))

    return next_appointment_id


def seed_procedures(
    connection: sqlite3.Connection,
    rows: list[dict],
    appointments_by_id: dict[int, AppointmentMeta],
) -> tuple[dict[int, list[dict]], int]:
    procedures_by_appointment: dict[int, list[dict]] = defaultdict(list)
    next_id = 1

    for row in rows:
        appointment_id = int(row["AppointmentID"])
        if appointment_id not in appointments_by_id:
            continue

        procedure_name = row["ProcedureName"].strip()
        family = procedure_family(procedure_name)
        acuity = acuity_for_procedure(procedure_name)
        source_id = int(row["ProcedureID"]) if row["ProcedureID"] else None

        connection.execute(
            """
            INSERT INTO MedicalProcedures (
                ProcedureRecordID,
                SourceProcedureID,
                ProcedureName,
                AppointmentID,
                ProcedureFamily,
                AcuityLevel
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (next_id, source_id, procedure_name, appointment_id, family, acuity),
        )
        procedures_by_appointment[appointment_id].append(
            {"record_id": next_id, "name": procedure_name, "family": family}
        )
        next_id += 1

    return procedures_by_appointment, next_id


def seed_prescriptions(
    connection: sqlite3.Connection,
    appointments_by_id: dict[int, AppointmentMeta],
    specialties: dict[int, str],
    reference_date: date,
) -> dict[int, list[dict]]:
    medications_by_appointment: dict[int, list[dict]] = defaultdict(list)
    next_id = 1

    for appointment in appointments_by_id.values():
        if appointment.status not in {"Completed", "Confirmed", "Scheduled"}:
            continue
        if stable_index(f"rx:{appointment.appointment_id}", 100) > 62:
            continue

        medication = medication_for_specialty(specialties[appointment.doctor_id], appointment.appointment_id)
        duration = 7 + stable_index(f"duration:{appointment.appointment_id}", 24)
        start_date = appointment.appointment_date
        end_date = (date.fromisoformat(start_date) + timedelta(days=duration)).isoformat()
        if appointment.appointment_date >= reference_date.isoformat():
            status = "Planned"
        elif end_date >= reference_date.isoformat():
            status = "Active"
        else:
            status = "Completed"

        dosage = ["5 mg", "10 mg", "20 mg", "40 mg"][stable_index(f"dosage:{appointment.appointment_id}", 4)]
        frequency = ["Daily", "Twice daily", "Every 8 hours", "As needed"][stable_index(f"freq:{appointment.appointment_id}", 4)]

        connection.execute(
            """
            INSERT INTO Prescriptions (
                PrescriptionID,
                AppointmentID,
                PatientID,
                DoctorID,
                MedicationID,
                Dosage,
                Frequency,
                DurationDays,
                StartDate,
                EndDate,
                PrescriptionStatus
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                next_id,
                appointment.appointment_id,
                appointment.patient_id,
                appointment.doctor_id,
                medication["id"],
                dosage,
                frequency,
                duration,
                start_date,
                end_date,
                status,
            ),
        )
        medications_by_appointment[appointment.appointment_id].append(medication)
        next_id += 1

    return medications_by_appointment


def seed_lab_results(
    connection: sqlite3.Connection,
    appointments_by_id: dict[int, AppointmentMeta],
    specialties: dict[int, str],
    reference_date: date,
) -> dict[int, list[dict]]:
    labs_by_appointment: dict[int, list[dict]] = defaultdict(list)
    next_id = 1

    for appointment in appointments_by_id.values():
        if appointment.status != "Completed":
            continue
        if appointment.appointment_date > reference_date.isoformat():
            continue
        if stable_index(f"lab:{appointment.appointment_id}", 100) > 58:
            continue

        templates = tests_for_specialty(specialties[appointment.doctor_id])
        selected = templates[stable_index(f"lab-template:{appointment.appointment_id}", len(templates))]
        flag_roll = stable_index(f"lab-flag:{appointment.appointment_id}", 100)
        if flag_roll < 8:
            flag = "Critical"
        elif flag_roll < 28:
            flag = "Attention"
        else:
            flag = "Normal"

        value = lab_value(selected, flag, appointment.appointment_id)
        collected_at = f"{appointment.appointment_date}T{appointment.appointment_time}:00"

        connection.execute(
            """
            INSERT INTO LabResults (
                LabResultID,
                AppointmentID,
                PatientID,
                FacilityID,
                TestName,
                Category,
                ResultValue,
                Unit,
                ReferenceRange,
                ResultFlag,
                CollectedAt,
                ResultStatus
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                next_id,
                appointment.appointment_id,
                appointment.patient_id,
                appointment.facility_id,
                selected["name"],
                selected["category"],
                value,
                selected["unit"],
                f"{selected['low']}-{selected['high']} {selected['unit']}",
                flag,
                collected_at,
                "Final",
            ),
        )
        labs_by_appointment[appointment.appointment_id].append({"name": selected["name"], "flag": flag})
        next_id += 1

    return labs_by_appointment


def seed_invoices(
    connection: sqlite3.Connection,
    billing_rows: list[dict],
    appointments_by_id: dict[int, AppointmentMeta],
    appointments_by_patient: dict[int, list[AppointmentMeta]],
    procedures_by_appointment: dict[int, list[dict]],
    prescriptions_by_appointment: dict[int, list[dict]],
    labs_by_appointment: dict[int, list[dict]],
    coverage_by_patient: dict[int, int],
    doctor_facilities: dict[int, int],
    specialties: dict[int, str],
    next_appointment_id: int,
    next_procedure_id: int,
    reference_date: date,
) -> None:
    line_item_id = 1
    doctor_ids = sorted(doctor_facilities)

    for row in billing_rows:
        patient_id = int(row["PatientID"])
        invoice_id = row["InvoiceID"].strip()
        charge_total = int(row["Amount"])
        appointment = select_or_create_invoice_appointment(
            connection,
            patient_id,
            invoice_id,
            row["Items"].strip(),
            appointments_by_id,
            appointments_by_patient,
            doctor_ids,
            doctor_facilities,
            specialties,
            next_appointment_id,
            reference_date,
        )
        next_appointment_id = max(next_appointment_id, max(appointments_by_id) + 1)

        procedures = procedures_by_appointment.get(appointment.appointment_id, [])
        if not procedures:
            created = create_procedure(
                connection,
                next_procedure_id,
                appointment.appointment_id,
                row["Items"].strip(),
            )
            procedures_by_appointment[appointment.appointment_id].append(created)
            procedures = [created]
            next_procedure_id += 1

        insurance_id = coverage_by_patient[patient_id]
        plan = next(plan for plan in INSURANCE_PLANS if plan["id"] == insurance_id)
        insurance_covered = int(round(charge_total * plan["coverage"]))
        patient_responsibility = charge_total - insurance_covered
        billing_status = invoice_status(appointment.appointment_date, invoice_id, reference_date)
        issued_at = (date.fromisoformat(appointment.appointment_date) + timedelta(days=2)).isoformat()
        paid_at = None
        if billing_status == "Settled":
            paid_at = (date.fromisoformat(issued_at) + timedelta(days=10 + stable_index(f"paid:{invoice_id}", 30))).isoformat()

        connection.execute(
            """
            INSERT INTO Invoices (
                InvoiceID,
                AppointmentID,
                PatientID,
                InsuranceID,
                FacilityID,
                BillingStatus,
                TotalCharge,
                InsuranceCovered,
                PatientResponsibility,
                IssuedAt,
                PaidAt
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_id,
                appointment.appointment_id,
                patient_id,
                insurance_id,
                appointment.facility_id,
                billing_status,
                charge_total,
                insurance_covered,
                patient_responsibility,
                issued_at,
                paid_at,
            ),
        )

        components = [
            ("Facility", "Facility fee", None, 0.18),
            ("Professional", "Physician services", None, 0.24),
            ("Procedure", procedures[0]["name"], procedures[0]["record_id"], 0.38),
        ]

        if labs_by_appointment.get(appointment.appointment_id):
            components.append(("Diagnostics", "Diagnostic review", None, 0.11))
        if prescriptions_by_appointment.get(appointment.appointment_id):
            components.append(("Pharmacy", "Medication management", None, 0.09))

        remainder = 1.0 - sum(component[3] for component in components)
        if remainder > 0:
            category, description, procedure_id, weight = components[1]
            components[1] = (category, description, procedure_id, weight + remainder)

        amounts = allocate_amounts(charge_total, [component[3] for component in components])
        for component, amount in zip(components, amounts):
            category, description, procedure_id, _weight = component
            connection.execute(
                """
                INSERT INTO InvoiceLineItems (
                    LineItemID,
                    InvoiceID,
                    ProcedureRecordID,
                    ChargeCategory,
                    ChargeDescription,
                    Amount
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (line_item_id, invoice_id, procedure_id, category, description, amount),
            )
            line_item_id += 1


def select_or_create_invoice_appointment(
    connection: sqlite3.Connection,
    patient_id: int,
    invoice_id: str,
    procedure_name: str,
    appointments_by_id: dict[int, AppointmentMeta],
    appointments_by_patient: dict[int, list[AppointmentMeta]],
    doctor_ids: list[int],
    doctor_facilities: dict[int, int],
    specialties: dict[int, str],
    next_appointment_id: int,
    reference_date: date,
) -> AppointmentMeta:
    existing = appointments_by_patient.get(patient_id)
    if existing:
        viable = [item for item in existing if item.status not in {"Cancelled", "No Show"}]
        if viable:
            return viable[stable_index(f"invoice:{invoice_id}", len(viable))]

    doctor_id = doctor_ids[stable_index(f"doctor:{patient_id}", len(doctor_ids))]
    facility_id = doctor_facilities[doctor_id]
    appointment_date = (reference_date - timedelta(days=90 + stable_index(f"retro:{invoice_id}", 680))).isoformat()
    appointment_time = f"{9 + stable_index(f'time:{invoice_id}', 8):02d}:{'30' if stable_index(invoice_id, 2) else '00'}"
    visit_type = visit_type_for_specialty(specialties[doctor_id])

    connection.execute(
        """
        INSERT INTO Appointments (
            AppointmentID,
            AppointmentDate,
            AppointmentTime,
            PatientID,
            DoctorID,
            FacilityID,
            VisitType,
            AppointmentStatus,
            EncounterChannel
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Completed', 'Outpatient')
        """,
        (
            next_appointment_id,
            appointment_date,
            appointment_time,
            patient_id,
            doctor_id,
            facility_id,
            visit_type,
        ),
    )

    meta = AppointmentMeta(
        appointment_id=next_appointment_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        facility_id=facility_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        status="Completed",
        visit_type=visit_type,
    )
    appointments_by_id[next_appointment_id] = meta
    appointments_by_patient[patient_id].append(meta)
    appointments_by_patient[patient_id].sort(key=lambda item: (item.appointment_date, item.appointment_time))
    return meta


def create_procedure(
    connection: sqlite3.Connection,
    procedure_record_id: int,
    appointment_id: int,
    procedure_name: str,
) -> dict:
    family = procedure_family(procedure_name)
    acuity = acuity_for_procedure(procedure_name)
    connection.execute(
        """
        INSERT INTO MedicalProcedures (
            ProcedureRecordID,
            SourceProcedureID,
            ProcedureName,
            AppointmentID,
            ProcedureFamily,
            AcuityLevel
        )
        VALUES (?, NULL, ?, ?, ?, ?)
        """,
        (procedure_record_id, procedure_name, appointment_id, family, acuity),
    )
    return {"record_id": procedure_record_id, "name": procedure_name, "family": family}


def invoice_status(appointment_date: str, invoice_id: str, reference_date: date) -> str:
    if appointment_date >= reference_date.isoformat():
        return "Pre-bill review"

    roll = stable_index(f"status:{invoice_id}", 100)
    if roll < 62:
        return "Settled"
    if roll < 78:
        return "Pending payer"
    if roll < 90:
        return "Patient balance"
    return "Under review"


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def stable_index(key: str, modulo: int) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulo


def synthetic_date(start_year: int, end_year: int, key: str) -> str:
    year = start_year + stable_index(f"{key}:year", end_year - start_year + 1)
    month = 1 + stable_index(f"{key}:month", 12)
    day = 1 + stable_index(f"{key}:day", 28)
    return date(year, month, day).isoformat()


def parse_time(value: str) -> str:
    if "T" in value:
        return value.split("T", 1)[1][:5]
    return value[:5]


def facility_for_specialty(specialty: str, doctor_id: int) -> int:
    lowered = specialty.lower()
    if "onc" in lowered:
        return 3
    if "pedi" in lowered or "gyne" in lowered or "obst" in lowered:
        return 2
    if "ophthalm" in lowered or "dermat" in lowered or "allerg" in lowered:
        return 4
    if "infectious" in lowered or "radiology" in lowered:
        return 6
    if "emergency" in lowered or "surgery" in lowered:
        return 1 if doctor_id % 2 == 0 else 5
    return 1 if doctor_id % 3 else 5


def visit_type_for_specialty(specialty: str) -> str:
    lowered = specialty.lower()
    if "surgery" in lowered or "onc" in lowered:
        return "Procedure Follow-up"
    if "emergency" in lowered:
        return "Acute Evaluation"
    if "pedi" in lowered:
        return "Wellness Visit"
    if "cardio" in lowered or "neuro" in lowered or "neph" in lowered:
        return "Chronic Care Review"
    return "Specialty Consultation"


def encounter_channel_for_specialty(specialty: str) -> str:
    lowered = specialty.lower()
    if "emergency" in lowered:
        return "Emergency"
    if "surgery" in lowered or "onc" in lowered:
        return "Inpatient"
    return "Outpatient"


def historical_status(appointment_id: int, appointment_date: str, reference_date: date) -> str:
    if appointment_date >= reference_date.isoformat():
        return "Scheduled"
    roll = stable_index(f"appt-status:{appointment_id}", 100)
    if roll < 8:
        return "Cancelled"
    if roll < 15:
        return "No Show"
    return "Completed"


def procedure_family(procedure_name: str) -> str:
    lowered = procedure_name.lower()
    if any(word in lowered for word in ["surgery", "biopsy", "transplant", "implant", "angioplasty", "cochlear"]):
        return "Surgical"
    if any(word in lowered for word in ["x-rays", "scan", "endoscopy", "puncture", "monitoring", "testing"]):
        return "Diagnostics"
    if any(word in lowered for word in ["therapy", "care", "management", "chemotherapy", "dialysis"]):
        return "Therapeutic"
    if any(word in lowered for word in ["immunization", "check-up", "allergy"]):
        return "Preventive"
    return "Clinical Services"


def acuity_for_procedure(procedure_name: str) -> str:
    lowered = procedure_name.lower()
    if any(word in lowered for word in ["trauma", "transplant", "bypass", "intensive care", "resuscitation"]):
        return "High"
    if any(word in lowered for word in ["surgery", "chemotherapy", "dialysis", "angioplasty"]):
        return "Moderate"
    return "Routine"


def medication_for_specialty(specialty: str, appointment_id: int) -> dict:
    lowered = specialty.lower()
    if "cardio" in lowered:
        pool = [1, 2, 3]
    elif "onc" in lowered:
        pool = [4, 5]
    elif "infectious" in lowered or "pedi" in lowered:
        pool = [6, 7]
    elif "neuro" in lowered or "psych" in lowered:
        pool = [8, 11]
    elif "endo" in lowered or "intern" in lowered:
        pool = [9, 10]
    else:
        pool = [5, 12, 6]
    medication_id = pool[stable_index(f"med:{appointment_id}", len(pool))]
    return next(item for item in MEDICATIONS if item["id"] == medication_id)


def tests_for_specialty(specialty: str) -> list[dict]:
    lowered = specialty.lower()
    if "cardio" in lowered:
        return LAB_TESTS["cardiology"]
    if "onc" in lowered:
        return LAB_TESTS["oncology"]
    if "pulmo" in lowered or "infectious" in lowered:
        return LAB_TESTS["respiratory"]
    if "neph" in lowered:
        return LAB_TESTS["renal"]
    if "gyne" in lowered or "obst" in lowered or "pedi" in lowered:
        return LAB_TESTS["women"]
    return LAB_TESTS["default"]


def lab_value(template: dict, flag: str, appointment_id: int) -> float:
    low = template["low"]
    high = template["high"]
    span = high - low if high != low else max(high, 1.0)
    marker = stable_index(f"value:{appointment_id}:{template['name']}", 1000) / 1000

    if flag == "Normal":
        return round(low + span * (0.2 + marker * 0.6), 2)
    if flag == "Attention":
        if stable_index(f"direction:{appointment_id}:{template['name']}", 2) == 0:
            return round(low - span * (0.1 + marker * 0.25), 2)
        return round(high + span * (0.1 + marker * 0.35), 2)
    return round(high + span * (0.45 + marker * 0.6), 2)


def allocate_amounts(total: int, weights: list[float]) -> list[int]:
    raw = [int(total * weight) for weight in weights]
    difference = total - sum(raw)
    if raw:
        raw[-1] += difference
    return raw


def synthetic_first_name(seed: int) -> str:
    names = [
        "Avery",
        "Jordan",
        "Morgan",
        "Casey",
        "Taylor",
        "Skyler",
        "Quinn",
        "Reese",
    ]
    return names[stable_index(f"first:{seed}", len(names))]


def synthetic_last_name(seed: int) -> str:
    names = [
        "Rowe",
        "Bennett",
        "Hart",
        "Sloan",
        "Ellis",
        "Monroe",
        "Parker",
        "Shaw",
    ]
    return names[stable_index(f"last:{seed}", len(names))]
