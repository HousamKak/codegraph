"""Validation endpoints."""

from fastapi import APIRouter, HTTPException
import logging

from ..database import get_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/validation", tags=["Validation"])


@router.post("")
async def validate(incremental: bool = False, pyright: bool = False):
    """
    Run validation on the graph.

    Checks for conservation law violations, broken references, etc.
    """
    validator = get_validator()

    try:
        report = validator.validate(incremental=incremental, include_pyright=pyright)
        return report
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/structural")
async def validate_structural():
    """Run only the Structural (S Law) checks."""
    validator = get_validator()

    try:
        return validator.get_structural_report()
    except Exception as e:
        logger.error(f"Structural validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reference")
async def validate_reference():
    """Run only the Referential (R Law) checks."""
    validator = get_validator()

    try:
        return validator.get_reference_report()
    except Exception as e:
        logger.error(f"Reference validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/typing")
async def validate_typing(pyright: bool = False):
    """Run only the Typing/Data Flow (T Law) checks."""
    validator = get_validator()

    try:
        return validator.get_typing_report(include_pyright=pyright)
    except Exception as e:
        logger.error(f"Typing validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def get_validation_report():
    """Get the last validation report."""
    validator = get_validator()

    try:
        report = validator.get_last_report()
        return report
    except Exception as e:
        logger.error(f"Get validation report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
