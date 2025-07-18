#!/usr/bin/env python3
"""
Test runner script for Document Intelligence & Parsing Center.
Provides different test suite execution options.
"""

import sys
import subprocess
import argparse
from pathlib import Path


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
    parser = argparse.ArgumentParser(description="Run DIPC test suites")
    parser.add_argument(
        "suite",
        choices=["unit", "integration", "performance", "security", "load", "all", "smoke"],
        help="Test suite to run"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Number of parallel workers"
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = ["python", "-m", "pytest"]
    
    if args.verbose:
        base_cmd.append("-v")
    
    if args.coverage:
        base_cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])
    
    if args.parallel > 1:
        base_cmd.extend(["-n", str(args.parallel)])
    
    # Test suite configurations
    test_configs = {
        "unit": {
            "markers": ["-m", "not integration and not performance and not security and not load"],
            "description": "Unit Tests",
            "timeout": 300
        },
        "integration": {
            "markers": ["-m", "integration"],
            "description": "Integration Tests",
            "timeout": 600
        },
        "performance": {
            "markers": ["-m", "performance"],
            "description": "Performance Tests",
            "timeout": 1200
        },
        "security": {
            "markers": ["-m", "security"],
            "description": "Security Tests",
            "timeout": 900
        },
        "load": {
            "markers": ["-m", "load"],
            "description": "Load Tests",
            "timeout": 1800
        },
        "smoke": {
            "markers": ["-m", "smoke or (not slow and not load and not performance)"],
            "description": "Smoke Tests",
            "timeout": 180
        },
        "all": {
            "markers": [],
            "description": "All Tests",
            "timeout": 3600
        }
    }
    
    success = True
    
    if args.suite == "all":
        # Run all test suites in sequence
        for suite_name in ["unit", "integration", "security", "performance"]:
            config = test_configs[suite_name]
            cmd = base_cmd + config["markers"] + ["--timeout", str(config["timeout"])]
            if not run_command(cmd, config["description"]):
                success = False
        
        # Run load tests separately (optional)
        print("\n" + "="*60)
        print("Load tests are resource intensive and optional.")
        response = input("Run load tests? (y/N): ").lower().strip()
        if response == 'y':
            config = test_configs["load"]
            cmd = base_cmd + config["markers"] + ["--timeout", str(config["timeout"])]
            if not run_command(cmd, config["description"]):
                success = False
    else:
        # Run specific test suite
        config = test_configs[args.suite]
        cmd = base_cmd + config["markers"] + ["--timeout", str(config["timeout"])]
        success = run_command(cmd, config["description"])
    
    # Summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 All requested tests completed successfully!")
        sys.exit(0)
    else:
        print("💥 Some tests failed. Check output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()