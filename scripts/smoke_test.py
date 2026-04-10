#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request


ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def fetch_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=10) as response:
        return int(response.status), json.loads(response.read().decode("utf-8"))


def wait_for_server(base_url: str, process: subprocess.Popen[str], timeout_seconds: int = 20) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"App server exited early.\n{output}".strip())

        try:
            status, _ = fetch_json(f"{base_url}/api/options")
            if status == 200:
                return
        except (error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(0.25)

    raise RuntimeError("Timed out waiting for the app server to accept requests.")


def stop_server(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    port = find_free_port()
    base_url = f"http://{HOST}:{port}"
    env = os.environ.copy()
    env["HOST"] = HOST
    env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(
        [sys.executable, "app.py", str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        wait_for_server(base_url, process)

        core_paths = [
            "/api/options",
            "/api/overview?facility=all&specialty=all",
            "/api/revenue-trend?facility=all&specialty=all",
            "/api/schedule?facility=all&specialty=all",
            "/api/lab-alerts?facility=all&specialty=all",
            "/api/patient-journey?patient_id=197",
        ]
        for path in core_paths:
            status, payload = fetch_json(f"{base_url}{path}")
            if status != 200:
                raise RuntimeError(f"{path} returned unexpected status {status}")
            if not isinstance(payload, dict):
                raise RuntimeError(f"{path} did not return a JSON object")

        demo_payload = {
            "firstName": "Smoke",
            "lastName": "Test",
            "email": "smoke.test@demo.local",
            "dateOfBirth": "1990-01-14",
            "sex": "Female",
            "city": "San Francisco",
            "stateCode": "CA",
            "facilityId": "1",
            "specialty": "Cardiology",
            "visitType": "Chronic Care Review",
            "appointmentDate": "2026-04-12",
            "appointmentTime": "09:00",
            "status": "Confirmed",
            "procedureName": "Cardiac follow-up evaluation",
            "insuranceId": "1",
            "billAmount": "9800",
            "medicationId": "2",
            "labFlag": "Attention",
            "labTestName": "BNP",
        }
        status, created = fetch_json(f"{base_url}/api/admin/encounter", method="POST", payload=demo_payload)
        if status != 201:
            raise RuntimeError(f"Admin encounter creation returned {status}")

        query = parse.quote("Smoke Test")
        status, search_payload = fetch_json(f"{base_url}/api/patients?query={query}")
        if status != 200:
            raise RuntimeError(f"Patient search returned {status}")

        rows = search_payload.get("rows", [])
        if not any(row.get("id") == created.get("patientId") for row in rows):
            raise RuntimeError("Created patient was not returned by patient search.")

        print("Smoke test passed.")
        print(f"Verified app on {base_url}")
        return 0
    finally:
        stop_server(process)


if __name__ == "__main__":
    raise SystemExit(main())
