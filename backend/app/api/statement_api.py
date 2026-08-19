from fastapi import APIRouter

from app.core.tools.statement import build_statement
from app.schemas.Statement import StatementRequest
router = APIRouter(prefix="/api/agent",tags=["statement"])

@router.post("/statement")
def statement(req:StatementRequest) -> dict:
    result =  build_statement(
        req.kind,
        {
            "city": req.city,
            "monthly_salary": req.monthly_salary,
            "years": req.years,
            "months": req.months,
            "scenario": req.scenario,
            "overtime_type": req.overtime_type,
            "hours": req.hours,
        },
    )

    return result