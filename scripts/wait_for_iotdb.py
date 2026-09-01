"""Wait until Apache IoTDB accepts Session API connections."""

from __future__ import annotations

import argparse
import time

from data_loader import IoTDBConfig, create_session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wait for IoTDB RPC readiness.")
    parser.add_argument("--host", default="iotdb")
    parser.add_argument("--port", default="6667")
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default="root")
    parser.add_argument("--timeout", type=int, default=120)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    deadline = time.time() + args.timeout
    config = IoTDBConfig(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
    )
    last_error = ""
    while time.time() < deadline:
        session = create_session(config)
        try:
            session.open(False)
            dataset = session.execute_query_statement("show databases")
            dataset.close_operation_handle()
            session.close()
            print(f"IoTDB is ready at {args.host}:{args.port}")
            return
        except Exception as exc:
            last_error = str(exc)
            try:
                session.close()
            except Exception:
                pass
            time.sleep(2)
    raise TimeoutError(f"IoTDB was not ready within {args.timeout}s: {last_error}")


if __name__ == "__main__":
    main()
