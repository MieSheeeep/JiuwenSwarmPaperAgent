"""Run the offline chain without importing model SDKs or secret settings."""
import argparse
import json

from research.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(description='Traceable offline research artifacts')
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('import-baseline', help='Rescore saved experiments and build a local report')
    command.add_argument('--source', default='output/baseline')
    command.add_argument('--output', default='output/research_v2')
    args = parser.parse_args()
    try:
        result = run_pipeline(args.source, args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f'Pipeline failed: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
