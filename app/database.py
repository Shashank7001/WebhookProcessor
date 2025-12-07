from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

from sqlalchemy.exc import OperationalError
from .logging_utils import app_logger 



engine = create_engine(
    settings.DATABASE_URL,connect_args={"check_same_thread": False}, 
    echo=(settings.LOG_LEVEL == "DEBUG")
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()



def init_db():
    try:
       
        Base.metadata.create_all(bind=engine, checkfirst=True)
        app_logger.info("Database schema initialized successfully.")
    
    except OperationalError as e:
        if 'already exists' in str(e):
             app_logger.info("Database already exists Worker Your bro did it first, continuing.", extra={"extra_data": {"db_init_status": "existing"}})
        else:
             app_logger.error(f"Unexpected OperationalError during DB init: {e}", exc_info=True)
             raise
             
    except Exception as e:
        app_logger.error(f"Fatal error initializing database: {e}", exc_info=True)
        raise

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

