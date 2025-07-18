"""Simple HTTP health check endpoint for workers."""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
from urllib.parse import urlparse
import structlog

from .monitoring.health_checks import get_worker_health_status, get_worker_metrics, check_worker_readiness

logger = structlog.get_logger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for worker health check endpoints."""
    
    def do_GET(self):
        """Handle GET requests for health checks."""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            
            if path == '/health':
                self._handle_health_check()
            elif path == '/health/detailed':
                self._handle_detailed_health_check()
            elif path == '/health/metrics':
                self._handle_metrics()
            elif path == '/health/ready':
                self._handle_readiness_check()
            else:
                self._send_error(404, "Not Found")
                
        except Exception as e:
            logger.error("Health check endpoint error", error=str(e))
            self._send_error(500, f"Internal Server Error: {str(e)}")
    
    def _handle_health_check(self):
        """Handle basic health check."""
        try:
            response = {
                "status": "healthy",
                "service": "dipc-worker",
                "version": "1.3.0",
                "timestamp": time.time()
            }
            self._send_json_response(200, response)
        except Exception as e:
            self._send_error(500, str(e))
    
    def _handle_detailed_health_check(self):
        """Handle detailed health check."""
        try:
            health_status = get_worker_health_status()
            status_code = 200 if health_status["status"] == "healthy" else 503
            self._send_json_response(status_code, health_status)
        except Exception as e:
            self._send_error(500, str(e))
    
    def _handle_metrics(self):
        """Handle metrics endpoint."""
        try:
            metrics = get_worker_metrics()
            self._send_json_response(200, metrics)
        except Exception as e:
            self._send_error(500, str(e))
    
    def _handle_readiness_check(self):
        """Handle readiness check."""
        try:
            ready = check_worker_readiness()
            response = {
                "ready": ready,
                "timestamp": time.time()
            }
            status_code = 200 if ready else 503
            self._send_json_response(status_code, response)
        except Exception as e:
            self._send_error(500, str(e))
    
    def _send_json_response(self, status_code: int, data: dict):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        json_data = json.dumps(data, indent=2)
        self.wfile.write(json_data.encode('utf-8'))
    
    def _send_error(self, status_code: int, message: str):
        """Send error response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        error_response = {
            "error": message,
            "status_code": status_code,
            "timestamp": time.time()
        }
        
        json_data = json.dumps(error_response, indent=2)
        self.wfile.write(json_data.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to use structured logging."""
        logger.info("Health check request", message=format % args)


class HealthCheckServer:
    """HTTP server for worker health checks."""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.server = None
        self.thread = None
        self.running = False
    
    def start(self):
        """Start the health check server."""
        try:
            self.server = HTTPServer(('0.0.0.0', self.port), HealthCheckHandler)
            self.thread = threading.Thread(target=self._run_server, daemon=True)
            self.running = True
            self.thread.start()
            
            logger.info(
                "Health check server started",
                port=self.port,
                endpoints=[
                    "/health",
                    "/health/detailed", 
                    "/health/metrics",
                    "/health/ready"
                ]
            )
            
        except Exception as e:
            logger.error("Failed to start health check server", error=str(e))
            raise
    
    def stop(self):
        """Stop the health check server."""
        if self.server and self.running:
            self.running = False
            self.server.shutdown()
            self.server.server_close()
            
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5)
            
            logger.info("Health check server stopped")
    
    def _run_server(self):
        """Run the server in a separate thread."""
        try:
            while self.running:
                self.server.serve_forever()
        except Exception as e:
            if self.running:  # Only log if we're supposed to be running
                logger.error("Health check server error", error=str(e))


# Global server instance
_health_server = None


def start_health_server(port: int = 8080):
    """Start the global health check server."""
    global _health_server
    
    if _health_server is None:
        _health_server = HealthCheckServer(port)
        _health_server.start()
    else:
        logger.warning("Health check server already running")


def stop_health_server():
    """Stop the global health check server."""
    global _health_server
    
    if _health_server:
        _health_server.stop()
        _health_server = None


def is_health_server_running() -> bool:
    """Check if health server is running."""
    global _health_server
    return _health_server is not None and _health_server.running