from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Any

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=100)
    experience_level: Literal["beginner", "intermediate", "advanced"] = "beginner"

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    experience_level: str
    class Config: from_attributes = True

class SessionCreate(BaseModel):
    module: Literal["case", "thinking", "quant", "pressure"] = "case"
    case_ref: str = "profitability_coffee"

class TurnIn(BaseModel):
    message: str = Field(min_length=1, max_length=8000)

class DecisionIn(BaseModel):
    kind: Literal["assumption", "hypothesis", "question", "evidence", "decision", "revision", "conclusion"]
    content: str = Field(min_length=1, max_length=4000)
    payload: dict[str, Any] = Field(default_factory=dict)
    parent_id: int | None = None

class EvaluateIn(BaseModel):
    response: str | None = None
