"""Shared helpers for the UI/UX + accessibility (WCAG 2.2 AA) audit.

Wraps axe-core-python so every page in the audit (and later, regression checks for
confirmed accessibility bugs) runs the same scan the same way.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from axe_core_python.sync_playwright import Axe
from playwright.sync_api import Page

# axe-core rules that are noisy/unreliable on third-party map/chart widgets this app embeds
# (Leaflet tiles, chart canvases) and are better judged manually; everything else from the
# default ruleset (wcag2a, wcag2aa, wcag21aa, wcag22aa tags) stays on.
DEFAULT_OPTIONS = {
    "runOnly": {
        "type": "tag",
        "values": ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"],
    }
}

_axe = Axe()


@dataclass
class AxeFinding:
    rule_id: str
    impact: str  # "minor" | "moderate" | "serious" | "critical"
    help_text: str
    help_url: str
    wcag_tags: list[str]
    node_count: int
    sample_html: str
    sample_target: str

    def wcag_criteria(self) -> str:
        tags = [t for t in self.wcag_tags if t.startswith("wcag") and t[4:6].isdigit()]
        return ", ".join(tags) if tags else ""


def run_axe_scan(page: Page, *, options: dict | None = None) -> list[AxeFinding]:
    """Run an axe-core scan on the current page and return violations only (not passes)."""
    results = _axe.run(page, options=options or DEFAULT_OPTIONS)
    findings = []
    for violation in results.get("violations", []):
        nodes = violation.get("nodes", [])
        sample = nodes[0] if nodes else {}
        findings.append(
            AxeFinding(
                rule_id=violation["id"],
                impact=violation.get("impact") or "unknown",
                help_text=violation.get("help", ""),
                help_url=violation.get("helpUrl", ""),
                wcag_tags=violation.get("tags", []),
                node_count=len(nodes),
                sample_html=sample.get("html", ""),
                sample_target=", ".join(sample.get("target", [])) if sample else "",
            )
        )
    findings.sort(key=lambda f: ["minor", "moderate", "serious", "critical"].index(f.impact) if f.impact in
                   ("minor", "moderate", "serious", "critical") else -1, reverse=True)
    return findings


def summarize_findings(findings: list[AxeFinding]) -> str:
    if not findings:
        return "axe-core: no violations"
    counts = {}
    for f in findings:
        counts[f.impact] = counts.get(f.impact, 0) + 1
    parts = ", ".join(f"{n} {impact}" for impact, n in counts.items())
    return f"axe-core: {len(findings)} violation type(s) ({parts})"
