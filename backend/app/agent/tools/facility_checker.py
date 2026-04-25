"""Facility Checker tool — fuzzy lookup against the accredited facilities directory."""
from __future__ import annotations

from app.agent.tools.base import Tool
from app.data_access import facilities_db


def _handler(args: dict) -> dict:
    name = (args.get("name") or "").strip()
    region = args.get("region")
    limit = int(args.get("limit", 5))
    if not name:
        return {"error": "Missing required argument: name"}

    matches = facilities_db.search_facility(name, region=region, limit=limit)
    if not matches:
        scope = f" in {region}" if region else ""
        return {
            "query": name,
            "region": region,
            "matches": [],
            "summary": (
                f"No facility matching '{name}'{scope} was found in the accredited "
                "directory. Verify against the latest NHIA accredited list before assuming "
                "non-accreditation."
            ),
        }
    top = matches[0]
    if top.accredited and top.accreditation_status.lower() == "active":
        summary = (
            f"'{top.name}' ({top.type}) in {top.town}, {top.region} is NHIS-accredited "
            f"(status: {top.accreditation_status}). Services on file: "
            f"{', '.join(top.services) or 'unspecified'}."
        )
    else:
        summary = (
            f"'{top.name}' ({top.type}) in {top.town}, {top.region} is NOT actively "
            f"accredited (status: {top.accreditation_status or 'Not Accredited'}). The "
            "member should expect to pay out of pocket there for non-emergencies."
        )
    return {
        "query": name,
        "region": region,
        "matches": [m.to_dict() for m in matches],
        "summary": summary,
    }


facility_checker_tool = Tool(
    name="facility_checker",
    description=(
        "Check whether a hospital or clinic is NHIS-accredited. "
        "Returns the best matches with type, region, accreditation status and services."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the facility (or part of it) to look up.",
            },
            "region": {
                "type": "string",
                "description": "Optional region to filter the search (e.g. 'Greater Accra').",
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
