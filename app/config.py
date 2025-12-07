from pydantic_settings import BaseSettings

class Settings(BaseSettings):
  
    DATABASE_URL: str
    WEBHOOK_SECRET: str
    LOG_LEVEL: str = "INFO"
    
    #This is default for page
    MESSAGES_DEFAULT_LIMIT: int = 50
    MESSAGES_MAX_LIMIT: int = 100

    class Config:

        env_file = ".env" 
        env_file_encoding = "utf-8"

try:
    settings = Settings()
    if not settings.WEBHOOK_SECRET:
        raise ValueError("WEBHOOK_SECRET is not set. Cannot start.")
except Exception as e:
    print(f"FATAL CONFIG ERROR: {e}")
    raise

