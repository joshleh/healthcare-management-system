const state = {
  facility: "all",
  specialty: "all",
  patientId: "",
  referenceDate: "",
};

const DEMO_SCENARIOS = {
  cardiology: {
    label: "Cardiology follow-up",
    values: {
      firstName: "Taylor",
      lastName: "Mills",
      email: "taylor.mills@demo.local",
      dateOfBirth: "1987-04-17",
      sex: "Female",
      city: "San Francisco",
      stateCode: "CA",
      facilityId: "1",
      specialty: "Cardiology",
      visitType: "Chronic Care Review",
      appointmentOffsetDays: 2,
      appointmentTime: "08:30",
      status: "Confirmed",
      procedureName: "Cardiac follow-up evaluation",
      insuranceId: "1",
      billAmount: "12500",
      medicationId: "2",
      labFlag: "Attention",
      labTestName: "BNP",
    },
  },
  oncology: {
    label: "Oncology infusion review",
    values: {
      firstName: "Ariana",
      lastName: "Cole",
      email: "ariana.cole@demo.local",
      dateOfBirth: "1979-09-22",
      sex: "Female",
      city: "San Jose",
      stateCode: "CA",
      facilityId: "3",
      specialty: "Oncologist",
      visitType: "Procedure Follow-up",
      appointmentOffsetDays: 1,
      appointmentTime: "10:15",
      status: "Completed",
      procedureName: "Infusion therapy reassessment",
      insuranceId: "4",
      billAmount: "28400",
      medicationId: "4",
      labFlag: "Critical",
      labTestName: "Hemoglobin",
    },
  },
  "womens-health": {
    label: "Women's imaging pathway",
    values: {
      firstName: "Naomi",
      lastName: "Chen",
      email: "naomi.chen@demo.local",
      dateOfBirth: "1992-11-08",
      sex: "Female",
      city: "Oakland",
      stateCode: "CA",
      facilityId: "2",
      specialty: "Radiology",
      visitType: "Procedure Follow-up",
      appointmentOffsetDays: 4,
      appointmentTime: "13:45",
      status: "Scheduled",
      procedureName: "Diagnostic imaging follow-up",
      insuranceId: "5",
      billAmount: "4600",
      medicationId: "12",
      labFlag: "None",
      labTestName: "Basic Metabolic Panel",
    },
  },
};

const elements = {
  facilityFilter: document.querySelector("#facility-filter"),
  specialtyFilter: document.querySelector("#specialty-filter"),
  patientSearch: document.querySelector("#patient-search"),
  patientResults: document.querySelector("#patient-results"),
  featuredPatients: document.querySelector("#featured-patients"),
  resetFilters: document.querySelector("#reset-filters"),
  sidebarReset: document.querySelector("#sidebar-reset"),
  adminForm: document.querySelector("#admin-form"),
  adminFeedback: document.querySelector("#admin-feedback"),
  adminFacility: document.querySelector("#admin-facility"),
  adminSpecialty: document.querySelector("#admin-specialty"),
  adminInsurance: document.querySelector("#admin-insurance"),
  adminMedication: document.querySelector("#admin-medication"),
  adminScenarios: document.querySelector("#admin-scenarios"),
};

init();

async function init() {
  try {
    const options = await fetchJson("/api/options");
    hydrateFilters(options);
    hydrateFeaturedPatients(options.featuredPatients);
    if (options.featuredPatients[0]) {
      state.patientId = String(options.featuredPatients[0].id);
    }
    state.referenceDate = options.referenceDate;
    document.querySelector("#reference-date").textContent = formatDate(options.referenceDate);
    const appointmentDateField = elements.adminForm.querySelector('input[name="appointmentDate"]');
    appointmentDateField.value = options.referenceDate;
    bindEvents();
    await loadDashboard();
  } catch (error) {
    renderFatal(error);
  }
}

function hydrateFilters(options) {
  const currentFilterFacility = state.facility;
  const currentFilterSpecialty = state.specialty;
  const currentAdminFacility = elements.adminFacility.value;
  const currentAdminSpecialty = elements.adminSpecialty.value;
  const currentAdminInsurance = elements.adminInsurance.value;
  const currentAdminMedication = elements.adminMedication.value;

  elements.facilityFilter.innerHTML = '<option value="all">All facilities</option>';
  elements.specialtyFilter.innerHTML = '<option value="all">All specialties</option>';
  elements.adminFacility.innerHTML = "";
  elements.adminSpecialty.innerHTML = "";
  elements.adminInsurance.innerHTML = "";
  elements.adminMedication.innerHTML = '<option value="">None</option>';

  options.facilities.forEach((facility) => {
    elements.facilityFilter.append(new Option(facility.name, String(facility.id)));
    elements.adminFacility.append(new Option(facility.name, String(facility.id)));
  });

  options.specialties.forEach((specialty) => {
    elements.specialtyFilter.append(new Option(specialty.name, specialty.name));
    elements.adminSpecialty.append(new Option(specialty.name, specialty.name));
  });

  options.insurancePlans.forEach((plan) => {
    elements.adminInsurance.append(new Option(`${plan.payer} • ${plan.plan}`, String(plan.id)));
  });

  options.medications.forEach((medication) => {
    elements.adminMedication.append(new Option(`${medication.name} • ${medication.category}`, String(medication.id)));
  });

  elements.facilityFilter.value = currentFilterFacility || "all";
  elements.specialtyFilter.value = currentFilterSpecialty || "all";

  if (currentAdminFacility) {
    elements.adminFacility.value = currentAdminFacility;
  }
  if (currentAdminSpecialty) {
    elements.adminSpecialty.value = currentAdminSpecialty;
  }
  if (currentAdminInsurance) {
    elements.adminInsurance.value = currentAdminInsurance;
  }
  if (currentAdminMedication) {
    elements.adminMedication.value = currentAdminMedication;
  }
}

function hydrateFeaturedPatients(patients) {
  elements.featuredPatients.innerHTML = patients
    .map(
      (patient) => `
        <button data-patient-id="${patient.id}" type="button">
          ${patient.name}
        </button>
      `
    )
    .join("");
}

function bindEvents() {
  elements.facilityFilter.addEventListener("change", async (event) => {
    state.facility = event.target.value;
    await loadDashboard();
  });

  elements.specialtyFilter.addEventListener("change", async (event) => {
    state.specialty = event.target.value;
    await loadDashboard();
  });

  let searchTimer;
  elements.patientSearch.addEventListener("input", () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(runPatientSearch, 180);
  });

  elements.resetFilters.addEventListener("click", async () => {
    await resetDashboardFilters();
  });

  elements.sidebarReset.addEventListener("click", async () => {
    await resetDashboardFilters();
  });

  elements.adminForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitAdminForm();
  });

  elements.adminScenarios.addEventListener("click", (event) => {
    const button = event.target.closest("[data-scenario]");
    if (!button) {
      return;
    }

    applyScenario(button.dataset.scenario);
  });

  document.addEventListener("click", (event) => {
    const patientButton = event.target.closest("[data-patient-id]");
    if (patientButton) {
      state.patientId = patientButton.dataset.patientId;
      elements.patientResults.classList.remove("visible");
      loadDashboard();
      return;
    }

    if (!event.target.closest(".search-field")) {
      elements.patientResults.classList.remove("visible");
    }
  });
}

async function loadDashboard() {
  const query = toQuery({
    facility: state.facility,
    specialty: state.specialty,
  });

  const patientQuery = toQuery({
    patient_id: state.patientId,
  });

  const [overview, revenue, departments, payerMix, schedule, labs, journey] = await Promise.all([
    fetchJson(`/api/overview?${query}`),
    fetchJson(`/api/revenue-trend?${query}`),
    fetchJson(`/api/department-load?${query}`),
    fetchJson(`/api/payer-mix?${query}`),
    fetchJson(`/api/schedule?${query}`),
    fetchJson(`/api/lab-alerts?${query}`),
    fetchJson(`/api/patient-journey?${patientQuery}`),
  ]);

  renderOverview(overview);
  renderRevenueChart(revenue.points);
  renderDepartmentChart(departments.rows);
  renderPayerMix(payerMix.rows);
  renderSchedule(schedule.rows);
  renderLabAlerts(labs.rows);
  renderPatientJourney(journey);
}

async function resetDashboardFilters() {
  state.facility = "all";
  state.specialty = "all";
  elements.facilityFilter.value = "all";
  elements.specialtyFilter.value = "all";
  elements.patientSearch.value = "";
  elements.patientResults.classList.remove("visible");
  await loadDashboard();
}

async function submitAdminForm() {
  const formData = new FormData(elements.adminForm);
  const payload = Object.fromEntries(formData.entries());
  elements.adminFeedback.textContent = "Creating demo encounter...";

  try {
    const result = await postJson("/api/admin/encounter", payload);
    state.patientId = String(result.patientId);
    elements.adminFeedback.textContent = result.message;
    await refreshOptionsAndDashboard();
    elements.patientSearch.value = result.patientName;
  } catch (error) {
    elements.adminFeedback.textContent = error.message;
  }
}

async function refreshOptionsAndDashboard() {
  const options = await fetchJson("/api/options");
  state.referenceDate = options.referenceDate;
  hydrateFilters(options);
  hydrateFeaturedPatients(options.featuredPatients);
  await loadDashboard();
}

function applyScenario(key) {
  const scenario = DEMO_SCENARIOS[key];
  if (!scenario) {
    return;
  }

  const values = { ...scenario.values };
  values.appointmentDate = scenarioDate(values.appointmentOffsetDays ?? 0);
  delete values.appointmentOffsetDays;

  Object.entries(values).forEach(([fieldName, value]) => {
    const field = elements.adminForm.elements.namedItem(fieldName);
    if (!field) {
      return;
    }

    field.value = value;
  });

  elements.adminFeedback.textContent = `${scenario.label} loaded. Review the fields, then create the encounter.`;
}

async function runPatientSearch() {
  const queryValue = elements.patientSearch.value.trim();
  const payload = await fetchJson(`/api/patients?${toQuery({ query: queryValue })}`);
  renderPatientResults(payload.rows);
}

function renderPatientResults(rows) {
  if (!rows.length) {
    elements.patientResults.innerHTML = '<div class="empty-state">No patients matched that search.</div>';
    elements.patientResults.classList.add("visible");
    return;
  }

  elements.patientResults.innerHTML = rows
    .map(
      (row) => `
        <button data-patient-id="${row.id}" type="button">
          <strong>${row.name}</strong>
          <small>${row.email}</small>
        </button>
      `
    )
    .join("");
  elements.patientResults.classList.add("visible");
}

function renderOverview(payload) {
  const metrics = payload.metrics;
  document.querySelector("#metric-appointments").textContent = formatNumber(metrics.totalAppointments || 0);
  document.querySelector("#metric-scheduled").textContent =
    `${formatNumber(metrics.scheduledVisits || 0)} scheduled • ${formatNumber(metrics.completedVisits || 0)} completed`;
  document.querySelector("#metric-revenue").textContent = formatCurrencyCompact(metrics.grossRevenue || 0);
  document.querySelector("#metric-invoice").textContent =
    `${formatCurrency(metrics.grossRevenue || 0)} exact gross revenue`;
  document.querySelector("#metric-coverage").textContent = formatPercent(metrics.coverageRate || 0);
  document.querySelector("#metric-alerts").textContent = formatNumber(metrics.abnormalLabs || 0);

  const highlight = payload.highlight;
  document.querySelector("#metric-highlight").textContent = highlight.facility
    ? `${highlight.facility} leads with ${formatCurrency(highlight.revenue || 0)}`
    : "No facility highlight available";
}

function renderRevenueChart(points) {
  const host = document.querySelector("#revenue-chart");
  if (!points.length) {
    host.innerHTML = renderEmptyState(
      "No revenue in this slice",
      "Try All Facilities or switch specialties to move back to a populated view.",
      "Reset filters"
    );
    return;
  }

  const width = 760;
  const height = 260;
  const padding = { top: 18, right: 16, bottom: 36, left: 16 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const maxValue = Math.max(...points.map((point) => point.revenue));
  const step = innerWidth / Math.max(points.length - 1, 1);

  const graphPoints = points.map((point, index) => {
    const x = padding.left + step * index;
    const y = padding.top + innerHeight - (point.revenue / maxValue) * innerHeight;
    return { ...point, x, y };
  });

  const linePath = graphPoints.map((point, index) => `${index ? "L" : "M"} ${point.x} ${point.y}`).join(" ");
  const areaPath = `${linePath} L ${padding.left + innerWidth} ${padding.top + innerHeight} L ${padding.left} ${padding.top + innerHeight} Z`;

  host.innerHTML = `
    <svg class="svg-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Monthly revenue trend">
      <line class="line-axis" x1="${padding.left}" y1="${padding.top + innerHeight}" x2="${padding.left + innerWidth}" y2="${padding.top + innerHeight}"></line>
      <line class="grid-line" x1="${padding.left}" y1="${padding.top}" x2="${padding.left + innerWidth}" y2="${padding.top}"></line>
      <path class="line-area" d="${areaPath}"></path>
      <path class="line-path" d="${linePath}"></path>
      ${graphPoints
        .filter((point) => point.revenue === maxValue)
        .map(
          (point) => `
            <circle cx="${point.x}" cy="${point.y}" r="5" fill="#0f766e"></circle>
            <text class="value-tag" x="${point.x + 8}" y="${point.y - 10}">${formatCurrencyShort(point.revenue)}</text>
          `
        )
        .join("")}
      ${graphPoints
        .filter((_, index) => index % Math.ceil(points.length / 6) === 0 || index === points.length - 1)
        .map(
          (point) => `
            <text class="tick" x="${point.x}" y="${height - 10}" text-anchor="middle">${point.period}</text>
          `
        )
        .join("")}
    </svg>
  `;
}

function renderDepartmentChart(rows) {
  const host = document.querySelector("#department-chart");
  if (!rows.length) {
    host.innerHTML = renderEmptyState(
      "No department activity",
      "This filter combination does not include visits for a ranked specialty view.",
      "Reset filters"
    );
    return;
  }

  const width = 420;
  const rowHeight = 26;
  const gap = 12;
  const labelWidth = 155;
  const height = rows.length * (rowHeight + gap) + 10;
  const maxValue = Math.max(...rows.map((row) => row.visits));

  host.innerHTML = `
    <svg class="svg-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Department workload">
      ${rows
        .map((row, index) => {
          const y = index * (rowHeight + gap) + 6;
          const widthValue = ((width - labelWidth - 38) * row.visits) / maxValue;
          return `
            <text class="tick" x="0" y="${y + 18}">${truncate(row.specialty, 22)}</text>
            <rect class="bar-fill" x="${labelWidth}" y="${y}" width="${widthValue}" height="${rowHeight}" rx="10"></rect>
            <text class="value-tag" x="${labelWidth + widthValue + 8}" y="${y + 18}">${row.visits}</text>
          `;
        })
        .join("")}
    </svg>
  `;
}

function renderPayerMix(rows) {
  const host = document.querySelector("#payer-mix");
  if (!rows.length) {
    host.innerHTML = renderEmptyState(
      "No payer mix available",
      "There are no invoices for the current slice, so payer distribution is unavailable here.",
      "Reset filters"
    );
    return;
  }

  const maxRevenue = Math.max(...rows.map((row) => row.revenue));
  host.innerHTML = rows
    .map(
      (row) => `
        <div class="payer-row">
          <header>
            <strong>${row.payer}</strong>
            <span title="${formatCurrency(row.revenue)}">${formatCurrencyCompact(row.revenue)}</span>
          </header>
          <div class="payer-track">
            <div class="payer-fill" style="width:${(row.revenue / maxRevenue) * 100}%"></div>
          </div>
          <small>${row.invoices} invoices</small>
        </div>
      `
    )
    .join("");
}

function renderSchedule(rows) {
  const host = document.querySelector("#schedule-table");
  if (!rows.length) {
    host.innerHTML = `
      <tr>
        <td colspan="6">
          ${renderEmptyState(
            "No appointments match this view",
            "Widen the facility or specialty filters to bring appointments back into the operating window.",
            "Reset filters"
          )}
        </td>
      </tr>
    `;
    return;
  }

  host.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td>${formatDate(row.date)}<br /><small>${row.time}</small></td>
          <td>${row.patient}</td>
          <td>${row.doctor}<br /><small>${row.specialty}</small></td>
          <td>${row.visitType}</td>
          <td><span class="status-pill ${statusClass(row.status)}">${row.status}</span></td>
          <td>${row.facility}</td>
        </tr>
      `
    )
    .join("");
}

function renderLabAlerts(rows) {
  const host = document.querySelector("#lab-alerts");
  if (!rows.length) {
    host.innerHTML = renderEmptyState(
      "No active lab escalations",
      "That can be a good sign. This slice currently has no attention or critical lab results.",
      "Reset filters"
    );
    return;
  }

  host.innerHTML = rows
    .map(
      (row) => `
        <article class="alert-item">
          <header>
            <strong>${row.testName}</strong>
            <span class="status-pill ${statusClass(row.flag)}">${row.flag}</span>
          </header>
          <p>${row.patient} • ${row.facility}</p>
          <small>${formatDateTime(row.collectedAt)} • ${row.value} ${row.unit}</small>
        </article>
      `
    )
    .join("");
}

function renderPatientJourney(payload) {
  const patient = payload.patient || {};
  const summary = payload.summary || {};

  document.querySelector("#patient-profile").innerHTML = patient.name
    ? `
        <strong>${patient.name}</strong>
        <p>${patient.sex} • ${patient.city}, ${patient.state}</p>
        <p>${patient.email}</p>
        <p>${patient.payer || "No payer"} • ${patient.planName || "No plan on file"}</p>
        <code>${patient.memberNumber || "Member number unavailable"}</code>
      `
    : renderEmptyState(
        "No patient selected",
        "Choose a featured patient or search by name to load a complete journey view.",
        "Load a featured patient"
      );

  document.querySelector("#patient-stat-appointments").textContent = formatNumber(summary.appointments || 0);
  document.querySelector("#patient-stat-procedures").textContent = formatNumber(summary.procedures || 0);
  document.querySelector("#patient-stat-billed").textContent = formatCurrency(summary.billed || 0);

  const timeline = document.querySelector("#patient-timeline");
  if (!payload.timeline || !payload.timeline.length) {
    timeline.innerHTML = renderEmptyState(
      "No journey events available",
      "This patient does not currently have timeline events in the seeded demo data.",
      "Load a featured patient"
    );
    return;
  }

  timeline.innerHTML = payload.timeline
    .map(
      (item) => `
        <article class="timeline-item">
          <header>
            <strong>${item.eventType}</strong>
            <span class="status-pill ${statusClass(item.status)}">${item.status}</span>
          </header>
          <strong>${item.title}</strong>
          <p>${item.detail}</p>
          <small>${formatDate(item.eventDate)}</small>
        </article>
      `
    )
    .join("");
}

function renderFatal(error) {
  document.body.innerHTML = `
    <main style="padding:2rem;font-family:Avenir Next,Segoe UI,sans-serif;">
      <h1>App failed to load</h1>
      <p>${error.message}</p>
    </main>
  `;
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed for ${url} with status ${response.status}`);
  }
  return response.json();
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed for ${url} with status ${response.status}`);
  }
  return data;
}

function toQuery(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) {
      query.set(key, value);
    }
  });
  return query.toString();
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatCurrencyShort(value) {
  if (value >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  return formatCurrency(value);
}

function formatCurrencyCompact(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: value >= 100000 ? "compact" : "standard",
    maximumFractionDigits: value >= 100000 ? 1 : 0,
  }).format(value);
}

function formatPercent(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function formatDate(value) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatDateTime(value) {
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function scenarioDate(offsetDays) {
  const baseDate = state.referenceDate || new Date().toISOString().slice(0, 10);
  const date = new Date(`${baseDate}T00:00:00`);
  date.setDate(date.getDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

function truncate(value, size) {
  return value.length > size ? `${value.slice(0, size - 1)}…` : value;
}

function statusClass(value = "") {
  return `status-${String(value).toLowerCase().replace(/\s+/g, "-")}`;
}

function renderEmptyState(title, body, actionLabel) {
  return `
    <div class="empty-state">
      <strong>${title}</strong>
      <p>${body}</p>
      <button class="ghost-button" type="button" data-empty-action="${actionLabel === "Load a featured patient" ? "featured" : "reset"}">
        ${actionLabel}
      </button>
    </div>
  `;
}

document.addEventListener("click", async (event) => {
  const action = event.target.closest("[data-empty-action]");
  if (!action) {
    return;
  }

  if (action.dataset.emptyAction === "reset") {
    elements.resetFilters.click();
    return;
  }

  const featured = elements.featuredPatients.querySelector("[data-patient-id]");
  if (featured) {
    featured.click();
  }
});
