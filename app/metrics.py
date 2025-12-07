from prometheus_client import Counter, Histogram, generate_latest


HTTP_REQUESTS_TOTAL = Counter(
    'http_requests_total', 
    'Total HTTP requests received', 
    ['path', 'status']
)

# Counter for webhook processing outcomes
WEBHOOK_REQUESTS_TOTAL = Counter(
    'webhook_requests_total', 
    'Total webhook processing outcomes', 
    ['result']
)

# Histogram for request latency in milliseconds
REQUEST_LATENCY_MS = Histogram(
    'request_latency_ms', 
    'Request latency in milliseconds',
    buckets=[10, 50, 100, 250, 500, 1000, 2000, float('inf')]
)



def increment_http_requests(path: str, status: int):
    HTTP_REQUESTS_TOTAL.labels(path=path, status=status).inc()

def increment_webhook_outcome(result: str):
    WEBHOOK_REQUESTS_TOTAL.labels(result=result).inc()

def observe_latency(path: str, latency_ms: float):
    REQUEST_LATENCY_MS.observe(latency_ms)

def generate_metrics_response() -> bytes:
    return generate_latest()