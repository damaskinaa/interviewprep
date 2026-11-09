import argparse

HOST = "127.0.0.1"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="nailit", description="Run the NailIt backend locally.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args(argv)

    from nailit.config import load_secrets

    load_secrets()

    import uvicorn

    uvicorn.run("nailit.api:app", host=HOST, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
