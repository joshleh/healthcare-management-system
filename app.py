import streamlit as st
import pandas as pd

st.set_page_config(page_title="Healthcare SQL Dashboard", layout="wide")

st.title("🏥 Healthcare Management Dashboard")
st.markdown("Explore SQL-driven insights from your healthcare system")

# Sidebar
st.sidebar.title("Navigation")
query = st.sidebar.radio("Select a View", [
    "Appointments for Patient",
    "Daily Appointment Count",
    "Most Active Doctors",
    "Total Billing per Patient",
    "Most Common Procedures",
    "Upcoming Appointments",
    "Patients with Multiple Doctors",
    "Doctor Billing Performance",
    "Unusual Billing Items",
    "Billing by Procedure & Date"
])

# Load CSVs
data_dir = "data"
q1 = pd.read_csv(f"{data_dir}/query_1_appointments_for_patientID109.csv")
q2 = pd.read_csv(f"{data_dir}/query_2_daily_appointment_count.csv")
q3 = pd.read_csv(f"{data_dir}/query_3_most_active_doctors.csv")
q4 = pd.read_csv(f"{data_dir}/query_4_total_billing_per_patient.csv")
q5 = pd.read_csv(f"{data_dir}/query_5_most_common_medical_procedures.csv")
q6 = pd.read_csv(f"{data_dir}/query_6_upcoming_appointments.csv")
q7 = pd.read_csv(f"{data_dir}/query_7_patients_seen_multiple_doctors.csv")
q8 = pd.read_csv(f"{data_dir}/query_8_doctor_billing_performance.csv")
q9 = pd.read_csv(f"{data_dir}/query_9_unusual_billing_items.csv")
q10 = pd.read_csv(f"{data_dir}/query_10_billing_by_procedure_and_date.csv")

# Views
if query == "Appointments for Patient":
    st.subheader("Appointments for Patient ID 109")
    st.dataframe(q1)

elif query == "Daily Appointment Count":
    st.subheader("📅 Daily Appointments")
    st.line_chart(q2.set_index("Date"))

elif query == "Most Active Doctors":
    st.subheader("Top 5 Most Active Doctors")
    st.bar_chart(q3.set_index("DoctorName"))

elif query == "Total Billing per Patient":
    st.subheader("💰 Billing Summary")
    st.dataframe(q4)

elif query == "Most Common Procedures":
    st.subheader("Most Frequently Performed Procedures")
    st.bar_chart(q5.set_index("ProcedureName"))

elif query == "Upcoming Appointments":
    st.subheader("⏳ Upcoming Appointments")
    st.dataframe(q6)

elif query == "Patients with Multiple Doctors":
    st.subheader("Patients Who’ve Seen More Than One Doctor")
    st.dataframe(q7)

elif query == "Doctor Billing Performance":
    st.subheader("Doctor Billing Performance")
    st.bar_chart(q8.set_index("DoctorName"))

elif query == "Unusual Billing Items":
    st.subheader("Unusual Billing Items (> $1000)")
    st.dataframe(q9)

elif query == "Billing by Procedure & Date":
    st.subheader("Revenue by Procedure Over Time")
    st.line_chart(q10.pivot(index="Date", columns="ProcedureName", values="TotalCharged").fillna(0))
