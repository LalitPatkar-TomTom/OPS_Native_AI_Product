"""
Data Fetcher  -  a generic partitioned-archive scanning engine.

It knows how to walk a folder of partitions, open archives inside them, and
pull rows out of a delimited file. It does NOT know what a CC rule is, what
"violations.csv" is, or that products are called OA and ON. All of that is
handed to it by the master agent, from the process spec.

READ-ONLY against the source. It opens archives and reads members. It never
creates, moves, renames or deletes anything in the source folder.

The shape it understands:

    <root>/
        <partition>/              a run, a batch, a date - whatever the spec says
            <archive>.zip
                <index member>    small; says whether the key is present at all
                <data member>     the rows we actually want

The index member is why this is fast enough to be useful. Opening every data
member to look for one key would mean reading gigabytes; the index is a few
kilobytes and answers "is it in here?" first.

Driven entirely by a source config - see `sources.violation_logs` in the
process spec for a worked example.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ==========================================================================
# Configuration, as handed over by the master agent
# ==========================================================================
@dataclass
class PartitionSpec:
    """How to recognise and order the partitions under the root."""
    pattern: str                       # regex with named groups
    order_by: list[str]                # named groups, in sort precedence
    label: str                         # e.g. "{product}_{major}.{minor}{suffix}"
    group_by: str | None = None        # each value is an independent series
    numeric_groups: list[str] = field(default_factory=list)

    def compiled(self) -> re.Pattern:
        return re.compile(self.pattern)


@dataclass
class ArchiveSpec:
    glob: str = "*.zip"
    name_pattern: str | None = None     # optional, for naming/filtering
    name_filter_group: str | None = None
    name_filter_values: list[str] | None = None


@dataclass
class MemberSpec:
    data: str                           # the file holding the rows we want
    index: str | None = None            # optional cheap pre-filter file


@dataclass
class FilterSpec:
    column: str
    equals: str


@dataclass
class IndexSpec:
    """Columns in the index member, used to pre-filter and to count."""
    key: str
    count: str | None = None
    group: str | None = None


@dataclass
class SearchSpec:
    latest_only: bool = True
    fallback_partitions: int = 1


@dataclass
class SourceConfig:
    root: Path
    partitions: PartitionSpec
    members: MemberSpec
    filter: FilterSpec
    archives: ArchiveSpec = field(default_factory=ArchiveSpec)
    index: IndexSpec | None = None
    search: SearchSpec = field(default_factory=SearchSpec)
    max_rows: int = 50_000
    # Which partition series to search. Empty means all of them. The caller
    # decides - for CC rules the spec routes Lanes to one product series and
    # everything else to another, which halves the archives opened.
    series: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, cfg: dict, substitutions: dict[str, str]) -> "SourceConfig":
        def sub(value: Any) -> Any:
            if isinstance(value, str):
                for k, v in substitutions.items():
                    value = value.replace("{" + k + "}", str(v))
            return value

        p = cfg["partitions"]
        m = cfg["members"]
        f = cfg["filter"]

        return cls(
            root=Path(sub(cfg["root"])).expanduser(),
            partitions=PartitionSpec(
                pattern=p["pattern"],
                order_by=p.get("order_by", []),
                label=p.get("label", "{0}"),
                group_by=p.get("group_by"),
                numeric_groups=p.get("numeric_groups", []),
            ),
            members=MemberSpec(data=m["data"], index=m.get("index")),
            filter=FilterSpec(column=f["column"], equals=str(sub(f["equals"]))),
            archives=ArchiveSpec(**cfg.get("archives", {})),
            index=IndexSpec(**cfg["index"]) if cfg.get("index") else None,
            search=SearchSpec(**{k: v for k, v in cfg.get("search", {}).items()
                                 if k in ("latest_only", "fallback_partitions")}),
            max_rows=cfg.get("max_rows", 50_000),
            series=list(cfg.get("series") or []),
        )


# ==========================================================================
# Discovery
# ==========================================================================
@dataclass
class Partition:
    path: Path
    groups: dict[str, str]
    label: str
    series: str | None

    def sort_key(self, spec: PartitionSpec) -> tuple:
        out = []
        for name in spec.order_by:
            raw = self.groups.get(name) or ""
            if name in spec.numeric_groups:
                out.append((0, int(raw) if raw.isdigit() else 0))
            else:
                out.append((1, raw))
        return tuple(out)


def discover_partitions(cfg: SourceConfig) -> dict[str | None, list[Partition]]:
    """Find every partition under the root, grouped into independent series.

    Anything whose name does not match the pattern is ignored - which is how
    stray folders (samples, tests, references) stay out of the way without
    needing to be listed.
    """
    rx = cfg.partitions.compiled()
    found: dict[str | None, list[Partition]] = {}

    if not cfg.root.exists():
        return found

    for child in sorted(cfg.root.iterdir()):
        if not child.is_dir():
            continue
        m = rx.match(child.name)
        if not m:
            continue
        groups = {k: (v or "") for k, v in m.groupdict().items()}
        series = groups.get(cfg.partitions.group_by) if cfg.partitions.group_by else None
        label = cfg.partitions.label.format(**groups) if cfg.partitions.label else child.name
        found.setdefault(series, []).append(
            Partition(path=child, groups=groups, label=label, series=series)
        )

    for series, parts in found.items():
        parts.sort(key=lambda p: p.sort_key(cfg.partitions))
    return found


# ==========================================================================
# Reading
# ==========================================================================
@dataclass
class FetchResult:
    key: str
    rows: list[dict] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    counts: list[dict] = field(default_factory=list)
    partitions_scanned: list[str] = field(default_factory=list)
    partitions_used: list[str] = field(default_factory=list)
    archives_opened: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def count_per_partition(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for c in self.counts:
            try:
                out[c["partition"]] = out.get(c["partition"], 0) + int(c["count"] or 0)
            except (TypeError, ValueError):
                continue
        return out


def _read_csv(zf: zipfile.ZipFile, name: str) -> tuple[list[str], list[list[str]]]:
    raw = zf.read(name).decode("utf-8", errors="replace")
    rows = list(csv.reader(io.StringIO(raw)))
    return (rows[0], rows[1:]) if rows else ([], [])


def _scan_archive(
    archive: Path, cfg: SourceConfig
) -> tuple[list[dict], list[dict], list[str], list[str]]:
    """Read one archive. Returns (rows, counts, columns, warnings)."""
    warnings: list[str] = []
    try:
        with zipfile.ZipFile(archive) as zf:
            names = set(zf.namelist())
            counts: list[dict] = []
            present = True

            # Cheap pre-filter: does the index say the key is in here at all?
            if cfg.index and cfg.members.index and cfg.members.index in names:
                present = False
                header, rows = _read_csv(zf, cfg.members.index)
                try:
                    i_key = header.index(cfg.index.key)
                except ValueError:
                    warnings.append(
                        f"{archive.name}: index has no column {cfg.index.key!r}")
                    return [], [], [], warnings
                i_count = (header.index(cfg.index.count)
                           if cfg.index.count and cfg.index.count in header else None)
                i_group = (header.index(cfg.index.group)
                           if cfg.index.group and cfg.index.group in header else None)
                for r in rows:
                    if len(r) > i_key and r[i_key] == cfg.filter.equals:
                        present = True
                        counts.append({
                            "group": r[i_group] if i_group is not None and len(r) > i_group else "",
                            "count": r[i_count] if i_count is not None and len(r) > i_count else "0",
                        })

            if not present:
                return [], counts, [], warnings

            if cfg.members.data not in names:
                warnings.append(f"{archive.name}: no member {cfg.members.data!r}")
                return [], counts, [], warnings

            header, rows = _read_csv(zf, cfg.members.data)
            try:
                i_filter = header.index(cfg.filter.column)
            except ValueError:
                warnings.append(
                    f"{archive.name}: data has no column {cfg.filter.column!r}")
                return [], counts, [], warnings

            matched = [dict(zip(header, r)) for r in rows
                       if len(r) > i_filter and r[i_filter] == cfg.filter.equals]
            return matched, counts, header, warnings

    except zipfile.BadZipFile:
        warnings.append(f"{archive.name}: not a readable archive")
    except OSError as exc:
        warnings.append(f"{archive.name}: {exc}")
    return [], [], [], warnings


def _scan_partition(part: Partition, cfg: SourceConfig, result: FetchResult) -> int:
    found = 0
    rx = re.compile(cfg.archives.name_pattern) if cfg.archives.name_pattern else None

    for archive in sorted(part.path.glob(cfg.archives.glob)):
        if rx and cfg.archives.name_filter_group and cfg.archives.name_filter_values:
            m = rx.match(archive.name)
            value = m.group(cfg.archives.name_filter_group) if m else ""
            if not any(value.startswith(v) for v in cfg.archives.name_filter_values):
                continue

        result.archives_opened += 1
        rows, counts, header, warns = _scan_archive(archive, cfg)
        result.warnings.extend(warns)

        for c in counts:
            result.counts.append({"partition": part.label, **c})

        if rows:
            if header and not result.columns:
                result.columns = header
            room = cfg.max_rows - len(result.rows)
            if room <= 0:
                result.warnings.append(
                    f"row cap of {cfg.max_rows:,} reached; output is truncated")
                break
            result.rows.extend(rows[:room])
            found += len(rows)
    return found


def fetch(cfg: SourceConfig) -> FetchResult:
    """Search each series for the key, newest partition first.

    If the newest partition does not contain the key, step back one partition
    at a time up to `fallback_partitions`. A key absent from all of them is
    reported as not found, rather than searched for through the whole history.
    """
    result = FetchResult(key=cfg.filter.equals)

    if not cfg.root.exists():
        result.warnings.append(f"source folder not found: {cfg.root}")
        return result

    series_map = discover_partitions(cfg)
    if not series_map:
        result.warnings.append(f"no partitions matched under {cfg.root}")
        return result

    depth = 1 + max(0, cfg.search.fallback_partitions) if cfg.search.latest_only else None

    if cfg.series:
        wanted = {str(s) for s in cfg.series}
        skipped = [k for k in series_map if k is not None and k not in wanted]
        series_map = {k: v for k, v in series_map.items()
                      if k is None or k in wanted}
        if skipped:
            result.warnings.append(
                "not searched (routed elsewhere): " + ", ".join(sorted(skipped)))
        if not series_map:
            result.warnings.append(
                f"no partitions for series {sorted(wanted)}")
            return result

    for series, parts in series_map.items():
        candidates = list(reversed(parts))
        if depth is not None:
            candidates = candidates[:depth]
        if not candidates:
            continue

        name = series or "all"
        for step, part in enumerate(candidates):
            result.partitions_scanned.append(part.label)
            if _scan_partition(part, cfg, result):
                result.partitions_used.append(part.label)
                if step:
                    result.warnings.append(
                        f"{name}: key not in the latest partition "
                        f"({candidates[0].label}); used {part.label} instead")
                break
        else:
            tried = ", ".join(c.label for c in candidates)
            result.warnings.append(f"{name}: key {cfg.filter.equals} not found in {tried}")

    return result


# ==========================================================================
# Output
# ==========================================================================
def write_xlsx(result: FetchResult, out_path: Path, title: str) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    head_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="1F3864")

    ws = wb.active
    ws.title = "Summary"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 34

    ws["A1"] = title
    ws["A1"].font = Font(name="Arial", size=14, bold=True, color="1F3864")

    reported = sum(result.count_per_partition().values())
    facts = [
        ("Rows in this extract", result.row_count),
        ("Source used", ", ".join(result.partitions_used) or "none"),
        ("Searched", ", ".join(result.partitions_scanned)),
        ("Archives opened", result.archives_opened),
    ]
    # State the shortfall on the first sheet, in plain words. Someone opening
    # this file must not have to notice that a row count looks suspiciously
    # round in order to realise it is incomplete.
    if reported > result.row_count:
        facts.insert(1, ("Total reported at source", reported))
        facts.insert(2, ("THIS EXTRACT IS CAPPED",
                         f"{reported - result.row_count:,} violations are not "
                         f"in this file"))
    r = 3
    for label, value in facts:
        ws.cell(r, 1, label).font = Font(name="Arial", size=10, bold=True)
        ws.cell(r, 2, value).font = Font(name="Arial", size=10)
        r += 1

    per = result.count_per_partition()
    if per:
        r += 1
        ws.cell(r, 1, "Count per source").font = Font(
            name="Arial", size=11, bold=True, color="1F3864")
        r += 1
        for col, label in enumerate(["Source", "Count"], start=1):
            c = ws.cell(r, col, label)
            c.font, c.fill = head_font, head_fill
        r += 1
        for key, count in sorted(per.items()):
            ws.cell(r, 1, key).font = Font(name="Arial", size=10)
            ws.cell(r, 2, count).font = Font(name="Arial", size=10)
            r += 1

    if result.warnings:
        r += 1
        ws.cell(r, 1, "Notes").font = Font(name="Arial", size=11, bold=True,
                                           color="C00000")
        r += 1
        for w in result.warnings[:30]:
            c = ws.cell(r, 1, w)
            c.font = Font(name="Arial", size=9, color="7F7F7F")
            c.alignment = Alignment(wrap_text=True)
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
            r += 1

    if result.rows:
        ws2 = wb.create_sheet("Data")
        cols = result.columns or list(result.rows[0].keys())
        for i, name in enumerate(cols, start=1):
            c = ws2.cell(1, i, name)
            c.font, c.fill = head_font, head_fill
            ws2.column_dimensions[c.column_letter].width = min(40, max(12, len(name) + 4))
        for ri, row in enumerate(result.rows, start=2):
            for ci, name in enumerate(cols, start=1):
                ws2.cell(ri, ci, row.get(name, ""))
        ws2.freeze_panes = "A2"
        ws2.auto_filter.ref = ws2.dimensions

    wb.save(out_path)
    return out_path


# ==========================================================================
def _scan_archive_multi(
    archive: Path, cfg: SourceConfig, keys: set[str]
) -> tuple[dict[str, list[dict]], dict[str, list[dict]], list[str], list[str]]:
    """Open one archive once and pull rows for EVERY key at the same time.

    This is the whole point of batching: the expensive work is decompressing
    and parsing the data member, and that cost is paid once here regardless of
    how many keys are wanted.
    """
    warnings: list[str] = []
    rows: dict[str, list[dict]] = {}
    counts: dict[str, list[dict]] = {}
    header: list[str] = []

    try:
        with zipfile.ZipFile(archive) as zf:
            names = set(zf.namelist())
            present = set(keys)

            # The index is small, so use it to narrow the keys before touching
            # the data member at all.
            if cfg.index and cfg.members.index and cfg.members.index in names:
                present = set()
                ih, irows = _read_csv(zf, cfg.members.index)
                try:
                    i_key = ih.index(cfg.index.key)
                except ValueError:
                    return {}, {}, [], [
                        f"{archive.name}: index has no column {cfg.index.key!r}"]
                i_count = (ih.index(cfg.index.count)
                           if cfg.index.count in ih else None)
                i_group = (ih.index(cfg.index.group)
                           if cfg.index.group in ih else None)
                for r in irows:
                    if len(r) <= i_key:
                        continue
                    k = r[i_key]
                    if k in keys:
                        present.add(k)
                        counts.setdefault(k, []).append({
                            "group": r[i_group] if i_group is not None and len(r) > i_group else "",
                            "count": r[i_count] if i_count is not None and len(r) > i_count else "0",
                        })

            if not present:
                return {}, counts, [], warnings

            if cfg.members.data not in names:
                return {}, counts, [], [
                    f"{archive.name}: no member {cfg.members.data!r}"]

            header, drows = _read_csv(zf, cfg.members.data)
            try:
                i_filter = header.index(cfg.filter.column)
            except ValueError:
                return {}, counts, [], [
                    f"{archive.name}: data has no column {cfg.filter.column!r}"]

            for r in drows:
                if len(r) <= i_filter:
                    continue
                k = r[i_filter]
                if k in present:
                    rows.setdefault(k, []).append(dict(zip(header, r)))

    except zipfile.BadZipFile:
        warnings.append(f"{archive.name}: not a readable archive")
    except OSError as exc:
        warnings.append(f"{archive.name}: {exc}")

    return rows, counts, header, warnings


def fetch_many(cfg_dict: dict, keys: list[str], *,
               series: list[str] | None = None) -> dict[str, FetchResult]:
    """Fetch several keys in ONE pass over the archives.

    Calling fetch() once per key re-reads the same archives every time, and
    the cost is dominated by decompressing and parsing the data member - tens
    of thousands of rows per archive. Reading each archive once and picking out
    every requested key together turns N x 2 minutes into roughly 2 minutes.

    "Latest partition, then one back" still applies per key: keys found in the
    newest partition are finished there, and only the ones still missing cause
    the older partition to be opened.
    """
    results: dict[str, FetchResult] = {k: FetchResult(key=k) for k in keys}
    if not keys:
        return results

    base = dict(cfg_dict)
    if series:
        base["series"] = series
    probe = SourceConfig.from_dict(base, {"rule_id": keys[0]})

    if not probe.root.exists():
        for r in results.values():
            r.warnings.append(f"source folder not found: {probe.root}")
        return results

    series_map = discover_partitions(probe)
    if probe.series:
        wanted = {str(s) for s in probe.series}
        series_map = {k: v for k, v in series_map.items()
                      if k is None or k in wanted}

    depth = 1 + max(0, probe.search.fallback_partitions)

    for name, parts in series_map.items():
        outstanding = {k for k in keys if not results[k].rows}
        for part in list(reversed(parts))[:depth]:
            if not outstanding:
                break
            for k in outstanding:
                results[k].partitions_scanned.append(part.label)

            for archive in sorted(part.path.glob(probe.archives.glob)):
                if not outstanding:
                    break
                rows_by_key, counts_by_key, header, warns = _scan_archive_multi(
                    archive, probe, outstanding)
                for k in outstanding:
                    results[k].archives_opened += 1
                if warns:
                    for k in outstanding:
                        results[k].warnings.extend(warns)

                for key, clist in counts_by_key.items():
                    for c in clist:
                        results[key].counts.append({"partition": part.label, **c})

                for key, rlist in rows_by_key.items():
                    res = results[key]
                    if header and not res.columns:
                        res.columns = header
                    room = probe.max_rows - len(res.rows)
                    res.rows.extend(rlist[:max(0, room)])
                    if part.label not in res.partitions_used:
                        res.partitions_used.append(part.label)

            outstanding = {k for k in outstanding if not results[k].rows}

        for key in keys:
            if not results[key].rows:
                results[key].warnings.append(
                    f"{name or 'all'}: key {key} not found in the partitions searched")

    return results


def run(task: dict) -> dict:
    """Agent entry point. The master agent passes the source config and the
    substitutions to apply to it. This agent supplies no defaults of its own."""
    source = dict(task["source"])
    substitutions = task.get("substitutions", {})
    # The caller may narrow the search to particular series.
    if task.get("series"):
        source["series"] = task["series"]
    cfg = SourceConfig.from_dict(source, substitutions)

    result = fetch(cfg)

    payload = {
        "key": result.key,
        "row_count": result.row_count,
        "count_per_partition": result.count_per_partition(),
        "partitions_used": result.partitions_used,
        "partitions_scanned": result.partitions_scanned,
        "archives_opened": result.archives_opened,
        "warnings": result.warnings,
        "file_path": None,
    }

    if task.get("output") and (result.rows or result.counts):
        out = Path(task["output"]["dir"]) / task["output"]["filename"].format(
            **substitutions)
        payload["file_path"] = str(write_xlsx(
            result, out, task["output"].get("title", "Extract").format(**substitutions)))

    return payload
