#!/usr/bin/env python3
"""
DIPC Health Check and Diagnostic Script

This script performs comprehensive health checks on all DIPC services
and provides diagnostic information to help troubleshoot issues.
"""

import subprocess
import requests
import json
import time
import os
import sys
import socket
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse

class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def colored_print(text: str, color: str = Colors.WHITE, bold: bool = False) -> None:
    """Print colored text."""
    prefix = Colors.BOLD if bold else ""
    print(f"{prefix}{color}{text}{Colors.RESET}")

def print_header(text: str) -> None:
    """Print a section header."""
    colored_print(f"\n{'='*60}", Colors.BLUE)
    colored_print(f" {text}", Colors.BLUE, bold=True)
    colored_print(f"{'='*60}", Colors.BLUE)

def print_success(text: str) -> None:
    """Print success message."""
    colored_print(f"✓ {text}", Colors.GREEN)

def print_warning(text: str) -> None:
    """Print warning message."""
    colored_print(f"⚠ {text}", Colors.YELLOW)

def print_error(text: str) -> None:
    """Print error message."""
    colored_print(f"✗ {text}", Colors.RED)

def print_info(text: str) -> None:
    """Print info message."""
    colored_print(f"ℹ {text}", Colors.CYAN)

class HealthChecker:
    """Main health checker class."""
    
    def __init__(self, api_url: str = "http://localhost:38100"):
        self.api_url = api_url.rstrip('/')
        self.results = {
            'overall': True,
            'services': {},
            'issues': []
        }
    
    def check_docker_availability(self) -> bool:
        """Check if Docker is available and running."""
        print_header("Docker Environment Check")
        
        try:
            # Check if Docker is installed
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print_error("Docker is not installed or not in PATH")
                return False
            
            print_success(f"Docker version: {result.stdout.strip()}")
            
            # Check if Docker is running
            result = subprocess.run(['docker', 'info'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print_error("Docker daemon is not running")
                return False
            
            print_success("Docker daemon is running")
            
            # Check Docker Compose
            result = subprocess.run(['docker-compose', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print_warning("Docker Compose not found, trying docker compose...")
                result = subprocess.run(['docker', 'compose', 'version'], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    print_error("Docker Compose is not available")
                    return False
            
            print_success(f"Docker Compose version: {result.stdout.strip()}")
            return True
            
        except FileNotFoundError:
            print_error("Docker is not installed")
            return False
    
    def check_docker_services(self) -> Dict[str, bool]:
        """Check the status of Docker services."""
        print_header("Docker Services Check")
        
        services = {}
        
        try:
            # Get running containers
            result = subprocess.run(['docker-compose', 'ps'], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                print_warning("Could not get docker-compose status, trying docker ps...")
                result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}'], 
                                      capture_output=True, text=True)
            
            output = result.stdout
            print_info("Docker containers status:")
            print(output)
            
            # Parse service status
            expected_services = ['dipc-api', 'dipc-worker', 'dipc-frontend', 'dipc-db', 'dipc-redis', 'dipc-qdrant']
            
            for service in expected_services:
                if service in output and 'Up' in output:
                    services[service] = True
                    print_success(f"{service} service is running")
                else:
                    services[service] = False
                    print_error(f"{service} service is not running")
            
            return services
            
        except Exception as e:
            print_error(f"Error checking Docker services: {str(e)}")
            return {}
    
    def check_port_availability(self) -> Dict[str, bool]:
        """Check if required ports are available."""
        print_header("Port Availability Check")
        
        ports = {
            'frontend': 38110,
            'api': 38100,
            'worker_health': 8001,
            'db': 5432,
            'redis': 6379,
            'qdrant': 6333,
            'qdrant_grpc': 6334
        }
        
        port_status = {}
        
        for service, port in ports.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    port_status[service] = True
                    print_success(f"{service} port {port} is accessible")
                else:
                    port_status[service] = False
                    print_error(f"{service} port {port} is not accessible")
                    
            except Exception as e:
                port_status[service] = False
                print_error(f"Error checking {service} port {port}: {str(e)}")
        
        return port_status
    
    def check_api_health(self) -> Dict[str, any]:
        """Check API health endpoint."""
        print_header("API Health Check")
        
        health_info = {
            'api_accessible': False,
            'health_endpoint': False,
            'response_time': None,
            'health_data': None
        }
        
        try:
            # Test basic connectivity
            start_time = time.time()
            response = requests.get(f"{self.api_url}/v1/health", timeout=10)
            response_time = time.time() - start_time
            
            health_info['api_accessible'] = True
            health_info['response_time'] = response_time
            
            print_success(f"API is accessible at {self.api_url}")
            print_info(f"Response time: {response_time:.2f}s")
            
            if response.status_code == 200:
                health_info['health_endpoint'] = True
                health_info['health_data'] = response.json()
                print_success("Health endpoint is working")
                print_info(f"Health data: {json.dumps(health_info['health_data'], indent=2)}")
            else:
                print_error(f"Health endpoint returned status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print_error("Cannot connect to API")
        except requests.exceptions.Timeout:
            print_error("API request timeout")
        except Exception as e:
            print_error(f"API health check failed: {str(e)}")
        
        return health_info
    
    def check_worker_health(self) -> Dict[str, any]:
        """Check worker health endpoint."""
        print_header("Worker Health Check")
        
        worker_info = {
            'worker_accessible': False,
            'health_endpoint': False,
            'celery_status': None
        }
        
        try:
            # Check worker health endpoint
            response = requests.get("http://localhost:8001/health", timeout=10)
            worker_info['worker_accessible'] = True
            
            if response.status_code == 200:
                worker_info['health_endpoint'] = True
                print_success("Worker health endpoint is working")
                print_info(f"Worker health data: {response.text}")
            else:
                print_error(f"Worker health endpoint returned status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print_error("Cannot connect to worker health endpoint")
        except Exception as e:
            print_error(f"Worker health check failed: {str(e)}")
        
        # Check Celery status
        try:
            result = subprocess.run(['docker-compose', 'exec', '-T', 'worker', 
                                   'celery', '-A', 'src.celery_app', 'inspect', 'ping'],
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                worker_info['celery_status'] = 'healthy'
                print_success("Celery workers are responding")
            else:
                worker_info['celery_status'] = 'unhealthy'
                print_error("Celery workers are not responding")
                
        except subprocess.TimeoutExpired:
            print_error("Celery status check timeout")
        except Exception as e:
            print_error(f"Celery status check failed: {str(e)}")
        
        return worker_info
    
    def check_database_connection(self) -> Dict[str, any]:
        """Check database connection."""
        print_header("Database Connection Check")
        
        db_info = {
            'connection': False,
            'migrations': False,
            'tables': []
        }
        
        try:
            # Check database connection
            result = subprocess.run(['docker-compose', 'exec', '-T', 'db', 
                                   'pg_isready', '-U', 'dipc_user', '-d', 'dipc'],
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                db_info['connection'] = True
                print_success("Database connection is working")
            else:
                print_error("Database connection failed")
                
        except Exception as e:
            print_error(f"Database connection check failed: {str(e)}")
        
        # Check migrations
        try:
            result = subprocess.run(['docker-compose', 'exec', '-T', 'api', 
                                   'python', '-m', 'alembic', 'current'],
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                db_info['migrations'] = True
                print_success("Database migrations are up to date")
                print_info(f"Current migration: {result.stdout.strip()}")
            else:
                print_error("Database migrations are not up to date")
                
        except Exception as e:
            print_error(f"Migration check failed: {str(e)}")
        
        return db_info
    
    def check_storage_access(self) -> Dict[str, any]:
        """Check storage access."""
        print_header("Storage Check")
        
        storage_info = {
            'local_storage_accessible': False,
            'directory_exists': False,
            'write_test': False
        }
        
        try:
            # Check local storage directory
            import os
            storage_path = "./storage"
            if os.path.exists(storage_path):
                storage_info['directory_exists'] = True
                print_success("Local storage directory exists")
                
                # Test write access
                test_file = os.path.join(storage_path, "test_write.txt")
                try:
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    storage_info['write_test'] = True
                    print_success("Storage directory is writable")
                except Exception:
                    print_error("Storage directory is not writable")
                    
                storage_info['local_storage_accessible'] = True
                print_success("Local storage is accessible")
            else:
                print_error("Local storage directory does not exist")
                
        except Exception as e:
            print_error(f"Storage check failed: {str(e)}")
        
        return storage_info
    
    def check_configuration(self) -> Dict[str, any]:
        """Check configuration files."""
        print_header("Configuration Check")
        
        config_info = {
            'env_file': False,
            'docker_compose': False,
            'api_keys': False
        }
        
        # Check .env file
        env_file = Path('.env')
        if env_file.exists():
            config_info['env_file'] = True
            print_success(".env file exists")
            
            # Check for API keys
            env_content = env_file.read_text()
            if 'OPENAI_API_KEY=' in env_content or 'OPENROUTER_API_KEY=' in env_content:
                config_info['api_keys'] = True
                print_success("API keys are configured")
            else:
                print_warning("No API keys found in .env file")
        else:
            print_error(".env file not found")
        
        # Check docker-compose file
        compose_file = Path('docker-compose.yml')
        if compose_file.exists():
            config_info['docker_compose'] = True
            print_success("docker-compose.yml exists")
        else:
            print_error("docker-compose.yml not found")
        
        return config_info
    
    def check_system_resources(self) -> Dict[str, any]:
        """Check system resources."""
        print_header("System Resources Check")
        
        resource_info = {
            'disk_space': None,
            'memory_usage': None,
            'docker_stats': None
        }
        
        try:
            # Check disk space
            result = subprocess.run(['df', '-h', '.'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 4:
                        resource_info['disk_space'] = {
                            'total': parts[1],
                            'used': parts[2],
                            'available': parts[3],
                            'usage_percent': parts[4]
                        }
                        print_success(f"Disk space: {parts[3]} available ({parts[4]} used)")
                        
                        # Warn if disk space is low
                        usage_percent = int(parts[4].replace('%', ''))
                        if usage_percent > 90:
                            print_error("Disk space is running low!")
                        elif usage_percent > 80:
                            print_warning("Disk space is getting low")
            
            # Check Docker stats
            result = subprocess.run(['docker', 'stats', '--no-stream', '--format', 
                                   'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                resource_info['docker_stats'] = result.stdout
                print_success("Docker container stats:")
                print(result.stdout)
            
        except Exception as e:
            print_error(f"System resource check failed: {str(e)}")
        
        return resource_info
    
    def run_comprehensive_check(self) -> Dict[str, any]:
        """Run all health checks."""
        print_header("DIPC Comprehensive Health Check")
        
        start_time = time.time()
        
        # Run all checks
        self.results['services']['docker'] = self.check_docker_availability()
        self.results['services']['docker_services'] = self.check_docker_services()
        self.results['services']['ports'] = self.check_port_availability()
        self.results['services']['api'] = self.check_api_health()
        self.results['services']['worker'] = self.check_worker_health()
        self.results['services']['database'] = self.check_database_connection()
        self.results['services']['storage'] = self.check_storage_access()
        self.results['services']['configuration'] = self.check_configuration()
        self.results['services']['resources'] = self.check_system_resources()
        
        # Calculate overall health
        total_time = time.time() - start_time
        
        # Summary
        print_header("Health Check Summary")
        
        issues = []
        
        # Check for critical issues
        if not self.results['services']['docker']:
            issues.append("Docker is not available")
        
        if not self.results['services']['api'].get('health_endpoint', False):
            issues.append("API health endpoint is not working")
        
        if not self.results['services']['database'].get('connection', False):
            issues.append("Database connection failed")
        
        if not self.results['services']['configuration'].get('api_keys', False):
            issues.append("API keys are not configured")
        
        self.results['issues'] = issues
        self.results['overall'] = len(issues) == 0
        
        if self.results['overall']:
            print_success("All health checks passed!")
        else:
            print_error("Some health checks failed:")
            for issue in issues:
                print_error(f"  - {issue}")
        
        print_info(f"Health check completed in {total_time:.2f}s")
        
        return self.results
    
    def generate_diagnostic_report(self) -> str:
        """Generate a diagnostic report."""
        report = []
        report.append("DIPC Health Check Report")
        report.append("=" * 50)
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Overall Health: {'HEALTHY' if self.results['overall'] else 'UNHEALTHY'}")
        report.append("")
        
        if self.results['issues']:
            report.append("Issues Found:")
            for issue in self.results['issues']:
                report.append(f"  - {issue}")
            report.append("")
        
        report.append("Service Status:")
        for service, status in self.results['services'].items():
            if isinstance(status, dict):
                report.append(f"  {service}: {json.dumps(status, indent=4)}")
            else:
                report.append(f"  {service}: {status}")
        
        return "\n".join(report)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="DIPC Health Check and Diagnostic Tool")
    parser.add_argument("--api-url", default="http://localhost:38100",
                       help="API URL to check")
    parser.add_argument("--save-report", action="store_true",
                       help="Save diagnostic report to file")
    parser.add_argument("--json", action="store_true",
                       help="Output results in JSON format")
    parser.add_argument("--quiet", action="store_true",
                       help="Only show summary")
    
    args = parser.parse_args()
    
    if not args.quiet:
        colored_print("DIPC Health Check and Diagnostic Tool", Colors.CYAN, bold=True)
    
    # Create health checker
    checker = HealthChecker(args.api_url)
    
    # Run checks
    results = checker.run_comprehensive_check()
    
    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    elif args.save_report:
        report = checker.generate_diagnostic_report()
        report_file = f"dipc-health-report-{int(time.time())}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        print_success(f"Diagnostic report saved to {report_file}")
    
    # Exit with appropriate code
    sys.exit(0 if results['overall'] else 1)

if __name__ == "__main__":
    main()