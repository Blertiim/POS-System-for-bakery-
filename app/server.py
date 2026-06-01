from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import json
import mimetypes

from .database import ROOT_DIR, initialize_database
from .repositories import (
    AppError,
    create_category,
    create_product,
    create_sale,
    daily_report,
    delete_category,
    delete_product,
    delete_sale,
    get_sale,
    list_categories,
    list_products,
    list_sales,
    receipt_text,
    update_category,
    update_product,
    update_sale,
)


STATIC_DIR = ROOT_DIR / "static"


class POSRequestHandler(BaseHTTPRequestHandler):
    server_version = "BakeryPOS/1.0"

    def do_GET(self) -> None:
        self.route_request()

    def do_POST(self) -> None:
        self.route_request()

    def do_PUT(self) -> None:
        self.route_request()

    def do_DELETE(self) -> None:
        self.route_request()

    def log_message(self, format: str, *args: object) -> None:
        return

    def route_request(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api(parsed)
            return
        self.serve_static(parsed.path)

    def handle_api(self, parsed) -> None:
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        method = self.command

        try:
            if path == "/api/health" and method == "GET":
                self.send_json({"status": "ok"})
                return

            if path == "/api/categories":
                if method == "GET":
                    include_inactive = query.get("include_inactive", ["0"])[0] == "1"
                    self.send_json(list_categories(include_inactive=include_inactive))
                    return
                if method == "POST":
                    self.send_json(create_category(self.read_json()), status=201)
                    return

            if path.startswith("/api/categories/"):
                category_id = self.parse_id(path, "/api/categories/")
                if method == "PUT":
                    self.send_json(update_category(category_id, self.read_json()))
                    return
                if method == "DELETE":
                    self.send_json(delete_category(category_id))
                    return

            if path == "/api/products":
                if method == "GET":
                    include_inactive = query.get("include_inactive", ["0"])[0] == "1"
                    search = query.get("search", [""])[0].strip()
                    category_value = query.get("category_id", [""])[0]
                    category_id = int(category_value) if category_value else None
                    self.send_json(
                        list_products(
                            search=search,
                            category_id=category_id,
                            include_inactive=include_inactive,
                        )
                    )
                    return
                if method == "POST":
                    self.send_json(create_product(self.read_json()), status=201)
                    return

            if path.startswith("/api/products/"):
                product_id = self.parse_id(path, "/api/products/")
                if method == "PUT":
                    self.send_json(update_product(product_id, self.read_json()))
                    return
                if method == "DELETE":
                    self.send_json(delete_product(product_id))
                    return

            if path == "/api/sales":
                if method == "GET":
                    date_text = query.get("date", [None])[0]
                    self.send_json(list_sales(date_text=date_text))
                    return
                if method == "POST":
                    self.send_json(create_sale(self.read_json()), status=201)
                    return

            if path.startswith("/api/sales/"):
                sale_id = self.parse_id(path, "/api/sales/")
                if method == "GET":
                    self.send_json(get_sale(sale_id))
                    return
                if method == "PUT":
                    self.send_json(update_sale(sale_id, self.read_json()))
                    return
                if method == "DELETE":
                    self.send_json(delete_sale(sale_id))
                    return

            if path == "/api/reports/daily" and method == "GET":
                date_text = query.get("date", [""])[0]
                if not date_text:
                    self.send_json({"error": "Data është e detyrueshme."}, status=400)
                    return
                self.send_json(daily_report(date_text))
                return

            if path.startswith("/api/receipts/") and path.endswith(".txt") and method == "GET":
                receipt_id = path.removeprefix("/api/receipts/").removesuffix(".txt")
                text = receipt_text(int(receipt_id))
                self.send_text(text, content_type="text/plain; charset=utf-8")
                return

            self.send_json({"error": "Rruga nuk u gjet."}, status=404)
        except AppError as exc:
            self.send_json({"error": str(exc)}, status=exc.status_code)
        except ValueError:
            self.send_json({"error": "Kërkesa nuk është e vlefshme."}, status=400)
        except Exception as exc:
            self.send_json({"error": f"Gabim në server: {exc}"}, status=500)

    def parse_id(self, path: str, prefix: str) -> int:
        value = path.removeprefix(prefix)
        if "/" in value or not value:
            raise ValueError("Invalid id")
        return int(value)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length == 0:
            return {}
        payload = self.rfile.read(length).decode("utf-8")
        return json.loads(payload)

    def send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, body_text: str, content_type: str = "text/plain") -> None:
        body = body_text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_static(self, request_path: str) -> None:
        if request_path in ("", "/"):
            request_path = "/index.html"
        relative_path = unquote(request_path).lstrip("/")
        target = (STATIC_DIR / relative_path).resolve()
        static_root = STATIC_DIR.resolve()
        try:
            target.relative_to(static_root)
        except ValueError:
            self.send_error(403)
            return
        if not target.exists() or not target.is_file():
            target = STATIC_DIR / "index.html"
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if target.suffix == ".js":
            content_type = "text/javascript"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    initialize_database()
    server = ThreadingHTTPServer((host, port), POSRequestHandler)
    print(f"Bakery POS running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
