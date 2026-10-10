import psutil
import time
import os
from datetime import datetime

class HealthChecker:
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.rate_limit_hits = 0

    def get_uptime(self):
        return time.time() - self.start_time

    def get_memory_usage(self):
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    def get_system_load(self):
        return psutil.cpu_percent(interval=0.1)

    def get_status(self):
        return {
            "status": "healthy",
            "uptime_seconds": round(self.get_uptime(), 2),
            "memory_mb": round(self.get_memory_usage(), 2),
            "cpu_percent": self.get_system_load(),
            "requests_served": self.request_count,
            "rate_limit_hits": self.rate_limit_hits,
            "timestamp": datetime.utcnow().isoformat()
        }

health_checker = HealthChecker()
