import os
import sys
import argparse


def main():
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description="ExHentai Gallery Downloader")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("--gui", action="store_true", help="Run in GUI mode (default)")
    parser.add_argument("--language", "-l", type=str, help="Set UI language")
    args = parser.parse_args()

    if args.cli:
        from .cli import main as cli_main
        cli_main()
    else:
        from .ui.app import App
        app = App(language=args.language)
        app.run()


if __name__ == "__main__":
    main()
