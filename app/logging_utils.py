import json
import logging
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

request_id_counter = 0

def setup_json_logger(level: str):
    global app_logger
    
    if 'app_logger' in globals() and app_logger.handlers:
        return

    app_logger = logging.getLogger("app")
    app_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    if app_logger.handlers:
        app_logger.handlers.clear()

    class JsonLogHandler(logging.Handler):
        def emit(self, record):
            log_entry = self.format(record)
            print(log_entry, flush=True)

        def format(self, record):
            log_data = {
                "ts": datetime.now().isoformat(timespec='milliseconds') + 'Z',
                "level": record.levelname,
                "message": record.getMessage(),
            }
            
            if hasattr(record, 'extra_data') and isinstance(record.extra_data, dict):
                log_data.update(record.extra_data)
            
            if record.exc_info:
                import traceback
                log_data["traceback"] = "".join(traceback.format_exception(*record.exc_info))

            return json.dumps(log_data)

    app_logger.addHandler(JsonLogHandler())
    app_logger.propagate = False # Prevent double logging

app_logger = logging.getLogger("app")
setup_json_logger("INFO") 

class JsonLoggingMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        global request_id_counter
        start_time = datetime.now()
        
        request_id_counter += 1
        request_id = f"req-{request_id_counter}"

        try:
            response = await call_next(request)
        except Exception as e:
            process_time = datetime.now() - start_time
            app_logger.error(
                "Uncaught server error", 
                exc_info=True,
                extra={"extra_data": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": 500,
                    "latency_ms": int(process_time.total_seconds() * 1000),
                }}
            )
            raise e 

        process_time = datetime.now() - start_time
        latency_ms = int(process_time.total_seconds() * 1000)

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": latency_ms,
        }
        
        if request.url.path == "/webhook":
            webhook_data = getattr(request.state, 'webhook_log_data', {})
            log_data.update(webhook_data)
        
        level = logging.INFO
        if response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.WARNING
        
        app_logger.log(
            level, 
            "Request processed", 
            extra={"extra_data": log_data}
        )
        
        return response