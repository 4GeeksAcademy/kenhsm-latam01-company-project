#!/usr/bin/env python3
"""Small standard-library API for incident analysis."""

from __future__ import annotations

import argparse
import json
import sys
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from incident_analysis import AnalysisResult, analyze_csv_text, export_metrics  # noqa: E402


class AnalysisStore:
    def __init__(self) -> None:
        self._result: AnalysisResult | None = None
        self._csv: str | None = None
        self._lock = Lock()

    def save(self, result: AnalysisResult) -> None:
        with self._lock:
            self._result = result
            self._csv = export_metrics(result)

    def result(self) -> AnalysisResult | None:
        with self._lock:
            return self._result

    def csv(self) -> str | None:
        with self._lock:
            return self._csv


store = AnalysisStore()


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "BrasalandAdminAPI/1.0"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._headers()
        self.end_headers()

    def do_POST(self) -> None:
        if self.path != "/api/incidents/analyze":
            self._json_error(HTTPStatus.NOT_FOUND, "Ruta no encontrada.")
            return
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            self._json_error(HTTPStatus.BAD_REQUEST, "El fichero debe enviarse como multipart/form-data.")
            return
        try:
            csv_text = self._read_uploaded_csv(content_type)
            result = analyze_csv_text(csv_text)
        except ValueError as error:
            self._json_error(HTTPStatus.BAD_REQUEST, str(error))
            return
        except (OSError, UnicodeError) as error:
            self._json_error(HTTPStatus.BAD_REQUEST, f"No se pudo leer el fichero: {error}")
            return
        store.save(result)
        self._json(HTTPStatus.OK, result.to_dict())

    def do_GET(self) -> None:
        if self.path != "/api/incidents/results/export":
            self._json_error(HTTPStatus.NOT_FOUND, "Ruta no encontrada.")
            return
        csv_result = store.csv()
        if csv_result is None:
            self._json_error(HTTPStatus.NOT_FOUND, "Todavía no existe un análisis para exportar.")
            return
        body = csv_result.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self._headers()
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="results.csv"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_uploaded_csv(self, content_type: str) -> str:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValueError("El fichero está vacío.")
        body = self.rfile.read(length)
        message = BytesParser(policy=default).parsebytes(
            b"MIME-Version: 1.0\r\nContent-Type: " + content_type.encode() + b"\r\n\r\n" + body
        )
        parts = [part for part in message.walk() if part.get_content_disposition() == "form-data"]
        upload = next((part for part in parts if part.get_filename() or part.get_payload(decode=True)), None)
        if upload is None:
            raise ValueError("No se encontró ningún fichero en la carga.")
        data = upload.get_payload(decode=True) or b""
        if not data.strip():
            raise ValueError("El fichero está vacío.")
        return data.decode("utf-8-sig")

    def _json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_error(self, status: HTTPStatus, message: str) -> None:
        self._json(status, {"error": message})

    def _headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format: str, *args: object) -> None:
        print(f"[admin-api] {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inicia la API de análisis de incidencias.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), ApiHandler)
    print(f"Brasaland Admin API disponible en http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAPI detenida.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
