# Healthcare Management System

An interactive healthcare operations analytics demo built for portfolio presentation. The project now combines a normalized healthcare schema, seeded operational data, a zero-dependency Python backend, and a hospital-style frontend for exploring care delivery, billing, facilities, labs, medications, and patient journeys.

## What It Is Now

This is no longer just a SQL exercise or a CSV viewer. It is positioned as a lightweight hospital analytics product demo with:

- live API-backed filtering
- facility-aware scheduling and revenue views
- billing linked directly to appointments and procedures
- insurance coverage and patient financial exposure
- medications and prescription history
- lab result monitoring with abnormal alert views
- patient timeline inspection for care journey storytelling

## Demo Experience

The main experience is the interactive app served by `app.py`.

### Public link strategy

- Main portfolio button: `https://joshleh.github.io/healthcare-management-system/`
- Secondary interactive button: add later, after the static portfolio link is live

This repo is now set up for that split:

- GitHub Pages serves the `docs/` portfolio showcase
- The interactive Python dashboard remains ready for a second deployment later

### Run locally

```bash
python3 app.py
```

Then open:

```text
http://127.0.0.1:8000
```

The app uses only the Python standard library plus SQLite, so there is nothing to install to run the demo locally.

## Project Structure

- `app.py`: zero-dependency web server and JSON API
- `backend/bootstrap.py`: reproducible database seeding and synthetic healthcare enrichment
- `schema.sql`: upgraded relational schema with facilities, insurance, labs, medications, and invoices
- `queries.sql`: portfolio-style analytics queries against the richer model
- `data/`: source CSV files
- `web/`: hospital-themed frontend
- `docs/`: static fallback demo from the earlier pass
- `er_diagram.png`: original entity relationship diagram

## Data Model Upgrades

The project was expanded from the original patient / doctor / appointment / procedure / billing model into a more realistic hospital analytics shape:

- `Facilities`: operational sites and capacity context
- `InsurancePlans` and `PatientCoverage`: payer mix and coverage modeling
- `Appointments`: now linked to facilities and visit types
- `MedicalProcedures`: tied directly to encounters with acuity and family labels
- `Medications` and `Prescriptions`: treatment layer
- `LabResults`: diagnostic monitoring and alerting
- `Invoices` and `InvoiceLineItems`: billing normalized around appointments and procedures

## Portfolio Angle

The strongest framing for this project is:

**Healthcare operations analytics: schema design, reporting logic, and a clean lightweight reporting surface.**

That story is reflected in the interface:

- command-center overview metrics
- revenue cycle tracking
- department load analysis
- payer mix visibility
- lab escalation feed
- searchable patient journey timeline

## SQL Workflow

If you want to inspect the model and reporting layer directly:

1. Review `schema.sql`
2. Review `queries.sql`
3. Run `python3 app.py` to generate the SQLite demo database automatically in `runtime/`

## Hosting Notes

- Free to run locally: yes
- Fast to load: yes, because the app uses a small SQLite database and a lightweight frontend
- Public hosting setup included: yes, via GitHub Pages for `docs/` and Render for the interactive app

For a purely static fallback, the `docs/` folder can still be hosted on GitHub Pages.

## Deployment Setup Included

### GitHub Pages

The repository includes a GitHub Actions workflow that publishes `docs/` to GitHub Pages.

Expected URL:

```text
https://joshleh.github.io/healthcare-management-system/
```

### Interactive app later

The interactive Python dashboard is ready to deploy separately after the GitHub Pages portfolio link is in place.

For now, the priority is the static showcase:

- fast first impression
- zero cold starts
- clean portfolio URL

## Dataset Source

[Kaggle healthcare management system dataset](https://www.kaggle.com/datasets/anouskaabhisikta/healthcare-management-system)
