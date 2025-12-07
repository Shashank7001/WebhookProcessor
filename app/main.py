import json
from datetime import datetime
from typing import Optional, Annotated

from fastapi import FastAPI, Depends, status, Response, Header, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, func, exc
from pydantic import ValidationError

from . import utils
from . import metrics
from .config import settings
from .database import init_db, get_db
from .models import WebhookMessage, Message, MessageQuery, MessagesResponse, StatsResponse,MessageOut
from .logging_utils import JsonLoggingMiddleware, setup_json_logger, app_logger


setup_json_logger(settings.LOG_LEVEL)
app = FastAPI()


app.add_middleware(JsonLoggingMiddleware)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = datetime.now()
    
    try:
        response = await call_next(request)
    except Exception as e:
        metrics.increment_http_requests(request.url.path, 500)
        raise e
    
    end_time = datetime.now()
    latency_ms = (end_time - start_time).total_seconds() * 1000
    
    metrics.increment_http_requests(request.url.path, response.status_code)
    metrics.observe_latency(request.url.path, latency_ms)
    
    return response

@app.on_event("startup")
async def startup_event():
    app_logger.info("Application starting up...", extra={"extra_data": {"event": "startup"}})
    try:
        init_db()
    except Exception as e:
        app_logger.error(f"Failed to initialize database: {e}", exc_info=True)
        pass

@app.on_event("shutdown")
async def shutdown_event():
    app_logger.info("Application shutting down...", extra={"extra_data": {"event": "shutdown"}})

async def get_raw_body(request: Request):
    return await request.body()

def verify_signature(
    raw_body: Annotated[bytes, Depends(get_raw_body)],
    x_signature: Annotated[Optional[str], Header(alias="X-Signature")]
):
    if not x_signature:
        app_logger.warning("Missing X-Signature header on /webhook")
        metrics.increment_webhook_outcome("missing_signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid signature"
        )
    if not utils.verify_hmac_signature(raw_body, x_signature, settings.WEBHOOK_SECRET):
        
        app_logger.error("Invalid X-Signature provided on /webhook", extra={"extra_data": {"signature": x_signature}})
        metrics.increment_webhook_outcome("invalid_signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid signature"
        )
    
    return True

@app.post("/webhook", status_code=status.HTTP_200_OK)
async def webhook_ingest(
    request: Request,
    raw_body: Annotated[bytes, Depends(get_raw_body)],
    db: Annotated[Session, Depends(get_db)],
    signature_ok: Annotated[bool, Depends(verify_signature)] 
):
    
    
    webhook_log_data = {"dup": False, "result": "created"} 

    try:
        data = json.loads(raw_body.decode('utf-8'))
        message_in = WebhookMessage.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        error_detail = "Validation Error"
        if isinstance(e, ValidationError):
            error_detail = json.loads(e.json())
        
        app_logger.warning("Webhook payload validation failed", extra={"extra_data": {"validation_error": error_detail}})
        metrics.increment_webhook_outcome("validation_error")
        webhook_log_data.update({"result": "validation_error"})
        
        request.state.webhook_log_data = webhook_log_data
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            content={"detail": error_detail}
        )

    new_message = Message(
        message_id=message_in.message_id,
        from_msisdn=message_in.from_msisdn,
        to_msisdn=message_in.to_msisdn,
        ts=message_in.ts,
        text=message_in.text,
        created_at=datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
    )

    try:
        db.add(new_message)
        db.commit()
    except exc.IntegrityError:
        db.rollback() 
        
        exists = db.query(Message.message_id).filter(
            Message.message_id == message_in.message_id
        ).first()
        
        if exists:
            webhook_log_data.update({"dup": True, "result": "duplicate"})
            metrics.increment_webhook_outcome("duplicate")
            app_logger.info(f"Duplicate message_id received: {message_in.message_id}")
        else:
          
            webhook_log_data.update({"result": "db_error"})
            metrics.increment_webhook_outcome("db_error")
            app_logger.error("Unexpected IntegrityError on webhook insert", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    webhook_log_data.update({"message_id": message_in.message_id})
    request.state.webhook_log_data = webhook_log_data
    
    return {"status": "ok"}



@app.get("/messages", response_model=MessagesResponse)
def list_messages(
    query_params: Annotated[MessageQuery, Depends()],
    db: Annotated[Session, Depends(get_db)],
    request: Request
):
    
    

    base_query = db.query(Message)
    
 
    raw_from = query_params.from_msisdn
    if not raw_from and 'from' in request.query_params:
        raw_from = request.query_params.get('from')

    if raw_from:
        normalized_from = raw_from.replace(' ', '+')
        app_logger.debug(f"Filtering by 'from' MSISDN raw={raw_from!r} normalized={normalized_from!r}")
        base_query = base_query.filter(Message.from_msisdn == normalized_from)
        
    
    if query_params.to_msisdn:
        normalized_to = query_params.to_msisdn.replace(' ', '+')
        base_query = base_query.filter(Message.to_msisdn == normalized_to)

    if query_params.since:
        base_query = base_query.filter(Message.ts >= query_params.since)
        

    if query_params.q:
        search_term = f"%{query_params.q}%"
        # Case-insensitive substring match
        base_query = base_query.filter(Message.text.ilike(search_term)) 
        

    total_count = base_query.count()
    

    final_query = base_query.order_by(
        Message.ts.asc(), 
        Message.message_id.asc()
    ).limit(
        query_params.limit
    ).offset(
        query_params.offset
    )
    
    messages = final_query.all()
    

    message_outs = [
        MessageOut(
            message_id=m.message_id, 
            from_msisdn=m.from_msisdn, 
            to_msisdn=m.to_msisdn, 
            ts=m.ts, 
            text=m.text
        ) 
        for m in messages
    ]
    
    return MessagesResponse(
        data=message_outs,
        total=total_count,
        limit=query_params.limit,
        offset=query_params.offset
    )



@app.get("/stats", response_model=StatsResponse)
def get_stats(db: Annotated[Session, Depends(get_db)]):
  
    total_messages = db.query(Message).count()
    senders_count = db.query(Message.from_msisdn).distinct().count()
    
  
    messages_per_sender_raw = db.query(
        Message.from_msisdn, 
        func.count(Message.message_id).label("count")
    ).group_by(
        Message.from_msisdn
    ).order_by(
        text("count DESC")
    ).limit(10).all()
    
    messages_per_sender = [
        {"from": r[0], "count": r[1]} 
        for r in messages_per_sender_raw
    ]
    
    first_message_ts = db.query(func.min(Message.ts)).scalar()
    last_message_ts = db.query(func.max(Message.ts)).scalar()
    
    if total_messages == 0:
        first_message_ts = None
        last_message_ts = None
    
    return StatsResponse(
        total_messages=total_messages,
        senders_count=senders_count,
        messages_per_sender=messages_per_sender,
        first_message_ts=first_message_ts,
        last_message_ts=last_message_ts
    )




@app.get("/health/live", status_code=status.HTTP_200_OK)
def liveness_probe():
    return {"status": "live"}

def check_db_reachable(db: Annotated[Session, Depends(get_db)]):

    try:
        db.execute(text("SELECT 1 FROM messages LIMIT 1"))
        return True
    except exc.DBAPIError as e:
        app_logger.error(f"Readiness probe failed: DB connection error: {e}")
        return False

@app.get("/health/ready", status_code=status.HTTP_200_OK)
def readiness_probe(db_ok: Annotated[bool, Depends(check_db_reachable)]):
    
    if not db_ok:
        return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    return {"status": "ready"}



@app.get("/metrics", response_class=PlainTextResponse)
def get_prometheus_metrics():
    return metrics.generate_metrics_response().decode('utf-8')