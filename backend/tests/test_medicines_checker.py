"""Medicines checker tool — DB-backed."""
from app.agent.tools.medicines_checker import medicines_checker_tool


def test_paracetamol_is_covered():
    out = medicines_checker_tool.run({"name": "paracetamol"})
    assert out["matches"], out
    assert out["matches"][0]["covered"] is True
    assert "NHIS Medicines List" in out["summary"]


def test_imatinib_is_not_covered():
    out = medicines_checker_tool.run({"name": "Imatinib"})
    assert out["matches"], out
    assert out["matches"][0]["covered"] is False
    assert "NOT" in out["summary"]


def test_unknown_medicine_returns_no_matches():
    out = medicines_checker_tool.run({"name": "Floofazole-XYZ-9999"})
    assert out["matches"] == []
    assert "No medicine" in out["summary"]


def test_missing_name_argument_errors():
    out = medicines_checker_tool.run({})
    assert "error" in out
