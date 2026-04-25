from app.agent.tools.facility_checker import facility_checker_tool


def test_korle_bu_is_accredited():
    out = facility_checker_tool.run({"name": "Korle Bu"})
    assert out["matches"], out
    top = out["matches"][0]
    assert top["accredited"] is True
    assert "NHIS-accredited" in out["summary"]


def test_nyaho_is_not_accredited():
    out = facility_checker_tool.run({"name": "Nyaho Medical Centre"})
    assert out["matches"], out
    top = out["matches"][0]
    assert top["accredited"] is False
    assert "NOT actively" in out["summary"]


def test_region_filter_narrows_results():
    out = facility_checker_tool.run({"name": "Regional Hospital", "region": "Volta"})
    assert out["matches"], out
    assert all(m["region"] == "Volta" for m in out["matches"])


def test_unknown_facility_returns_no_matches():
    out = facility_checker_tool.run({"name": "ZZZ Nonexistent Clinic XYZ"})
    assert out["matches"] == []
    assert "No facility" in out["summary"]
