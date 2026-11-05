"""
Small 8-week trend line charts for the per-process-type daily briefing (5 Nov 2026).

User, 5 Nov: "lets add line chart as trend line". One PNG per process-type card: a row of small line charts,
one per metric (FTA, Efficiency vs its own baseline, CoQ, Yield when the process type has it), each with its
reference line (FTA target, 100% = baseline, CoQ level, Yield target). Full weeks are a solid line; the
current week, still in progress, is a dotted segment to a hollow point, so a half week does not read as a drop.
Rules and drawing only, no AI. The PNG goes into the email as an inline image (cid), so Outlook shows it
without "download pictures"; see delivery._send_email(inline_images=...).
"""
from __future__ import annotations

import io
import math
from datetime import date

import matplotlib

matplotlib.use("Agg")   # no display on the Azure job or in tests
import matplotlib.pyplot as plt  # noqa: E402

from config import COQ_MONITOR, FTA_TARGET, YIELD_TARGET  # noqa: E402

# (series key, title, reference value, reference label, higher is better)
PANELS = (
    ("fta", "FTA", FTA_TARGET, f"target {FTA_TARGET:g}%", True),
    ("eff_vs_bl", "Eff vs own baseline", 100.0, "baseline", True),
    ("coq", "CoQ", COQ_MONITOR, f"level {COQ_MONITOR:g}%", False),
    ("yield", "Yield", YIELD_TARGET, f"target {YIELD_TARGET:g}%", True),
)
_LINE, _GOOD, _BAD, _REF, _MUTED = "#1B2A4A", "#1E8449", "#922B21", "#8A96A8", "#6B7A8D"
WIDTH_PX = 600          # shown size in the email; drawn at 2x for sharp text
HEIGHT_PX = 150
DPI = 160


def _short(week: str) -> str:
    """'2 Nov' for '2026-11-02'."""
    d = date.fromisoformat(str(week)[:10])
    return f"{d.day} {d.strftime('%b')}"


def _num(v) -> float:
    """Float, or NaN for a missing value (a gap in the line). Yield above 100% is not a real yield: a gap."""
    return float("nan") if v is None else float(v)


def panels_for(series: list[dict]) -> list[tuple]:
    """The PANELS this series has data for (Yield only for Orbit SD process types)."""
    return [p for p in PANELS if any(w.get(p[0]) is not None for w in series)]


def trend_png(series: list[dict], in_progress: bool) -> bytes:
    """One row of small line charts for one process type's weekly series (oldest first); `in_progress` =
    the last week is the current, unfinished one. Returns PNG bytes."""
    panels = panels_for(series)
    n = max(1, len(panels))
    # drawn at twice the shown size so text stays sharp on high-DPI screens
    fig, axes = plt.subplots(1, n, figsize=(WIDTH_PX * 2 / DPI, HEIGHT_PX * 2 / DPI), dpi=DPI, squeeze=False)
    xs = list(range(len(series)))
    labels = [_short(w["week"]) for w in series]
    for ax, (key, title, ref, ref_label, higher) in zip(axes[0], panels):
        ys = [_num(w.get(key) if not (key == "yield" and (w.get(key) or 0) > 100) else None) for w in series]
        full = ys[:-1] if in_progress else ys
        ax.plot(xs[:len(full)], full, color=_LINE, linewidth=1.6, marker="o", markersize=2.8)
        if in_progress and len(ys) >= 2 and not math.isnan(ys[-1]):
            prev = next((i for i in range(len(ys) - 2, -1, -1) if not math.isnan(ys[i])), None)
            if prev is not None:
                ax.plot([xs[prev], xs[-1]], [ys[prev], ys[-1]], color=_LINE, linewidth=1.2, linestyle=":")
            ax.plot([xs[-1]], [ys[-1]], marker="o", markersize=4, markerfacecolor="white", markeredgecolor=_LINE)
        ax.axhline(ref, color=_REF, linewidth=0.9, linestyle="--")
        ax.text(xs[0], ref, f" {ref_label}", color=_MUTED, fontsize=6, va="bottom", ha="left")
        last = next((v for v in reversed(ys) if not math.isnan(v)), None)
        ok = last is not None and (last >= ref if higher else last < ref)
        fmt = "{:.0f}%" if key == "eff_vs_bl" else "{:.1f}%"
        ax.set_title(f"{title}  " + (fmt.format(last) if last is not None else "—"), fontsize=7.5, loc="left",
                     color=_GOOD if ok else _BAD if last is not None else _MUTED, fontweight="bold")
        vals = [v for v in ys if not math.isnan(v)] + [ref]
        lo, hi = min(vals), max(vals)
        pad = max(1.0, (hi - lo) * 0.15)
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_xticks([xs[0], xs[-1]])
        ax.set_xticklabels([labels[0], labels[-1] + (" so far" if in_progress else "")], fontsize=6, color=_MUTED)
        ax.tick_params(axis="y", labelsize=6, colors=_MUTED, length=2)
        ax.tick_params(axis="x", length=2)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#D5DBE2")
    fig.tight_layout(pad=0.4, w_pad=0.8)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI)
    plt.close(fig)
    return buf.getvalue()
