"""30 evaluation cases covering the five scenario categories from the project brief.

Run with:
    python -m scripts.eval_cases                # heuristic fallback (no API key)
    python -m scripts.eval_cases --provider anthropic   # use the configured LLM

Results are printed as a table and written to data/processed/eval_results.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import orchestrator  # noqa: E402
from app.config import settings  # noqa: E402


# (category, question, expected_tool, expected_substring_in_answer)
EVAL_CASES: list[tuple[str, str, str, str]] = [
    # Coverage queries (6)
    ("coverage", "Is dialysis covered under NHIS?", "policy_retriever", "dialysis"),
    ("coverage", "Does NHIS pay for caesarean section?", "policy_retriever", "caesarean"),
    ("coverage", "Is cancer treatment covered by NHIS?", "policy_retriever", "cancer"),
    ("coverage", "Are eye care services like cataract surgery covered?", "policy_retriever", "cataract"),
    ("coverage", "Will NHIS cover my IVF treatment?", "policy_retriever", "reproduction"),
    ("coverage", "Does NHIS cover emergency stabilisation?", "policy_retriever", "emerg"),

    # Drug entitlement (6)
    ("medicines", "Should I pay for Paracetamol at the clinic?", "medicines_checker", "Paracetamol"),
    ("medicines", "Is Artemether-Lumefantrine on the NHIS list?", "medicines_checker", "Artemether"),
    ("medicines", "Is insulin a covered medication?", "medicines_checker", "Insulin"),
    ("medicines", "Will NHIS pay for my Imatinib prescription?", "medicines_checker", "Imatinib"),
    ("medicines", "Is amoxicillin covered for my child?", "medicines_checker", "Amoxicillin"),
    ("medicines", "Is Tenofovir/Lamivudine/Dolutegravir covered by NHIS?", "medicines_checker", "Tenofovir"),

    # Facility accreditation (6)
    ("facilities", "Is Korle Bu Teaching Hospital NHIS-accredited?", "facility_checker", "Korle Bu"),
    ("facilities", "Is Komfo Anokye Teaching Hospital accredited?", "facility_checker", "Komfo Anokye"),
    ("facilities", "Is Nyaho Medical Centre accredited under NHIS?", "facility_checker", "Nyaho"),
    ("facilities", "Is Tema General Hospital NHIS accredited?", "facility_checker", "Tema"),
    ("facilities", "Is the Trust Hospital in Osu accredited?", "facility_checker", "Trust"),
    ("facilities", "Is Ridge Hospital in Greater Accra accredited?", "facility_checker", "Ridge"),

    # Membership / renewal (6)
    ("enrollment", "My NHIS card expired, what do I do?", "policy_retriever", "renew"),
    ("enrollment", "How do I register for NHIS for the first time?", "policy_retriever", "register"),
    ("enrollment", "Can I use the *929# short code to renew?", "policy_retriever", "*929#"),
    ("enrollment", "Do pregnant women pay a premium?", "policy_retriever", "pregnant"),
    ("enrollment", "Is the Ghana Card the same as my NHIS card?", "policy_retriever", "Ghana Card"),
    ("enrollment", "How long does it take for my new NHIS membership to become active?", "policy_retriever", "waiting"),

    # Rights / disputes (6)
    ("disputes", "The pharmacy at the hospital asked me to buy my drug outside, is that allowed?", "policy_retriever", "outside"),
    ("disputes", "They turned me away because I had no cash even though I have NHIS, what are my rights?", "policy_retriever", "rights"),
    ("disputes", "Where do I file an NHIS complaint?", "policy_retriever", "complaint"),
    ("disputes", "How long does NHIS take to respond to a complaint?", "policy_retriever", "working days"),
    ("disputes", "Can I be charged for a service that is on the benefit package?", "policy_retriever", "co-payment"),
    ("disputes", "Should I keep receipts when filing a complaint?", "policy_retriever", "receipt"),
]


def run_one(case: tuple[str, str, str, str]) -> dict:
    category, question, expected_tool, expected_substr = case
    resp = orchestrator.answer(question)
    tool_names = [tc["name"] for tc in resp.tool_calls]
    tool_match = expected_tool in tool_names
    substr_match = expected_substr.lower() in (resp.answer or "").lower()
    return {
        "category": category,
        "question": question,
        "expected_tool": expected_tool,
        "tool_called": tool_names,
        "tool_match": tool_match,
        "expected_substring": expected_substr,
        "substring_match": substr_match,
        "answer_excerpt": (resp.answer or "")[:280],
        "provider": resp.provider,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default=None, help="Override LLM_PROVIDER for this run.")
    parser.add_argument("--out", default=None, help="Path to write JSON results.")
    args = parser.parse_args()

    if args.provider:
        settings.llm_provider = args.provider

    results = [run_one(case) for case in EVAL_CASES]

    by_cat: dict[str, list[dict]] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r)

    print(f"\n{'CAT':<11} {'TOOL':<5} {'SUBSTR':<7} QUESTION")
    print("-" * 100)
    correct_tool = 0
    correct_substr = 0
    for r in results:
        print(
            f"{r['category']:<11} "
            f"{'OK' if r['tool_match'] else 'MISS':<5} "
            f"{'OK' if r['substring_match'] else 'MISS':<7} "
            f"{r['question']}"
        )
        correct_tool += int(r["tool_match"])
        correct_substr += int(r["substring_match"])

    n = len(results)
    print("-" * 100)
    print(f"Tool routing accuracy:    {correct_tool}/{n} ({correct_tool / n:.0%})")
    print(f"Answer substring recall:  {correct_substr}/{n} ({correct_substr / n:.0%})")
    for cat, items in by_cat.items():
        c_tool = sum(1 for r in items if r["tool_match"])
        c_sub = sum(1 for r in items if r["substring_match"])
        print(f"  {cat:<11} tool {c_tool}/{len(items)}  substr {c_sub}/{len(items)}")

    out_path = Path(args.out) if args.out else (
        Path(settings.chroma_persist_dir).parent / "eval_results.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote detailed results to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
