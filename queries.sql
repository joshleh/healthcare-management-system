-- 1. Monthly revenue by facility
SELECT
    f.FacilityName,
    substr(i.IssuedAt, 1, 7) AS RevenueMonth,
    SUM(i.TotalCharge) AS GrossRevenue,
    SUM(i.PatientResponsibility) AS PatientBalance
FROM Invoices i
JOIN Facilities f ON f.FacilityID = i.FacilityID
GROUP BY f.FacilityName, RevenueMonth
ORDER BY RevenueMonth, GrossRevenue DESC;

-- 2. Upcoming schedule in the next 14 days by specialty
SELECT
    a.AppointmentDate,
    d.Specialization,
    COUNT(*) AS ScheduledVisits
FROM Appointments a
JOIN Doctors d ON d.DoctorID = a.DoctorID
WHERE a.AppointmentDate BETWEEN '2026-04-09' AND date('2026-04-09', '+14 day')
  AND a.AppointmentStatus IN ('Scheduled', 'Confirmed')
GROUP BY a.AppointmentDate, d.Specialization
ORDER BY a.AppointmentDate, ScheduledVisits DESC;

-- 3. Claim settlement rate by payer
SELECT
    ip.PayerName,
    COUNT(*) AS InvoiceCount,
    ROUND(100.0 * AVG(CASE WHEN i.BillingStatus = 'Settled' THEN 1 ELSE 0 END), 1) AS SettlementRatePct
FROM Invoices i
JOIN InsurancePlans ip ON ip.InsuranceID = i.InsuranceID
GROUP BY ip.PayerName
ORDER BY SettlementRatePct DESC;

-- 4. Critical and attention lab alerts by facility
SELECT
    f.FacilityName,
    lr.ResultFlag,
    COUNT(*) AS AlertCount
FROM LabResults lr
JOIN Facilities f ON f.FacilityID = lr.FacilityID
WHERE lr.ResultFlag IN ('Attention', 'Critical')
GROUP BY f.FacilityName, lr.ResultFlag
ORDER BY AlertCount DESC;

-- 5. Active medication utilization by category
SELECT
    m.Category,
    COUNT(*) AS ActivePrescriptions
FROM Prescriptions p
JOIN Medications m ON m.MedicationID = p.MedicationID
WHERE p.PrescriptionStatus IN ('Active', 'Planned')
GROUP BY m.Category
ORDER BY ActivePrescriptions DESC;

-- 6. Revenue contribution by procedure family
SELECT
    mp.ProcedureFamily,
    SUM(ili.Amount) AS Revenue
FROM InvoiceLineItems ili
JOIN MedicalProcedures mp ON mp.ProcedureRecordID = ili.ProcedureRecordID
GROUP BY mp.ProcedureFamily
ORDER BY Revenue DESC;

-- 7. Patients with multiple specialties visited
SELECT
    p.PatientID,
    p.FirstName || ' ' || p.LastName AS PatientName,
    COUNT(DISTINCT d.Specialization) AS SpecialtyCount
FROM Appointments a
JOIN Patients p ON p.PatientID = a.PatientID
JOIN Doctors d ON d.DoctorID = a.DoctorID
GROUP BY p.PatientID
HAVING COUNT(DISTINCT d.Specialization) > 2
ORDER BY SpecialtyCount DESC, PatientName;

-- 8. Highest billing specialists
SELECT
    d.Specialization,
    SUM(i.TotalCharge) AS GrossRevenue,
    COUNT(DISTINCT a.AppointmentID) AS VisitCount
FROM Invoices i
JOIN Appointments a ON a.AppointmentID = i.AppointmentID
JOIN Doctors d ON d.DoctorID = a.DoctorID
GROUP BY d.Specialization
ORDER BY GrossRevenue DESC
LIMIT 10;

-- 9. Facility care mix across appointments, labs, and medications
SELECT
    f.FacilityName,
    COUNT(DISTINCT a.AppointmentID) AS Visits,
    COUNT(DISTINCT lr.LabResultID) AS LabPanels,
    COUNT(DISTINCT p.PrescriptionID) AS Prescriptions
FROM Facilities f
LEFT JOIN Appointments a ON a.FacilityID = f.FacilityID
LEFT JOIN LabResults lr ON lr.FacilityID = f.FacilityID
LEFT JOIN Prescriptions p ON p.AppointmentID = a.AppointmentID
GROUP BY f.FacilityID
ORDER BY Visits DESC;

-- 10. Patient financial exposure after insurance
SELECT
    p.FirstName || ' ' || p.LastName AS PatientName,
    ip.PayerName,
    SUM(i.TotalCharge) AS GrossCharges,
    SUM(i.InsuranceCovered) AS InsuranceCovered,
    SUM(i.PatientResponsibility) AS PatientResponsibility
FROM Invoices i
JOIN Patients p ON p.PatientID = i.PatientID
JOIN InsurancePlans ip ON ip.InsuranceID = i.InsuranceID
GROUP BY p.PatientID
ORDER BY PatientResponsibility DESC
LIMIT 20;
