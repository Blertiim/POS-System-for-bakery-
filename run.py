import argparse
import os

from app.server import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Bakery POS web application.")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", default=int(os.environ.get("PORT", "8000")), type=int)
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
