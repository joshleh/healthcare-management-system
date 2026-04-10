from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import date, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from backend.bootstrap import (
    INSURANCE_PLANS,
    MEDICATIONS,
    build_demo_database,
    encounter_channel_for_specialty,
    procedure_family,
    acuity_for_procedure,
)


ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
RUNTIME_DIR = ROOT / "runtime"
DB_PATH = RUNTIME_DIR / "healthcare_demo.db"
REFERENCE_DATE = date.fromisoformat(os.environ.get("DEMO_REFERENCE_DATE", "2026-04-09"))


def connect_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def query_one(sql: str, params: list | tuple = ()) -> dict:
    with connect_db() as connection:
        row = connection.execute(sql, params).fetchone()
    return dict(row) if row else {}


def query_all(sql: str, params: list | tuple = ()) -> list[dict]:
    with connect_db() as connection:
        rows = connection.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def build_filter_clause(params: dict[str, list[str]], alias: str = "a") -> tuple[str, list]:
    clauses: list[str] = []
    values: list = []

    facility_id = first_param(params, "facility")
    specialty = first_param(params, "specialty")

    if facility_id and facility_id != "all":
        clauses.append(f"{alias}.FacilityID = ?")
        values.append(int(facility_id))

    if specialty and specialty != "all":
        clauses.append("d.Specialization = ?")
        values.append(specialty)

    if not clauses:
        return "", values

    return "WHERE " + " AND ".join(clauses), values


def first_param(params: dict[str, list[str]], key: str, default: str = "") -> str:
    values = params.get(key)
    if not values:
        return default
    return values[0]


def get_options() -> dict:
    facilities = query_all(
        """
        SELECT FacilityID AS id, FacilityName AS name, FacilityType AS type, City AS city, StateCode AS state
        FROM Facilities
        ORDER BY FacilityName
        """
    )
    specialties = query_all(
        """
        SELECT DISTINCT Specialization AS name
        FROM Doctors
        ORDER BY Specialization
        """
    )
    featured_patients = query_all(
        """
        SELECT
            p.PatientID AS id,
            p.FirstName || ' ' || p.LastName AS name,
            COALESCE(SUM(i.TotalCharge), 0) AS billed
        FROM Patients p
        LEFT JOIN Invoices i ON i.PatientID = p.PatientID
        GROUP BY p.PatientID
        ORDER BY billed DESC, name
        LIMIT 8
        """
    )

    return {
        "referenceDate": REFERENCE_DATE.isoformat(),
        "facilities": facilities,
        "specialties": specialties,
        "insurancePlans": [
            {
                "id": plan["id"],
                "payer": plan["payer"],
                "plan": plan["plan"],
                "type": plan["type"],
            }
            for plan in INSURANCE_PLANS
        ],
        "medications": [
            {
                "id": medication["id"],
                "name": medication["name"],
                "category": medication["category"],
            }
            for medication in MEDICATIONS
        ],
        "featuredPatients": featured_patients,
    }


def next_demo_invoice_id() -> str:
    row = query_one(
        """
        SELECT COUNT(*) + 1 AS next_id
        FROM Invoices
        WHERE InvoiceID LIKE 'demo-%'
        """
    )
    return f"demo-{int(row['next_id']):06d}"


def choose_doctor_for_admin(specialty: str, facility_id: int) -> dict:
    doctor = query_one(
        """
        SELECT DoctorID, DoctorName, Specialization, FacilityID
        FROM Doctors
        WHERE Specialization = ? AND FacilityID = ?
        ORDER BY DoctorName
        LIMIT 1
        """,
        [specialty, facility_id],
    )
    if doctor:
        return doctor

    return {}


def create_demo_encounter(payload: dict) -> dict:
    required_fields = [
        "firstName",
        "lastName",
        "facilityId",
        "specialty",
        "appointmentDate",
        "appointmentTime",
        "visitType",
        "status",
        "insuranceId",
    ]
    missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    first_name = str(payload["firstName"]).strip()
    last_name = str(payload["lastName"]).strip()
    email = str(payload.get("email") or "").strip() or f"{first_name.lower()}.{last_name.lower()}@demo.local"
    city = str(payload.get("city") or "San Francisco").strip()
    state_code = str(payload.get("stateCode") or "CA").strip() or "CA"
    sex = str(payload.get("sex") or "Female").strip()
    date_of_birth = str(payload.get("dateOfBirth") or "1989-01-15").strip()
    facility_id = int(payload["facilityId"])
    insurance_id = int(payload["insuranceId"])
    specialty = str(payload["specialty"]).strip()
    appointment_date = str(payload["appointmentDate"]).strip()
    appointment_time = str(payload["appointmentTime"]).strip()
    visit_type = str(payload["visitType"]).strip()
    appointment_status = str(payload["status"]).strip()
    procedure_name = str(payload.get("procedureName") or "Clinical follow-up").strip()
    bill_amount = int(payload.get("billAmount") or 0)
    lab_flag = str(payload.get("labFlag") or "None").strip()
    lab_test_name = str(payload.get("labTestName") or "Basic Metabolic Panel").strip()
    medication_id = payload.get("medicationId")

    insurance_plan = next((plan for plan in INSURANCE_PLANS if plan["id"] == insurance_id), None)
    if insurance_plan is None:
        raise ValueError("The selected insurance plan is invalid.")

    with connect_db() as connection:
        doctor = choose_doctor_for_admin(specialty, facility_id)
        patient_id = int(
            connection.execute("SELECT COALESCE(MAX(PatientID), 0) + 1 FROM Patients").fetchone()[0]
        )
        if not doctor:
            doctor_id = int(
                connection.execute("SELECT COALESCE(MAX(DoctorID), 0) + 1 FROM Doctors").fetchone()[0]
            )
            doctor = {
                "DoctorID": doctor_id,
                "DoctorName": f"Demo {specialty} Team",
                "FacilityID": facility_id,
            }
            connection.execute(
                """
                INSERT INTO Doctors (DoctorID, DoctorName, Specialization, DoctorContact, FacilityID)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    doctor_id,
                    doctor["DoctorName"],
                    specialty,
                    f"(415) 700-{doctor_id:04d}",
                    facility_id,
                ),
            )
        appointment_id = int(
            connection.execute("SELECT COALESCE(MAX(AppointmentID), 0) + 1 FROM Appointments").fetchone()[0]
        )
        procedure_record_id = int(
            connection.execute(
                "SELECT COALESCE(MAX(ProcedureRecordID), 0) + 1 FROM MedicalProcedures"
            ).fetchone()[0]
        )

        connection.execute(
            """
            INSERT INTO Patients (PatientID, FirstName, LastName, Email, DateOfBirth, Sex, City, StateCode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (patient_id, first_name, last_name, email, date_of_birth, sex, city, state_code),
        )
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
                insurance_id,
                f"MBR-{patient_id:06d}",
                f"GRP-{1000 + patient_id}",
                REFERENCE_DATE.isoformat(),
            ),
        )
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
                doctor["DoctorID"],
                facility_id,
                visit_type,
                appointment_status,
                encounter_channel_for_specialty(specialty),
            ),
        )
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
            (
                procedure_record_id,
                procedure_name,
                appointment_id,
                procedure_family(procedure_name),
                acuity_for_procedure(procedure_name),
            ),
        )

        if medication_id:
            medication_id = int(medication_id)
            prescription_id = int(
                connection.execute(
                    "SELECT COALESCE(MAX(PrescriptionID), 0) + 1 FROM Prescriptions"
                ).fetchone()[0]
            )
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
                VALUES (?, ?, ?, ?, ?, '10 mg', 'Daily', 30, ?, date(?, '+30 day'), ?)
                """,
                (
                    prescription_id,
                    appointment_id,
                    patient_id,
                    doctor["DoctorID"],
                    medication_id,
                    appointment_date,
                    appointment_date,
                    "Planned" if appointment_date >= REFERENCE_DATE.isoformat() else "Active",
                ),
            )

        if lab_flag and lab_flag != "None":
            lab_result_id = int(
                connection.execute("SELECT COALESCE(MAX(LabResultID), 0) + 1 FROM LabResults").fetchone()[0]
            )
            if lab_flag == "Critical":
                result_value = 145.0
            else:
                result_value = 118.0
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
                VALUES (?, ?, ?, ?, ?, 'Chemistry', ?, 'mg/dL', '70-110 mg/dL', ?, ?, 'Final')
                """,
                (
                    lab_result_id,
                    appointment_id,
                    patient_id,
                    facility_id,
                    lab_test_name,
                    result_value,
                    lab_flag,
                    f"{appointment_date}T{appointment_time}:00",
                ),
            )

        if bill_amount > 0:
            invoice_id = next_demo_invoice_id()
            insurance_covered = int(round(bill_amount * insurance_plan["coverage"]))
            patient_responsibility = bill_amount - insurance_covered
            line_item_id = int(
                connection.execute(
                    "SELECT COALESCE(MAX(LineItemID), 0) + 1 FROM InvoiceLineItems"
                ).fetchone()[0]
            )
            issued_at = appointment_date if appointment_date >= REFERENCE_DATE.isoformat() else str(
                date.fromisoformat(appointment_date) + timedelta(days=2)
            )
            billing_status = "Pre-bill review" if appointment_date >= REFERENCE_DATE.isoformat() else "Pending payer"

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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    invoice_id,
                    appointment_id,
                    patient_id,
                    insurance_id,
                    facility_id,
                    billing_status,
                    bill_amount,
                    insurance_covered,
                    patient_responsibility,
                    issued_at,
                ),
            )
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
                VALUES (?, ?, ?, 'Procedure', ?, ?)
                """,
                (
                    line_item_id,
                    invoice_id,
                    procedure_record_id,
                    procedure_name,
                    bill_amount,
                ),
            )

        connection.commit()

    patient_name = f"{first_name} {last_name}"
    return {
        "success": True,
        "patientId": patient_id,
        "patientName": patient_name,
        "appointmentId": appointment_id,
        "message": f"Added demo encounter for {patient_name}.",
    }


def get_overview(params: dict[str, list[str]]) -> dict:
    where_clause, values = build_filter_clause(params)
    threshold = REFERENCE_DATE.isoformat()

    appointment_counts = query_one(
        f"""
        SELECT
            COUNT(*) AS totalAppointments,
            SUM(CASE WHEN a.AppointmentDate >= ? THEN 1 ELSE 0 END) AS scheduledVisits,
            SUM(CASE WHEN a.AppointmentStatus = 'Completed' THEN 1 ELSE 0 END) AS completedVisits
        FROM Appointments a
        JOIN Doctors d ON d.DoctorID = a.DoctorID
        {where_clause}
        """,
        [threshold, *values],
    )
    invoice_metrics = query_one(
        f"""
        SELECT
            COALESCE(SUM(i.TotalCharge), 0) AS grossRevenue,
            COALESCE(AVG(i.TotalCharge), 0) AS avgInvoice,
            COALESCE(AVG(CASE WHEN i.TotalCharge > 0 THEN CAST(i.InsuranceCovered AS REAL) / i.TotalCharge END), 0) AS coverageRate
        FROM Appointments a
        JOIN Doctors d ON d.DoctorID = a.DoctorID
        JOIN Invoices i ON i.AppointmentID = a.AppointmentID
        {where_clause}
        """,
        values,
    )
    abnormal_labs = query_one(
        f"""
        SELECT COUNT(*) AS abnormalLabs
        FROM LabResults lr
        JOIN Appointments a ON a.AppointmentID = lr.AppointmentID
        JOIN Doctors d ON d.DoctorID = a.DoctorID
        {where_clause} {"AND" if where_clause else "WHERE"} lr.ResultFlag IN ('Attention', 'Critical')
        """,
        values,
    )

    highlight = query_one(
        f"""
        SELECT
            f.FacilityName AS facility,
            COUNT(DISTINCT a.AppointmentID) AS visitCount,
            COALESCE(SUM(i.TotalCharge), 0) AS revenue
        FROM Appointments a
        JOIN Doctors d ON d.DoctorID = a.DoctorID
        JOIN Facilities f ON f.FacilityID = a.FacilityID
        LEFT JOIN Invoices i ON i.AppointmentID = a.AppointmentID
        {where_clause}
        GROUP BY f.FacilityID
        ORDER BY revenue DESC, visitCount DESC
        LIMIT 1
        """,
        values,
    )

    return {
        "metrics": {
            **appointment_counts,
            **invoice_metrics,
            **abnormal_labs,
        },
        "highlight": highlight,
    }


def get_revenue_trend(params: dict[str, list[str]]) -> dict:
    where_clause, values = build_filter_clause(params)
    rows = query_all(
        f"""
        SELECT
            substr(i.IssuedAt, 1, 7) AS period,
            COALESCE(SUM(i.TotalCharge), 0) AS revenue
        FROM Appointments a
        JOIN Doctors d ON d.DoctorID = a.DoctorID
        JOIN Invoices i ON i.AppointmentID = a.AppointmentID
        {where_clause}
        GROUP BY period
        ORDER BY period
        LIMIT 18
        """,
        values,
    )
    return {"points": rows}


def get_department_load(params: dict[str, list[str]]) -> dict:
    where_clause, values = build_filter_clause(params)
    rows = query_all(
        f"""
        SELECT
            d.Specialization AS specialty,
            COUNT(DISTINCT a.AppointmentID) AS visits,
            COUNT(DISTINCT a.PatientID) AS patients
        FROM Appointments a
        JOIN Doctors d ON d.DoctorID = a.DoctorID
        {where_clause}
        GROUP BY d.Specialization
        ORDER BY visits DESC
        LIMIT 8
        """,
        values,
    )
    return {"rows": rows}


def get_payer_mix(params: dict[str, list[str]]) -> dict:
    where_clause, values = build_filter_clause(params)
    rows = query_all(
        f"""
        SELECT
            ip.PayerName AS payer,
            COUNT(DISTINCT i.InvoiceID) AS invoices,
            SUM(i.TotalCharge) AS revenue
        FROM Appointments a
        JOIN Doctors d ON d.DoctorID = a.DoctorID
        JOIN Invoices i ON i.AppointmentID = a.AppointmentID
        JOIN InsurancePlans ip ON ip.InsuranceID = i.InsuranceID
        {where_clause}
        GROUP BY ip.InsuranceID
        ORDER BY revenue DESC
        LIMIT 6
        """,
        values,
    )
    return {"rows": rows}


def get_schedule(params: dict[str, list[str]]) -> dict:
    where_clause, values = build_filter_clause(params)
    rows = query_all(
        f"""
        SELECT
            a.AppointmentID AS id,
            a.AppointmentDate AS date,
            a.AppointmentTime AS time,
            a.AppointmentStatus AS status,
            a.VisitType AS visitType,
            p.FirstName || ' ' || p.LastName AS patient,
            d.DoctorName AS doctor,
            d.Specialization AS specialty,
            f.FacilityName AS facility
        FROM Appointments a
        JOIN Doctors d ON d.DoctorID = a.DoctorID
        JOIN Patients p ON p.PatientID = a.PatientID
        JOIN Facilities f ON f.FacilityID = a.FacilityID
        {where_clause}
        ORDER BY
            CASE WHEN a.AppointmentDate >= ? THEN 0 ELSE 1 END,
            ABS(julianday(a.AppointmentDate) - julianday(?)),
            a.AppointmentTime
        LIMIT 12
        """,
        [*values, REFERENCE_DATE.isoformat(), REFERENCE_DATE.isoformat()],
    )
    return {"rows": rows}


def get_lab_alerts(params: dict[str, list[str]]) -> dict:
    where_clause, values = build_filter_clause(params)
    rows = query_all(
        f"""
        SELECT
            lr.LabResultID AS id,
            lr.CollectedAt AS collectedAt,
            lr.TestName AS testName,
            lr.ResultValue AS value,
            lr.Unit AS unit,
            lr.ResultFlag AS flag,
            p.FirstName || ' ' || p.LastName AS patient,
            f.FacilityName AS facility
        FROM LabResults lr
        JOIN Appointments a ON a.AppointmentID = lr.AppointmentID
        JOIN Doctors d ON d.DoctorID = a.DoctorID
        JOIN Patients p ON p.PatientID = lr.PatientID
        JOIN Facilities f ON f.FacilityID = lr.FacilityID
        {where_clause} {"AND" if where_clause else "WHERE"} lr.ResultFlag IN ('Attention', 'Critical')
        ORDER BY
            CASE lr.ResultFlag WHEN 'Critical' THEN 0 ELSE 1 END,
            lr.CollectedAt DESC
        LIMIT 10
        """,
        values,
    )
    return {"rows": rows}


def search_patients(params: dict[str, list[str]]) -> dict:
    query = first_param(params, "query").strip().lower()
    if query:
        rows = query_all(
            """
            SELECT
                p.PatientID AS id,
                p.FirstName || ' ' || p.LastName AS name,
                p.Email AS email
            FROM Patients p
            WHERE lower(p.FirstName || ' ' || p.LastName) LIKE ?
               OR lower(p.Email) LIKE ?
            ORDER BY
                CASE
                    WHEN lower(p.FirstName || ' ' || p.LastName) = ? THEN 0
                    WHEN lower(p.Email) = ? THEN 1
                    WHEN lower(p.FirstName || ' ' || p.LastName) LIKE ? THEN 2
                    ELSE 3
                END,
                p.PatientID DESC,
                name
            LIMIT 10
            """,
            [f"%{query}%", f"%{query}%", query, query, f"{query}%"],
        )
    else:
        rows = query_all(
            """
            SELECT
                p.PatientID AS id,
                p.FirstName || ' ' || p.LastName AS name,
                p.Email AS email
            FROM Patients p
            LEFT JOIN Invoices i ON i.PatientID = p.PatientID
            GROUP BY p.PatientID
            ORDER BY COALESCE(SUM(i.TotalCharge), 0) DESC, name
            LIMIT 10
            """
        )
    return {"rows": rows}


def get_patient_journey(params: dict[str, list[str]]) -> dict:
    patient_id = first_param(params, "patient_id")
    if not patient_id:
        featured = get_options()["featuredPatients"]
        if not featured:
            return {"patient": {}, "timeline": []}
        patient_id = str(featured[0]["id"])

    patient = query_one(
        """
        SELECT
            p.PatientID AS id,
            p.FirstName || ' ' || p.LastName AS name,
            p.Email AS email,
            p.DateOfBirth AS dateOfBirth,
            p.Sex AS sex,
            p.City AS city,
            p.StateCode AS state,
            ip.PayerName AS payer,
            ip.PlanName AS planName,
            pc.MemberNumber AS memberNumber
        FROM Patients p
        LEFT JOIN PatientCoverage pc ON pc.PatientID = p.PatientID AND pc.IsPrimary = 1
        LEFT JOIN InsurancePlans ip ON ip.InsuranceID = pc.InsuranceID
        WHERE p.PatientID = ?
        """,
        [patient_id],
    )

    timeline = query_all(
        """
        SELECT
            eventDate,
            eventType,
            title,
            detail,
            status
        FROM (
            SELECT
                a.AppointmentDate AS eventDate,
                'Appointment' AS eventType,
                d.Specialization || ' visit with Dr. ' || d.DoctorName AS title,
                a.VisitType || ' at ' || f.FacilityName AS detail,
                a.AppointmentStatus AS status
            FROM Appointments a
            JOIN Doctors d ON d.DoctorID = a.DoctorID
            JOIN Facilities f ON f.FacilityID = a.FacilityID
            WHERE a.PatientID = ?

            UNION ALL

            SELECT
                a.AppointmentDate AS eventDate,
                'Procedure' AS eventType,
                mp.ProcedureName AS title,
                mp.ProcedureFamily || ' pathway' AS detail,
                mp.AcuityLevel AS status
            FROM MedicalProcedures mp
            JOIN Appointments a ON a.AppointmentID = mp.AppointmentID
            WHERE a.PatientID = ?

            UNION ALL

            SELECT
                substr(lr.CollectedAt, 1, 10) AS eventDate,
                'Lab' AS eventType,
                lr.TestName AS title,
                printf('%.1f %s', lr.ResultValue, lr.Unit) AS detail,
                lr.ResultFlag AS status
            FROM LabResults lr
            WHERE lr.PatientID = ?

            UNION ALL

            SELECT
                pr.StartDate AS eventDate,
                'Medication' AS eventType,
                m.MedicationName AS title,
                pr.Dosage || ' • ' || pr.Frequency AS detail,
                pr.PrescriptionStatus AS status
            FROM Prescriptions pr
            JOIN Medications m ON m.MedicationID = pr.MedicationID
            WHERE pr.PatientID = ?

            UNION ALL

            SELECT
                substr(i.IssuedAt, 1, 10) AS eventDate,
                'Billing' AS eventType,
                'Invoice ' || substr(i.InvoiceID, 1, 8) AS title,
                '$' || printf('%,d', i.TotalCharge) || ' total charge' AS detail,
                i.BillingStatus AS status
            FROM Invoices i
            WHERE i.PatientID = ?
        )
        ORDER BY eventDate DESC
        LIMIT 18
        """,
        [patient_id, patient_id, patient_id, patient_id, patient_id],
    )

    summary = {
        **query_one("SELECT COUNT(*) AS appointments FROM Appointments WHERE PatientID = ?", [patient_id]),
        **query_one(
            """
            SELECT COUNT(*) AS procedures
            FROM MedicalProcedures
            WHERE AppointmentID IN (SELECT AppointmentID FROM Appointments WHERE PatientID = ?)
            """,
            [patient_id],
        ),
        **query_one("SELECT COUNT(*) AS labs FROM LabResults WHERE PatientID = ?", [patient_id]),
        **query_one("SELECT COUNT(*) AS medications FROM Prescriptions WHERE PatientID = ?", [patient_id]),
        **query_one("SELECT COALESCE(SUM(TotalCharge), 0) AS billed FROM Invoices WHERE PatientID = ?", [patient_id]),
    }

    return {
        "patient": patient,
        "summary": summary,
        "timeline": timeline,
    }


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api(parsed)
            return

        if parsed.path in {"/", ""}:
            self.path = "/index.html"
        else:
            self.path = parsed.path

        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/admin/encounter":
            self.handle_admin_post()
            return

        self.respond_json({"error": "Not found"}, status=404)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[http] {self.address_string()} - {fmt % args}")

    def handle_api(self, parsed) -> None:
        params = parse_qs(parsed.query)

        routes = {
            "/api/options": get_options,
            "/api/overview": lambda: get_overview(params),
            "/api/revenue-trend": lambda: get_revenue_trend(params),
            "/api/department-load": lambda: get_department_load(params),
            "/api/payer-mix": lambda: get_payer_mix(params),
            "/api/schedule": lambda: get_schedule(params),
            "/api/lab-alerts": lambda: get_lab_alerts(params),
            "/api/patients": lambda: search_patients(params),
            "/api/patient-journey": lambda: get_patient_journey(params),
        }

        handler = routes.get(parsed.path)
        if handler is None:
            self.respond_json({"error": "Not found"}, status=404)
            return

        try:
            self.respond_json(handler())
        except Exception as exc:  # pragma: no cover - surfaced in local logs
            self.respond_json({"error": str(exc)}, status=500)

    def handle_admin_post(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw_body.decode("utf-8"))
            self.respond_json(create_demo_encounter(payload), status=201)
        except ValueError as exc:
            self.respond_json({"error": str(exc)}, status=400)
        except Exception as exc:  # pragma: no cover - surfaced in local logs
            self.respond_json({"error": str(exc)}, status=500)

    def respond_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    RUNTIME_DIR.mkdir(exist_ok=True)
    build_demo_database(DB_PATH, ROOT / "data", REFERENCE_DATE)

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else "8000"))
    server = ThreadingHTTPServer((host, port), AppHandler)

    print(f"Healthcare operations demo ready at http://{host}:{port}")
    print(f"Reference date: {REFERENCE_DATE.isoformat()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
