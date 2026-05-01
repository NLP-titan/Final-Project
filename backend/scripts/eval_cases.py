"""Eval script with questions and gold answers sourced from the NHIS knowledge base.

Cases are built from three sources:
  medicines.csv   – 6 drug queries (3 covered, 3 not-covered) — hard GT check
  facilities.csv  – 6 facility queries (5 accredited, 1 not-accredited) — hard GT check
  policy .md docs – 17 policy queries (6 coverage, 6 enrollment, 5 disputes)
                    evaluated with LLM-as-judge (score 1–3, pass = ≥ 2)

Run:
    python -m scripts.eval_cases                     # heuristic, no LLM judge
    python -m scripts.eval_cases --provider openai   # full LLM path + LLM judge
    python -m scripts.eval_cases --provider anthropic

Results written to data/processed/eval_results.json
Generated cases written to data/processed/eval_cases_generated.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import orchestrator  # noqa: E402
from app.config import settings     # noqa: E402


# ── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class EvalCase:
    case_id: str
    category: str
    question: str
    expected_tool: str
    gold_context: str               # verbatim text from the KB (CSV row or section)
    check_type: Literal["bool_match", "llm_judge"]
    expected_bool: bool | None = None   # True=covered/accredited (bool_match only)
    source_ref: str = ""


@dataclass
class EvalResult:
    case_id: str
    category: str
    question: str
    expected_tool: str
    tool_called: list[str]
    tool_match: bool
    answer_excerpt: str
    correct: bool
    judge_score: int | None     # 1–3 for policy cases; None for hard-GT cases
    provider: str
    check_type: str


# ── CSV helper ────────────────────────────────────────────────────────────────

def _load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ── Medicine cases ────────────────────────────────────────────────────────────

_MED_QUESTIONS = {
    True: [
        "Is {name} covered by NHIS?",
        "Should I pay for {name} at an NHIS facility?",
        "Is {name} on the NHIS medicines list?",
    ],
    False: [
        "Is {name} available on the NHIS formulary?",
        "Will NHIS pay for my {name} prescription?",
        "Does NHIS cover {name}?",
    ],
}

_COVERED_PICKS     = ["Paracetamol", "Artemether-Lumefantrine", "Insulin (Soluble)"]
_NOT_COVERED_PICKS = ["Tenofovir/Lamivudine/Dolutegravir", "Erythropoietin", "Imatinib"]


def build_medicine_cases(csv_path: Path) -> list[EvalCase]:
    rows = {r["name"]: r for r in _load_csv(csv_path)}
    cases = []
    for i, name in enumerate(_COVERED_PICKS + _NOT_COVERED_PICKS):
        row = rows[name]
        covered = row["covered"].strip().lower() == "yes"
        template = _MED_QUESTIONS[covered][i % 3]
        gold_context = (
            f"Medicine: {row['name']} ({row.get('generic_name', '')})\n"
            f"Form: {row.get('form', '')} {row.get('strength', '')}\n"
            f"Covered by NHIS: {row['covered']}\n"
            f"Level of care: {row.get('level_of_care', '')}\n"
            f"Notes: {row.get('notes', '')}"
        )
        cases.append(EvalCase(
            case_id=f"med_{i:02d}",
            category="medicines",
            question=template.format(name=name),
            expected_tool="medicines_checker",
            gold_context=gold_context,
            check_type="bool_match",
            expected_bool=covered,
            source_ref=f"medicines.csv: {name}",
        ))
    return cases


# ── Facility cases ────────────────────────────────────────────────────────────

_FAC_QUESTIONS = [
    "Is {name} NHIS-accredited?",
    "Can I use my NHIS card at {name}?",
    "Does {name} accept NHIS?",
    "Is {name} a recognised NHIS facility?",
    "Is {name} an accredited NHIS provider?",
    "Can I receive NHIS-covered services at {name}?",
]

_FAC_ACCREDITED_PICKS     = [
    "Korle Bu Teaching Hospital",
    "Komfo Anokye Teaching Hospital",
    "Ridge Hospital",
    "Tema General Hospital",
    "Trust Hospital",
]
_FAC_NOT_ACCREDITED_PICKS = ["Nyaho Medical Centre"]


def build_facility_cases(csv_path: Path) -> list[EvalCase]:
    rows = {r["name"]: r for r in _load_csv(csv_path)}
    cases = []
    for i, name in enumerate(_FAC_ACCREDITED_PICKS + _FAC_NOT_ACCREDITED_PICKS):
        row = rows[name]
        accredited = row["accredited"].strip().lower() == "yes"
        status = row.get("accreditation_status", "").strip()
        gold_context = (
            f"Facility: {row['name']}\n"
            f"Type: {row.get('type', '')}\n"
            f"Region: {row.get('region', '')}, {row.get('district', '')}\n"
            f"NHIS Accredited: {row['accredited']}\n"
            f"Accreditation Status: {status}\n"
            f"Services: {row.get('services', '')}"
        )
        cases.append(EvalCase(
            case_id=f"fac_{i:02d}",
            category="facilities",
            question=_FAC_QUESTIONS[i].format(name=name),
            expected_tool="facility_checker",
            gold_context=gold_context,
            check_type="bool_match",
            expected_bool=accredited and status.lower() == "active",
            source_ref=f"facilities.csv: {name}",
        ))
    return cases


# ── Policy cases ──────────────────────────────────────────────────────────────

# (category, question, policy_file, section_heading)
_POLICY_SPEC: list[tuple[str, str, str, str]] = [
    # coverage — sourced from 01_benefits_package.md
    ("coverage", "What outpatient services does NHIS cover?",
     "01_benefits_package.md", "Outpatient services"),
    ("coverage", "What inpatient services are covered under NHIS?",
     "01_benefits_package.md", "Inpatient services"),
    ("coverage", "Does NHIS cover emergency stabilisation?",
     "01_benefits_package.md", "Emergency services"),
    ("coverage", "What eye care does NHIS cover?",
     "01_benefits_package.md", "Eye care"),
    ("coverage", "What services are excluded from the NHIS benefit package?",
     "01_benefits_package.md", "What is NOT covered (exclusion list)"),
    ("coverage", "Can I be charged a co-payment at an NHIS facility?",
     "01_benefits_package.md", "How co-payment works"),
    # enrollment — sourced from 02_membership_and_renewal.md
    ("enrollment", "Who is eligible for NHIS membership?",
     "02_membership_and_renewal.md", "Eligibility"),
    ("enrollment", "How do I register for NHIS for the first time?",
     "02_membership_and_renewal.md", "How to register"),
    ("enrollment", "How do I renew my NHIS membership?",
     "02_membership_and_renewal.md", "Renewal"),
    ("enrollment", "Is there a waiting period for new NHIS members?",
     "02_membership_and_renewal.md", "Waiting period for new members"),
    ("enrollment", "What do I do if I lose my NHIS card?",
     "02_membership_and_renewal.md", "Replacement of lost cards"),
    ("enrollment", "How much does NHIS membership cost?",
     "02_membership_and_renewal.md", "Premiums"),
    # disputes — sourced from 03_disputes_and_rights.md
    ("disputes", "What are my rights as an active NHIS member at a facility?",
     "03_disputes_and_rights.md", "Member rights at accredited facilities"),
    ("disputes", "What actions by a facility violate my NHIS rights?",
     "03_disputes_and_rights.md", "What constitutes a violation"),
    ("disputes", "How do I file a complaint against an NHIS facility?",
     "03_disputes_and_rights.md", "How to file a complaint"),
    ("disputes", "How long does NHIS take to resolve a complaint?",
     "03_disputes_and_rights.md", "Timelines"),
    ("disputes", "What evidence should I keep when filing an NHIS complaint?",
     "03_disputes_and_rights.md", "What you should keep"),
]


def _extract_section(md_text: str, heading: str) -> str:
    """Return the body text of a named section (any heading level)."""
    if md_text.startswith("---"):
        end = md_text.find("---", 3)
        if end != -1:
            md_text = md_text[end + 3:].lstrip()

    pattern = re.compile(
        r'^(#{1,3})\s+' + re.escape(heading) + r'\s*$', re.MULTILINE
    )
    m = pattern.search(md_text)
    if not m:
        return f"[Section '{heading}' not found in document]"

    level = len(m.group(1))
    start = m.end()
    next_hdg = re.compile(r'^#{1,' + str(level) + r'}\s', re.MULTILINE)
    nxt = next_hdg.search(md_text, start)
    end = nxt.start() if nxt else len(md_text)
    return md_text[start:end].strip()


def build_policy_cases(policies_dir: Path) -> list[EvalCase]:
    cases = []
    for i, (cat, question, filename, section) in enumerate(_POLICY_SPEC):
        md_text = (policies_dir / filename).read_text(encoding="utf-8")
        gold_context = _extract_section(md_text, section)
        cases.append(EvalCase(
            case_id=f"pol_{i:02d}",
            category=cat,
            question=question,
            expected_tool="policy_retriever",
            gold_context=gold_context,
            check_type="llm_judge",
            source_ref=f"{filename}: {section}",
        ))
    return cases


# ── Evaluation ────────────────────────────────────────────────────────────────

_COVERED_YES = frozenset([
    "covered", "on the nhis", "included", "formulary", "nhis pays",
    "free of charge", "entitled", "available on", "benefit package",
])
_COVERED_NO = frozenset([
    "not covered", "excluded", "not included", "not on the nhis",
    "pay out", "not available on", "not in the formulary", "not a benefit",
    "outside the", "no, it is not",
])

_ACCREDITED_YES = frozenset([
    "accredited", "active", "nhis-accredited", "nhis facility",
    "accepted", "valid nhis",
])
_ACCREDITED_NO = frozenset([
    "not accredited", "suspended", "not accepted", "does not accept nhis",
    "no nhis", "not a nhis", "not currently accredited",
])


def _bool_check(answer: str, expected: bool, category: str) -> bool:
    low = answer.lower()
    if category == "medicines":
        if any(p in low for p in _COVERED_NO):
            return not expected
        if any(p in low for p in _COVERED_YES):
            return expected
    elif category == "facilities":
        if any(p in low for p in _ACCREDITED_NO):
            return not expected
        if any(p in low for p in _ACCREDITED_YES):
            return expected
    return False    # ambiguous — mark incorrect


_JUDGE_PROMPT = """\
You are evaluating an AI assistant's answer against a verified ground-truth extract \
from the Ghana NHIS knowledge base.

Ground-truth (from the NHIS knowledge base):
---
{gold_context}
---

Agent's answer:
---
{answer}
---

Rate how well the answer reflects the ground-truth on a 1–3 scale:
3 = Correct and complete — key facts accurately stated
2 = Partially correct — right direction but some details missing or imprecise
1 = Incorrect — contradicts or significantly misrepresents the policy

Reply with ONLY the digit (1, 2, or 3) and nothing else."""


def _llm_judge(gold_context: str, answer: str, judge_model: str) -> int | None:
    """Score an answer 1–3 against the gold context using a separate judge model.

    judge_model is an OpenRouter model string (e.g. "openai/gpt-4o",
    "anthropic/claude-3-5-sonnet"). Kept separate from the agent model so the
    judge is independent of the system under evaluation.
    """
    if not settings.openai_api_key:
        return None
    prompt = _JUDGE_PROMPT.format(
        gold_context=gold_context[:1500],
        answer=answer[:800],
    )
    try:
        from openai import OpenAI
        resp = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openai_api_key,
        ).chat.completions.create(
            model=judge_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,  
        )
        text = (resp.choices[0].message.content or "").strip()
        hit = re.search(r"[123]", text)
        return int(hit.group()) if hit else None
    except Exception as exc:
        print(f"  [judge error: {exc}]")
        return None


def run_one(case: EvalCase, judge_model: str) -> EvalResult:
    resp = orchestrator.answer(case.question)
    tool_names = [tc["name"] for tc in resp.tool_calls]
    tool_match = case.expected_tool in tool_names
    answer_text = resp.answer or ""

    if case.check_type == "bool_match":
        correct = _bool_check(answer_text, case.expected_bool, case.category)
        judge_score = None
    else:
        judge_score = _llm_judge(case.gold_context, answer_text, judge_model)
        correct = judge_score is not None and judge_score >= 2

    return EvalResult(
        case_id=case.case_id,
        category=case.category,
        question=case.question,
        expected_tool=case.expected_tool,
        tool_called=tool_names,
        tool_match=tool_match,
        answer_excerpt=answer_text[:280],
        correct=correct,
        judge_score=judge_score,
        provider=resp.provider,
        check_type=case.check_type,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the NHIS agent against KB-sourced questions and gold answers."
    )
    parser.add_argument("--provider", default=None, help="Override LLM_PROVIDER for this run.")
    parser.add_argument(
        "--judge-model",
        default=None,
        help="OpenRouter model string for the LLM judge (default: JUDGE_MODEL from .env). "
             "Should differ from the agent model to avoid self-grading. "
             "Example: openai/gpt-4o  or  anthropic/claude-3-5-sonnet",
    )
    parser.add_argument("--out", default=None, help="Path to write JSON results.")
    args = parser.parse_args()

    if args.provider:
        settings.llm_provider = args.provider

    judge_model = args.judge_model or settings.judge_model

    raw_dir = Path(settings.policies_dir).parent
    cases: list[EvalCase] = (
        build_medicine_cases(raw_dir / "medicines.csv")
        + build_facility_cases(raw_dir / "facilities.csv")
        + build_policy_cases(Path(settings.policies_dir))
    )

    cases_path = Path(settings.chroma_persist_dir).parent / "eval_cases_generated.json"
    cases_path.parent.mkdir(parents=True, exist_ok=True)
    cases_path.write_text(json.dumps([asdict(c) for c in cases], indent=2), encoding="utf-8")
    print(f"Built {len(cases)} cases  →  {cases_path}\n")

    print(f"Running {len(cases)} cases  (provider={settings.llm_provider!r}, judge={judge_model!r}) …")
    results = [run_one(c, judge_model) for c in cases]

    by_cat: dict[str, list[EvalResult]] = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    print(f"\n{'CAT':<12} {'TOOL':<5} {'CORRECT':<8} {'JUDGE':<6} QUESTION")
    print("-" * 110)
    total_tool = total_correct = 0
    for r in results:
        judge_str = str(r.judge_score) if r.judge_score is not None else "-"
        print(
            f"{r.category:<12} "
            f"{'OK' if r.tool_match else 'MISS':<5} "
            f"{'OK' if r.correct else 'MISS':<8} "
            f"{judge_str:<6} "
            f"{r.question}"
        )
        total_tool += int(r.tool_match)
        total_correct += int(r.correct)

    n = len(results)
    print("-" * 110)
    print(f"Tool routing accuracy:  {total_tool}/{n} ({total_tool / n:.0%})")
    print(f"Answer correctness:     {total_correct}/{n} ({total_correct / n:.0%})")
    for cat, items in by_cat.items():
        c_tool = sum(1 for r in items if r.tool_match)
        c_ans  = sum(1 for r in items if r.correct)
        scores = [r.judge_score for r in items if r.judge_score is not None]
        avg    = f"  avg_judge={sum(scores)/len(scores):.2f}" if scores else ""
        print(f"  {cat:<12} tool {c_tool}/{len(items)}  correct {c_ans}/{len(items)}{avg}")

    out_path = Path(args.out) if args.out else (
        Path(settings.chroma_persist_dir).parent / "eval_results.json"
    )
    out_path.write_text(json.dumps([asdict(r) for r in results], indent=2), encoding="utf-8")
    print(f"\nDetailed results  →  {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
