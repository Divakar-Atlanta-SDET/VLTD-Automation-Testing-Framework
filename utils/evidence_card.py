"""
Renders a clean "evidence card" PNG for an API-only bug - for Jira attachments where there is no distinct UI
screenshot to take (the page looks normal; only the network response proves the defect).

Usage: build the HTML with `evidence_card_html(...)`, then screenshot it with any Playwright `Page`:
    page.set_content(evidence_card_html(...))
    page.locator("#card").screenshot(path=out_path)
"""

import html
import json
from datetime import date


def _pretty(body: str | dict | None) -> str:
    if body is None:
        return "(no body)"
    if isinstance(body, (dict, list)):
        return json.dumps(body, indent=2)
    try:
        return json.dumps(json.loads(body), indent=2)
    except (ValueError, TypeError):
        return str(body)


def evidence_card_html(
    *,
    bug_id: str,
    title: str,
    severity: str,
    method: str,
    path: str,
    status: int,
    role: str = "",
    request_body: str | dict | None = None,
    response_body: str | dict | None = None,
    note: str = "",
) -> str:
    severity_color = {
        "Highest": "#b91c1c", "High": "#c2410c", "Medium": "#b45309", "Low": "#4b5563",
    }.get(severity, "#4b5563")
    status_color = "#15803d" if 200 <= status < 300 else "#b91c1c"
    req = html.escape(_pretty(request_body))
    resp = html.escape(_pretty(response_body))
    role_line = f'<div class="meta">Signed in as: <b>{html.escape(role)}</b></div>' if role else ""
    note_block = f'<div class="note">{html.escape(note)}</div>' if note else ""
    req_block = (
        f'<div class="block"><div class="label">Request body</div><pre>{req}</pre></div>' if request_body is not None else ""
    )

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
  body {{ margin: 0; background: #f3f4f6; font-family: -apple-system, Segoe UI, Arial, sans-serif; }}
  #card {{ width: 920px; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 28px 32px;
           box-sizing: border-box; }}
  .top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }}
  .bugid {{ font-size: 13px; font-weight: 700; color: #374151; letter-spacing: 0.04em; }}
  .severity {{ font-size: 12px; font-weight: 700; color: #fff; background: {severity_color};
               padding: 3px 10px; border-radius: 999px; }}
  h1 {{ font-size: 19px; margin: 10px 0 4px; color: #111827; }}
  .meta {{ font-size: 13px; color: #4b5563; margin-bottom: 14px; }}
  .call {{ display: flex; align-items: center; gap: 10px; background: #0f172a; color: #e5e7eb; border-radius: 8px;
           padding: 10px 14px; font-family: Consolas, monospace; font-size: 13px; margin-bottom: 14px; }}
  .method {{ font-weight: 700; color: #93c5fd; }}
  .status {{ margin-left: auto; font-weight: 700; color: {status_color}; }}
  .block {{ margin-bottom: 12px; }}
  .label {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
            color: #6b7280; margin-bottom: 4px; }}
  pre {{ background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 10px 12px;
         font-family: Consolas, monospace; font-size: 12.5px; color: #111827; white-space: pre-wrap;
         word-break: break-word; margin: 0; max-height: 260px; overflow: hidden; }}
  .note {{ font-size: 12.5px; color: #6b7280; margin-top: 10px; border-top: 1px dashed #e5e7eb; padding-top: 10px; }}
  .footer {{ margin-top: 14px; font-size: 11px; color: #9ca3af; text-align: right; }}
</style></head>
<body>
<div id="card">
  <div class="top"><span class="bugid">{html.escape(bug_id)}</span><span class="severity">{html.escape(severity)}</span></div>
  <h1>{html.escape(title)}</h1>
  {role_line}
  <div class="call"><span class="method">{html.escape(method)}</span><span>{html.escape(path)}</span><span class="status">{status}</span></div>
  {req_block}
  <div class="block"><div class="label">Response</div><pre>{resp}</pre></div>
  {note_block}
  <div class="footer">Captured {date.today().isoformat()} · VLTD staging (https://vltd.misbackend.com)</div>
</div>
</body></html>"""
