"""Observability utilities for metrics, tracing, and monitoring."""

import time
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading
from datetime import datetime, timedelta
import structlog

from .logging import metrics_collector, error_tracker

logger = structlog.get_logger(__name__)


@dataclass
class Metric:
    """Represents a single metric data point."""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    metric_type: str = "gauge"  # gauge, counter, histogram


@dataclass
class Alert:
    """Represents an alert condition."""
    name: str
    condition: Callable[[float], bool]
    message: str
    severity: str = "warning"  # info, warning, error, critical
    cooldown_seconds: int = 300  # 5 minutes default cooldown


class MetricsBuffer:
    """Thread-safe buffer for collecting metrics."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.metrics = deque(maxlen=max_size)
        self.lock = threading.Lock()
    
    def add_metric(self, metric: Metric):
        """Add a metric to the buffer."""
        with self.lock:
            self.metrics.append(metric)
    
    def get_metrics(self, since: Optional[float] = None) -> List[Metric]:
        """Get metrics from the buffer, optionally filtered by timestamp."""
        with self.lock:
            if since is None:
                return list(self.metrics)
            return [m for m in self.metrics if m.timestamp >= since]
    
    def clear_old_metrics(self, older_than: float):
        """Remove metrics older than the specified timestamp."""
        with self.lock:
            while self.metrics and self.metrics[0].timestamp < older_than:
                self.metrics.popleft()


class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: Dict[str, float] = {}  # Last triggered time
        self.lock = threading.Lock()
    
    def register_alert(self, alert: Alert):
        """Register a new alert."""
        with self.lock:
            self.alerts[alert.name] = alert
            logger.info("Alert registered", alert_name=alert.name, severity=alert.severity)
    
    def check_alerts(self, metrics: List[Metric]):
        """Check all registered alerts against current metrics."""
        current_time = time.time()
        
        # Group metrics by name for easier lookup
        metrics_by_name = defaultdict(list)
        for metric in metrics:
            metrics_by_name[metric.name].append(metric)
        
        with self.lock:
            for alert_name, alert in self.alerts.items():
                # Check cooldown
                last_triggered = self.alert_history.get(alert_name, 0)
                if current_time - last_triggered < alert.cooldown_seconds:
                    continue
                
                # Find relevant metrics
                relevant_metrics = []
                for metric_name, metric_list in metrics_by_name.items():
                    if alert_name in metric_name or metric_name in alert_name:
                        relevant_metrics.extend(metric_list)
                
                # Check alert condition
                for metric in relevant_metrics:
                    if alert.condition(metric.value):
                        self._trigger_alert(alert, metric)
                        self.alert_history[alert_name] = current_time
                        break
    
    def _trigger_alert(self, alert: Alert, metric: Metric):
        """Trigger an alert."""
        logger.warning(
            "Alert triggered",
            alert_name=alert.name,
            alert_message=alert.message,
            severity=alert.severity,
            metric_name=metric.name,
            metric_value=metric.value,
            metric_tags=metric.tags
        )
        
        # In a production system, this would send notifications
        # via email, Slack, PagerDuty, etc.


class PerformanceMonitor:
    """Monitors application performance and collects metrics."""
    
    def __init__(self):
        self.metrics_buffer = MetricsBuffer()
        self.alert_manager = AlertManager()
        self.running = False
        self.monitor_thread = None
        
        # Setup default alerts
        self._setup_default_alerts()
    
    def start(self):
        """Start the performance monitor."""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Performance monitor started")
    
    def stop(self):
        """Stop the performance monitor."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Performance monitor stopped")
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None, metric_type: str = "gauge"):
        """Record a metric."""
        metric = Metric(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags or {},
            metric_type=metric_type
        )
        self.metrics_buffer.add_metric(metric)
    
    def record_api_request(self, method: str, path: str, status_code: int, duration: float):
        """Record API request metrics."""
        tags = {
            "method": method,
            "path": path,
            "status_code": str(status_code),
            "status_class": f"{status_code // 100}xx"
        }
        
        self.record_metric("api_request_duration", duration, tags, "histogram")
        self.record_metric("api_request_count", 1, tags, "counter")
        
        # Log to structured logger as well
        metrics_collector.log_api_request(method, path, status_code, duration)
    
    def record_task_processing(self, task_type: str, status: str, duration: float, **kwargs):
        """Record task processing metrics."""
        tags = {
            "task_type": task_type,
            "status": status
        }
        
        self.record_metric("task_processing_duration", duration, tags, "histogram")
        self.record_metric("task_processing_count", 1, tags, "counter")
        
        # Record additional metrics
        for key, value in kwargs.items():
            if isinstance(value, (int, float)):
                self.record_metric(f"task_{key}", value, tags)
        
        # Log to structured logger
        metrics_collector.log_task_metrics(task_type, status, duration, **kwargs)
    
    def record_database_operation(self, operation: str, duration: float, success: bool = True):
        """Record database operation metrics."""
        tags = {
            "operation": operation,
            "status": "success" if success else "error"
        }
        
        self.record_metric("database_operation_duration", duration, tags, "histogram")
        self.record_metric("database_operation_count", 1, tags, "counter")
    
    def record_external_service_call(self, service: str, operation: str, duration: float, success: bool = True):
        """Record external service call metrics."""
        tags = {
            "service": service,
            "operation": operation,
            "status": "success" if success else "error"
        }
        
        self.record_metric("external_service_duration", duration, tags, "histogram")
        self.record_metric("external_service_count", 1, tags, "counter")
    
    def get_metrics_summary(self, since_minutes: int = 60) -> Dict[str, Any]:
        """Get a summary of metrics from the last N minutes."""
        since_timestamp = time.time() - (since_minutes * 60)
        metrics = self.metrics_buffer.get_metrics(since_timestamp)
        
        if not metrics:
            return {"message": "No metrics available", "timeframe_minutes": since_minutes}
        
        # Group metrics by name
        metrics_by_name = defaultdict(list)
        for metric in metrics:
            metrics_by_name[metric.name].append(metric)
        
        summary = {
            "timeframe_minutes": since_minutes,
            "total_metrics": len(metrics),
            "metrics": {}
        }
        
        for name, metric_list in metrics_by_name.items():
            values = [m.value for m in metric_list]
            summary["metrics"][name] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1] if values else 0
            }
        
        return summary
    
    def _setup_default_alerts(self):
        """Setup default system alerts."""
        # High error rate alert
        self.alert_manager.register_alert(Alert(
            name="high_error_rate",
            condition=lambda x: x > 0.05,  # 5% error rate
            message="High error rate detected",
            severity="warning"
        ))
        
        # Slow response time alert
        self.alert_manager.register_alert(Alert(
            name="slow_response_time",
            condition=lambda x: x > 5.0,  # 5 seconds
            message="Slow response time detected",
            severity="warning"
        ))
        
        # High memory usage alert
        self.alert_manager.register_alert(Alert(
            name="high_memory_usage",
            condition=lambda x: x > 90.0,  # 90% memory usage
            message="High memory usage detected",
            severity="error"
        ))
        
        # High CPU usage alert
        self.alert_manager.register_alert(Alert(
            name="high_cpu_usage",
            condition=lambda x: x > 80.0,  # 80% CPU usage
            message="High CPU usage detected",
            severity="warning"
        ))
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Check alerts
                recent_metrics = self.metrics_buffer.get_metrics(time.time() - 300)  # Last 5 minutes
                self.alert_manager.check_alerts(recent_metrics)
                
                # Clean up old metrics (keep last 24 hours)
                cleanup_time = time.time() - (24 * 60 * 60)
                self.metrics_buffer.clear_old_metrics(cleanup_time)
                
                # Sleep for 30 seconds
                time.sleep(30)
                
            except Exception as e:
                error_tracker.log_error(e, category="monitoring")
                time.sleep(30)  # Continue monitoring even if there's an error
    
    def _collect_system_metrics(self):
        """Collect system performance metrics."""
        try:
            import psutil
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_metric("system_cpu_percent", cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.record_metric("system_memory_percent", memory.percent)
            self.record_metric("system_memory_used", memory.used)
            self.record_metric("system_memory_available", memory.available)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.record_metric("system_disk_percent", disk_percent)
            self.record_metric("system_disk_used", disk.used)
            self.record_metric("system_disk_free", disk.free)
            
            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            self.record_metric("process_memory_rss", process_memory.rss)
            self.record_metric("process_memory_vms", process_memory.vms)
            self.record_metric("process_cpu_percent", process.cpu_percent())
            self.record_metric("process_num_threads", process.num_threads())
            
            # Log resource usage
            metrics_collector.log_resource_usage(cpu_percent, memory.percent, disk_percent)
            
        except Exception as e:
            error_tracker.log_error(e, category="system_metrics")


class RequestTracer:
    """Distributed tracing for requests."""
    
    def __init__(self):
        self.active_traces: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
    
    def start_trace(self, trace_id: str, operation: str, **context):
        """Start a new trace."""
        with self.lock:
            self.active_traces[trace_id] = {
                "trace_id": trace_id,
                "operation": operation,
                "start_time": time.time(),
                "spans": [],
                "context": context
            }
    
    def add_span(self, trace_id: str, span_name: str, duration: float, **tags):
        """Add a span to an existing trace."""
        with self.lock:
            if trace_id in self.active_traces:
                self.active_traces[trace_id]["spans"].append({
                    "name": span_name,
                    "duration": duration,
                    "timestamp": time.time(),
                    "tags": tags
                })
    
    def finish_trace(self, trace_id: str, success: bool = True, error: Optional[str] = None):
        """Finish a trace and log the results."""
        with self.lock:
            if trace_id not in self.active_traces:
                return
            
            trace = self.active_traces.pop(trace_id)
            total_duration = time.time() - trace["start_time"]
            
            logger.info(
                "Trace completed",
                trace_id=trace_id,
                operation=trace["operation"],
                total_duration=total_duration,
                success=success,
                error=error,
                spans_count=len(trace["spans"]),
                context=trace["context"]
            )
            
            # Log individual spans for detailed analysis
            for span in trace["spans"]:
                logger.debug(
                    "Trace span",
                    trace_id=trace_id,
                    span_name=span["name"],
                    span_duration=span["duration"],
                    span_tags=span["tags"]
                )


# Global instances
performance_monitor = PerformanceMonitor()
request_tracer = RequestTracer()


def start_monitoring():
    """Start all monitoring services."""
    performance_monitor.start()
    logger.info("Monitoring services started")


def stop_monitoring():
    """Stop all monitoring services."""
    performance_monitor.stop()
    logger.info("Monitoring services stopped")


def get_monitoring_status() -> Dict[str, Any]:
    """Get current monitoring status."""
    return {
        "performance_monitor_running": performance_monitor.running,
        "metrics_buffer_size": len(performance_monitor.metrics_buffer.metrics),
        "active_traces": len(request_tracer.active_traces),
        "registered_alerts": len(performance_monitor.alert_manager.alerts)
    }