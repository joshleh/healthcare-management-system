PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS InvoiceLineItems;
DROP TABLE IF EXISTS Invoices;
DROP TABLE IF EXISTS LabResults;
DROP TABLE IF EXISTS Prescriptions;
DROP TABLE IF EXISTS Medications;
DROP TABLE IF EXISTS MedicalProcedures;
DROP TABLE IF EXISTS Appointments;
DROP TABLE IF EXISTS PatientCoverage;
DROP TABLE IF EXISTS InsurancePlans;
DROP TABLE IF EXISTS Doctors;
DROP TABLE IF EXISTS Patients;
DROP TABLE IF EXISTS Facilities;

PRAGMA foreign_keys = ON;

CREATE TABLE Facilities (
    FacilityID INTEGER PRIMARY KEY,
    FacilityName TEXT NOT NULL,
    FacilityType TEXT NOT NULL,
    City TEXT NOT NULL,
    StateCode TEXT NOT NULL,
    Region TEXT NOT NULL,
    BedCapacity INTEGER NOT NULL
);

CREATE TABLE Patients (
    PatientID INTEGER PRIMARY KEY,
    FirstName TEXT NOT NULL,
    LastName TEXT NOT NULL,
    Email TEXT NOT NULL,
    DateOfBirth TEXT NOT NULL,
    Sex TEXT NOT NULL,
    City TEXT NOT NULL,
    StateCode TEXT NOT NULL
);

CREATE TABLE Doctors (
    DoctorID INTEGER PRIMARY KEY,
    DoctorName TEXT NOT NULL,
    Specialization TEXT NOT NULL,
    DoctorContact TEXT,
    FacilityID INTEGER NOT NULL,
    FOREIGN KEY (FacilityID) REFERENCES Facilities(FacilityID)
);

CREATE TABLE InsurancePlans (
    InsuranceID INTEGER PRIMARY KEY,
    PayerName TEXT NOT NULL,
    PlanName TEXT NOT NULL,
    PlanType TEXT NOT NULL,
    CoverageRate REAL NOT NULL
);

CREATE TABLE PatientCoverage (
    CoverageID INTEGER PRIMARY KEY AUTOINCREMENT,
    PatientID INTEGER NOT NULL,
    InsuranceID INTEGER NOT NULL,
    MemberNumber TEXT NOT NULL,
    GroupNumber TEXT NOT NULL,
    EffectiveDate TEXT NOT NULL,
    CoverageStatus TEXT NOT NULL,
    IsPrimary INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (PatientID) REFERENCES Patients(PatientID),
    FOREIGN KEY (InsuranceID) REFERENCES InsurancePlans(InsuranceID)
);

CREATE TABLE Appointments (
    AppointmentID INTEGER PRIMARY KEY,
    AppointmentDate TEXT NOT NULL,
    AppointmentTime TEXT NOT NULL,
    PatientID INTEGER NOT NULL,
    DoctorID INTEGER NOT NULL,
    FacilityID INTEGER NOT NULL,
    VisitType TEXT NOT NULL,
    AppointmentStatus TEXT NOT NULL,
    EncounterChannel TEXT NOT NULL,
    FOREIGN KEY (PatientID) REFERENCES Patients(PatientID),
    FOREIGN KEY (DoctorID) REFERENCES Doctors(DoctorID),
    FOREIGN KEY (FacilityID) REFERENCES Facilities(FacilityID)
);

CREATE TABLE MedicalProcedures (
    ProcedureRecordID INTEGER PRIMARY KEY,
    SourceProcedureID INTEGER,
    ProcedureName TEXT NOT NULL,
    AppointmentID INTEGER NOT NULL,
    ProcedureFamily TEXT NOT NULL,
    AcuityLevel TEXT NOT NULL,
    FOREIGN KEY (AppointmentID) REFERENCES Appointments(AppointmentID)
);

CREATE TABLE Medications (
    MedicationID INTEGER PRIMARY KEY,
    MedicationName TEXT NOT NULL,
    Category TEXT NOT NULL,
    Form TEXT NOT NULL,
    UnitCost INTEGER NOT NULL
);

CREATE TABLE Prescriptions (
    PrescriptionID INTEGER PRIMARY KEY,
    AppointmentID INTEGER NOT NULL,
    PatientID INTEGER NOT NULL,
    DoctorID INTEGER NOT NULL,
    MedicationID INTEGER NOT NULL,
    Dosage TEXT NOT NULL,
    Frequency TEXT NOT NULL,
    DurationDays INTEGER NOT NULL,
    StartDate TEXT NOT NULL,
    EndDate TEXT NOT NULL,
    PrescriptionStatus TEXT NOT NULL,
    FOREIGN KEY (AppointmentID) REFERENCES Appointments(AppointmentID),
    FOREIGN KEY (PatientID) REFERENCES Patients(PatientID),
    FOREIGN KEY (DoctorID) REFERENCES Doctors(DoctorID),
    FOREIGN KEY (MedicationID) REFERENCES Medications(MedicationID)
);

CREATE TABLE LabResults (
    LabResultID INTEGER PRIMARY KEY,
    AppointmentID INTEGER NOT NULL,
    PatientID INTEGER NOT NULL,
    FacilityID INTEGER NOT NULL,
    TestName TEXT NOT NULL,
    Category TEXT NOT NULL,
    ResultValue REAL NOT NULL,
    Unit TEXT NOT NULL,
    ReferenceRange TEXT NOT NULL,
    ResultFlag TEXT NOT NULL,
    CollectedAt TEXT NOT NULL,
    ResultStatus TEXT NOT NULL,
    FOREIGN KEY (AppointmentID) REFERENCES Appointments(AppointmentID),
    FOREIGN KEY (PatientID) REFERENCES Patients(PatientID),
    FOREIGN KEY (FacilityID) REFERENCES Facilities(FacilityID)
);

CREATE TABLE Invoices (
    InvoiceID TEXT PRIMARY KEY,
    AppointmentID INTEGER NOT NULL,
    PatientID INTEGER NOT NULL,
    InsuranceID INTEGER NOT NULL,
    FacilityID INTEGER NOT NULL,
    BillingStatus TEXT NOT NULL,
    TotalCharge INTEGER NOT NULL,
    InsuranceCovered INTEGER NOT NULL,
    PatientResponsibility INTEGER NOT NULL,
    IssuedAt TEXT NOT NULL,
    PaidAt TEXT,
    FOREIGN KEY (AppointmentID) REFERENCES Appointments(AppointmentID),
    FOREIGN KEY (PatientID) REFERENCES Patients(PatientID),
    FOREIGN KEY (InsuranceID) REFERENCES InsurancePlans(InsuranceID),
    FOREIGN KEY (FacilityID) REFERENCES Facilities(FacilityID)
);

CREATE TABLE InvoiceLineItems (
    LineItemID INTEGER PRIMARY KEY,
    InvoiceID TEXT NOT NULL,
    ProcedureRecordID INTEGER,
    ChargeCategory TEXT NOT NULL,
    ChargeDescription TEXT NOT NULL,
    Amount INTEGER NOT NULL,
    FOREIGN KEY (InvoiceID) REFERENCES Invoices(InvoiceID),
    FOREIGN KEY (ProcedureRecordID) REFERENCES MedicalProcedures(ProcedureRecordID)
);

CREATE INDEX idx_appointments_date ON Appointments(AppointmentDate);
CREATE INDEX idx_appointments_facility ON Appointments(FacilityID);
CREATE INDEX idx_labresults_flag ON LabResults(ResultFlag);
CREATE INDEX idx_invoices_issuedat ON Invoices(IssuedAt);
