#!/usr/bin/env python3
"""
Test Runner Script - Runs pytest with coverage and common options

Usage:
    run_tests.py                     # Run all tests with coverage
    run_tests.py --unit              # Run only unit tests
    run_tests.py --integration       # Run only integration tests
    run_tests.py --fast              # Run without coverage (faster)
    run_tests.py --verbose           # Verbose output
    run_tests.py --path tests/unit   # Run tests in specific path

Examples:
    python scripts/run_tests.py
    python scripts/run_tests.py --unit --verbose
    python scripts/run_tests.py --path tests/unit/test_task_manager.py
"""

import subprocess
import sys
import argparse
from pathlib import Path


def build_pytest_command(args):
    """Build the pytest command with appropriate flags."""
    cmd = ["pytest"]

    # Determine test path
    if args.path:
        cmd.append(args.path)
    elif args.unit:
        cmd.append("tests/unit")
    elif args.integration:
        cmd.append("tests/integration")
    else:
        cmd.append("tests/")

    # Coverage options (unless --fast)
    if not args.fast:
        cmd.extend([
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            f"--cov-fail-under={args.min_coverage}"
        ])

    # Verbosity
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    # Show local variables in tracebacks
    cmd.append("--tb=short")

    # Parallel execution (if pytest-xdist installed)
    if args.parallel:
        cmd.extend(["-n", "auto"])

    # Additional pytest args
    if args.pytest_args:
        cmd.extend(args.pytest_args)

    return cmd


def main():
    parser = argparse.ArgumentParser(
        description="Run tests with pytest and coverage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument("--unit", action="store_true",
                        help="Run only unit tests (tests/unit)")
    parser.add_argument("--integration", action="store_true",
                        help="Run only integration tests (tests/integration)")
    parser.add_argument("--fast", action="store_true",
                        help="Skip coverage for faster execution")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose test output")
    parser.add_argument("--parallel", "-p", action="store_true",
                        help="Run tests in parallel (requires pytest-xdist)")
    parser.add_argument("--path", type=str,
                        help="Specific test path to run")
    parser.add_argument("--min-coverage", type=int, default=80,
                        help="Minimum coverage threshold (default: 80)")
    parser.add_argument("pytest_args", nargs="*",
                        help="Additional arguments to pass to pytest")

    args = parser.parse_args()

    # Build and display command
    cmd = build_pytest_command(args)
    print(f"Running: {' '.join(cmd)}")
    print("-" * 50)

    # Execute pytest
    result = subprocess.run(cmd)

    # Print coverage report location if generated
    if not args.fast and result.returncode == 0:
        htmlcov = Path("htmlcov/index.html")
        if htmlcov.exists():
            print("-" * 50)
            print(f"Coverage report: file://{htmlcov.absolute()}")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
