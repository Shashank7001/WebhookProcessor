from .database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text
from pydantic import BaseModel, Field, field_validator,model_validator
from typing import Optional
from datetime import datetime
import re




class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(String, primary_key=True)#This is the PK
    from_msisdn: Mapped[str] = mapped_column(String, nullable=False)
    to_msisdn: Mapped[str] = mapped_column(String, nullable=False)
    ts: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)




RE_TZ = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
RE_PHONE = re.compile(r"^\+\d{1,15}$")

class WebhookMessage(BaseModel):
    message_id: str = Field(..., min_length=1)
    from_msisdn: str = Field(alias="from")
    to_msisdn: str = Field(alias="to")   
    ts: str
    text: Optional[str] = Field(None, max_length=4096)

    #This validates phone
    @field_validator('from_msisdn', 'to_msisdn')
    @classmethod
    def validate_phone(cls, v: str):
        if not RE_PHONE.match(v):
            raise ValueError("must be in E.164-like format, starting with '+'")
        return v
    
    #This validates Time
    @field_validator('ts')
    @classmethod
    def validate_timezone(cls, v: str):
        if not RE_TZ.match(v):
            raise ValueError("must be a strict ISO-8601 UTC string with 'Z' suffix")
        try:
            datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            raise ValueError("timestamp format is valid but date/time itself is invalid")
        return v

    model_config = {
        "populate_by_name": True
    }

class MessageOut(BaseModel):
    message_id: str
    from_msisdn: str = Field(alias="from")
    to_msisdn: str = Field(alias="to")
    ts: str
    text: Optional[str] = None
    
    model_config = {
        "populate_by_name": True
    }

class MessagesResponse(BaseModel):
    data: list[MessageOut]
    total: int
    limit: int
    offset: int

class SenderStat(BaseModel):
    from_msisdn: str = Field(alias="from")
    count: int
    
    model_config = {
        "populate_by_name": True
    }

class StatsResponse(BaseModel):
    total_messages: int
    senders_count: int
    messages_per_sender: list[SenderStat]
    first_message_ts: Optional[str]
    last_message_ts: Optional[str]



class MessageQuery(BaseModel):
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)
    from_msisdn: Optional[str] = Field(None, alias="from")
    since: Optional[str] = None
    q: Optional[str] = None
    to_msisdn: Optional[str] = Field(None, alias="to")

    @model_validator(mode='before')
    @classmethod
    def check_since_format(cls, values):
        since = values.get('since')
        if since and not RE_TZ.match(since):
            raise ValueError("since must be a strict ISO-8601 UTC string with 'Z' suffix")
        return values
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }