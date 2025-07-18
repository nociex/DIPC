#!/usr/bin/env python3
"""
Test runner script for DIPC Workers.
"""

import sys
import subprocess
import argparse


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run DIPC Worker test suites")
    parser.add_argument(
        "suite",
        choices=["unit", "integration", "all"],
        default="unit",
        nargs="?",
        help="Test suite to run"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = ["python", "-m", "pytest", "tests/", "-v"]
    
    if args.coverage:
        base_cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])
    
    success = True
    
    if args.suite == "all":
        # Run all worker tests
        success = run_command(base_cmd, "All Worker Tests")
    elif args.suite == "unit":
        # Run unit tests only
        cmd = base_cmd + ["-m", "not integration"]
        success = run_command(cmd, "Worker Unit Tests")
    elif args.suite == "integration":
        # Run integration tests
        cmd = base_cmd + ["-m", "integration"]
        success = run_command(cmd, "Worker Integration Tests")
    
    if success:
        print("🎉 Worker tests completed successfully!")
        sys.exit(0)
    else:
        print("💥 Worker tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()