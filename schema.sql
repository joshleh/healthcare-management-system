-- Patients Table
CREATE TABLE Patients (
    PatientID INT PRIMARY KEY,
    firstname VARCHAR(100),
    lastname VARCHAR(100),
    email VARCHAR(255)
);

-- Doctors Table
CREATE TABLE Doctors (
    DoctorID INT PRIMARY KEY,
    DoctorName VARCHAR(150),
    Specialization VARCHAR(100),
    DoctorContact VARCHAR(150)
);

-- Appointments Table
CREATE TABLE Appointments (
    AppointmentID INT PRIMARY KEY,
    Date DATE,
    Time TIME,
    PatientID INT,
    DoctorID INT,
    FOREIGN KEY (PatientID) REFERENCES Patients(PatientID),
    FOREIGN KEY (DoctorID) REFERENCES Doctors(DoctorID)
);

-- Medical Procedures Table
CREATE TABLE MedicalProcedures (
    ProcedureID INT PRIMARY KEY,
    ProcedureName VARCHAR(200),
    AppointmentID INT,
    FOREIGN KEY (AppointmentID) REFERENCES Appointments(AppointmentID)
);

-- Billing Table
CREATE TABLE Billing (
    InvoiceID VARCHAR(50) PRIMARY KEY,
    PatientID INT,
    Items TEXT,
    Amount INT,
    FOREIGN KEY (PatientID) REFERENCES Patients(PatientID)
);
