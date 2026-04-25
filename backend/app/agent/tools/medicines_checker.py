"""Medicines Checker tool — fuzzy lookup against the NHIS medicines formulary."""
from __future__ import annotations

from app.agent.tools.base import Tool
from app.data_access import medicines_db


def _handler(args: dict) -> dict:
    name = (args.get("name") or "").strip()
    if not name:
        return {"error": "Missing required argument: name"}
    limit = int(args.get("limit", 5))
    matches = medicines_db.search_medicine(name, limit=limit)
    if not matches:
        return {
            "query": name,
            "matches": [],
            "summary": (
                f"No medicine matching '{name}' found in the NHIS Medicines List. "
                "Treat as not-on-formulary unless verified against the latest official list."
            ),
        }
    top = matches[0]
    if top.covered:
        summary = (
            f"'{top.name}' ({top.generic_name} {top.strength} {top.form}) is on the NHIS "
            f"Medicines List and should be provided without out-of-pocket payment at "
            f"{', '.join(top.level_of_care) or 'eligible levels of care'}."
        )
    else:
        summary = (
            f"'{top.name}' ({top.generic_name} {top.strength} {top.form}) is NOT on the NHIS "
            f"Medicines List. The member may be asked to pay or seek the medicine through "
            f"another programme. Notes: {top.notes}".rstrip()
        )
    return {
        "query": name,
        "matches": [m.to_dict() for m in matches],
        "summary": summary,
    }


medicines_checker_tool = Tool(
    name="medicines_checker",
    description=(
        "Check whether a specific medicine is on the NHIS Medicines List. "
        "Returns the best matches with brand and generic names, strength, form, coverage "
        "status, and the levels of care at which it is normally available."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Brand or generic name of the medicine to check.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of fuzzy matches to return (default 5).",
                "default": 5,
                "minimum": 1,
                "maximum": 10,
            },
        },
        "required": ["name"],
    },
    handler=_handler,
)
