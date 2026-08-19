from typing import Optional

from pydantic import BaseModel


class StatementRequest(BaseModel):
    kind: str  # "severance" / "overtime"
    city: str
    monthly_salary: float
    years: Optional[int] = 0  # severance
    months: Optional[int] = 0  # severance
    scenario: Optional[str] = "negotiated"  # severance
    overtime_type: Optional[str] = "weekday"  # overtime
    hours: Optional[float] = 0  # overtime