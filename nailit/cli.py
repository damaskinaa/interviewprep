import argparse
import logging
import sys

HOST = "127.0.0.1"


def check_library(path):
    from nailit.library import LibraryError, load_library, summary

    try:
        lib = load_library(path)
    except LibraryError as error:
        for line in error.errors:
            print(f"ERROR {line}", file=sys.stderr)
        print(f"{len(error.errors)} error(s)", file=sys.stderr)
        return 1
    print(f"OK: {summary(lib)}")
    return 0


def serve(port, reload):
    from nailit.config import load_secrets

    load_secrets()
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("nailit").setLevel(logging.INFO)

    import uvicorn

    uvicorn.run("nailit.api:app", host=HOST, port=port, reload=reload)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="nailit", description="Run the NailIt backend locally.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    commands = parser.add_subparsers(dest="command")
    check = commands.add_parser("check-library", help="Validate a library folder (default ~/NailIt/library).")
    check.add_argument("path", nargs="?")
    args = parser.parse_args(argv)
    if args.command == "check-library":
        return check_library(args.path)
    return serve(args.port, args.reload)


if __name__ == "__main__":
    sys.exit(main())
