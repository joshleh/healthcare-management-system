
-- 1. Lists all appointments for a specific patient
-- Joins Appointments with Doctors to show detailed visit info
SELECT 
    a.AppointmentID, 
    a.Date, 
    a.Time,
    d.DoctorName, 
    d.Specialization
FROM Appointments a
JOIN Doctors d ON a.DoctorID = d.DoctorID
WHERE a.PatientID = 109
ORDER BY a.Date, a.Time;

-- 2. Obtains daily appointment count
-- Useful for daily workload tracking
SELECT 
    Date,
    COUNT(*) AS TotalAppointments
FROM Appointments
GROUP BY Date
ORDER BY Date;

-- 3. Showcases most active doctors by number of appointments
SELECT 
    d.DoctorName,
    d.Specialization,
    COUNT(*) AS TotalAppointments
FROM Appointments a
JOIN Doctors d ON a.DoctorID = d.DoctorID
GROUP BY d.DoctorName, d.Specialization
ORDER BY TotalAppointments DESC
LIMIT 5;

-- 4. Shows total billing per patient
-- Combines patient names with total charges
SELECT 
    TRIM(p.firstname || ' ' || p.lastname) AS PatientName,
    SUM(b.Amount) AS TotalBilled
FROM Billing b
JOIN Patients p ON b.PatientID = p.PatientID
GROUP BY p.PatientID, PatientName
ORDER BY TotalBilled DESC;

-- 5. Shows most common medical procedures
SELECT 
    ProcedureName,
    COUNT(*) AS TimesPerformed
FROM MedicalProcedures
GROUP BY ProcedureName
ORDER BY TimesPerformed DESC
LIMIT 10;

-- 6. Provides upcoming appointments (future dates only)
-- Joins Patients and Doctors for full context
SELECT 
    a.AppointmentID, 
    a.Date, 
    a.Time,
    TRIM(p.firstname || ' ' || p.lastname) AS PatientName,
    d.DoctorName
FROM Appointments a
JOIN Patients p ON a.PatientID = p.PatientID
JOIN Doctors d ON a.DoctorID = d.DoctorID
WHERE a.Date >= CURRENT_DATE
ORDER BY a.Date, a.Time;

-- 7. Provides patients who've seen more than one doctor
SELECT 
    p.PatientID,
    TRIM(p.firstname || ' ' || p.lastname) AS PatientName,
    COUNT(DISTINCT a.DoctorID) AS DoctorCount
FROM Appointments a
JOIN Patients p ON a.PatientID = p.PatientID
GROUP BY p.PatientID, PatientName
HAVING COUNT(DISTINCT a.DoctorID) > 1;

-- 8. Shows doctor billing performance
-- Revenue associated with doctors via patient billing
SELECT 
    d.DoctorName,
    SUM(b.Amount) AS TotalRevenue
FROM Appointments a
JOIN Doctors d ON a.DoctorID = d.DoctorID
JOIN Billing b ON a.PatientID = b.PatientID
GROUP BY d.DoctorName
ORDER BY TotalRevenue DESC;

-- 9. Shows unusual billing items
-- Useful for outlier detection or audits
SELECT *
FROM Billing
WHERE Amount > 1000
ORDER BY Amount DESC;

-- 10. Showcases billing by procedure and appointment date
-- Combines procedures, appointments, and billing
SELECT 
    mp.ProcedureName,
    a.Date,
    SUM(b.Amount) AS TotalCharged
FROM MedicalProcedures mp
JOIN Appointments a ON mp.AppointmentID = a.AppointmentID
JOIN Billing b ON a.PatientID = b.PatientID
GROUP BY mp.ProcedureName, a.Date
ORDER BY TotalCharged DESC;
