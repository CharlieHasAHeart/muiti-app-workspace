import re
from dataclasses import dataclass, field
from typing import Callable

from .llm_front_matter_judge import FrontMatterJudgeResult, OpenAICompatibleFrontMatterJudge
from .llm_heading_judge import HeadingJudgeResult, OpenAICompatibleHeadingJudge

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S.*?)\s*$")
MANUAL_TOC_TITLE_RE = re.compile(r"^目录$")
MANUAL_TOC_ITEM_RE = re.compile(
    r"^\s*(?:"
    r"第\s*[0-9一二三四五六七八九十百千]+\s*(?:章|节|部分|篇)"
    r"|[一二三四五六七八九十百千]+[、.]"
    r"|\d+(?:\.\d+)*"
    r"|[0-9]+[、.]"
    r")"
)
SKIPPABLE_TRAILING_TITLES = {"word 排版使用提示", "排版使用提示", "使用提示"}
STRONG_FALSE_TITLE_PATTERNS = (
    re.compile(r"^第\s*([0-9]+|[一二三四五六七八九十百千]+)\s*(章|节|部分|篇)"),
    re.compile(r"^[一二三四五六七八九十百千]+\s*[、.]"),
    re.compile(r"^\d+(?:\.\d+)*\s*$"),
    re.compile(r"^\d+\s*[、.]"),
)


@dataclass
class HeadingInfo:
    line_no: int
    level: int
    text: str


@dataclass
class ManualTocCandidate:
    title_line_no: int
    end_line_no: int
    title_text: str
    items: list[str] = field(default_factory=list)
    heading_match_ratio: float = 0.0


@dataclass
class MarkdownScanResult:
    lines: list[str]
    headings: list[HeadingInfo]
    manual_toc_candidate: ManualTocCandidate | None = None
    trailing_notes_start_line: int | None = None


@dataclass
class FrontMatterPlan:
    has_subtitle: bool = False
    subtitle_text: str = ""
    subtitle_line: int | None = None
    confidence: float = 0.0
    reason: str = ""
    source: str = "none"


@dataclass
class HeadingNormalizationPlan:
    has_document_title: bool = False
    title_text: str = ""
    heading_shift: int = 0
    confidence: float = 0.0
    reason: str = ""
    source: str = "none"
    remove_manual_toc: bool = False
    manual_toc_start_line: int | None = None
    manual_toc_end_line: int | None = None
    remove_trailing_notes: bool = False
    trailing_notes_start_line: int | None = None
    skip_first_h1_in_body: bool = False


@dataclass
class RuleResult:
    has_document_title: bool | None = None
    skip_first_h1_in_body: bool | None = None
    heading_shift: int | None = None
    manual_toc_range: tuple[int, int] | None = None
    remove_manual_toc: bool | None = None
    trailing_notes_start_line: int | None = None
    remove_trailing_notes: bool | None = None
    subtitle_text: str | None = None
    subtitle_line: int | None = None
    title_text: str | None = None
    reasons: list[str] = field(default_factory=list)


@dataclass
class LLMResult:
    has_document_title: bool | None = None
    skip_first_h1_in_body: bool | None = None
    heading_shift: int | None = None
    remove_manual_toc: bool | None = None
    subtitle_text: str | None = None
    subtitle_line: int | None = None
    title_text: str | None = None
    confidence: float = 0.0
    reason: str = ""
    source: str = "none"


@dataclass
class FinalResult:
    has_document_title: bool = False
    skip_first_h1_in_body: bool = False
    heading_shift: int = 0
    remove_manual_toc: bool = False
    manual_toc_range: tuple[int, int] | None = None
    remove_trailing_notes: bool = False
    trailing_notes_start_line: int | None = None
    subtitle_text: str = ""
    subtitle_line: int | None = None
    title_text: str = ""
    source: str = "rule"
    reason: str = ""


@dataclass
class DecisionPlan:
    scan: MarkdownScanResult
    rule_result: RuleResult
    llm_result: LLMResult
    final_result: FinalResult
    heading_plan: HeadingNormalizationPlan
    front_matter_plan: FrontMatterPlan


def extract_headings(md_text: str) -> list[HeadingInfo]:
    headings: list[HeadingInfo] = []
    for line_no, line in enumerate(md_text.splitlines(), start=1):
        match = HEADING_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        text = match.group(2).strip()
        headings.append(HeadingInfo(line_no=line_no, level=level, text=text))
    return headings


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).strip().lower()


def _is_strong_chapter_title(text: str) -> bool:
    stripped = text.strip()
    return any(pattern.match(stripped) for pattern in STRONG_FALSE_TITLE_PATTERNS)


def detect_manual_toc_candidate(lines: list[str], headings: list[HeadingInfo]) -> ManualTocCandidate | None:
    if not headings:
        return None

    heading_texts = {_normalize_text(h.text) for h in headings if h.level >= 2}
    for idx, heading in enumerate(headings):
        if heading.level < 2 or not MANUAL_TOC_TITLE_RE.match(heading.text.strip()):
            continue

        next_heading_line = headings[idx + 1].line_no if idx + 1 < len(headings) else len(lines) + 1
        raw_block = [lines[line_no - 1].strip() for line_no in range(heading.line_no + 1, next_heading_line)]
        items = [line for line in raw_block if line and not line.startswith('---')]
        if len(items) < 2:
            continue

        normalized_items = {_normalize_text(item) for item in items}
        matched_lines = [
            item for item in normalized_items
            if any(text in item or item in text for text in heading_texts)
        ]
        numbered_items = [line for line in items if MANUAL_TOC_ITEM_RE.match(line)]
        if len(numbered_items) < max(1, len(items) // 3) and len(matched_lines) < max(2, len(items) // 2):
            continue

        matched = len(matched_lines)
        ratio = matched / max(1, len(normalized_items))
        if ratio < 0.5:
            continue

        return ManualTocCandidate(
            title_line_no=heading.line_no,
            end_line_no=next_heading_line - 1,
            title_text=heading.text,
            items=items,
            heading_match_ratio=ratio,
        )
    return None


def detect_trailing_notes_start(headings: list[HeadingInfo]) -> int | None:
    for heading in reversed(headings):
        if heading.text.strip().lower() in SKIPPABLE_TRAILING_TITLES:
            return heading.line_no
    return None


def scan_markdown(md_text: str) -> MarkdownScanResult:
    lines = md_text.splitlines()
    headings = extract_headings(md_text)
    return MarkdownScanResult(
        lines=lines,
        headings=headings,
        manual_toc_candidate=detect_manual_toc_candidate(lines, headings),
        trailing_notes_start_line=detect_trailing_notes_start(headings),
    )


def should_consult_llm(scan: MarkdownScanResult) -> bool:
    headings = scan.headings
    if len(headings) < 3:
        return False

    h1_headings = [heading for heading in headings if heading.level == 1]
    if len(h1_headings) != 1:
        return False

    first_heading = headings[0]
    if first_heading.level != 1 or first_heading.line_no > 3:
        return False

    remaining_levels = {heading.level for heading in headings[1:]}
    if not remaining_levels or min(remaining_levels) < 2:
        return False

    max_level = max(heading.level for heading in headings)
    if max_level < 3:
        return False

    return True


def build_heading_outline(headings: list[HeadingInfo], limit: int = 24) -> str:
    lines = []
    for heading in headings[:limit]:
        indent = "  " * (heading.level - 1)
        lines.append(f"{indent}- L{heading.level} @ line {heading.line_no}: {heading.text}")
    if len(headings) > limit:
        lines.append(f"... ({len(headings) - limit} more headings omitted)")
    return "\n".join(lines)


def build_context_excerpt(md_text: str, max_lines: int = 80) -> str:
    lines = md_text.splitlines()
    excerpt = lines[:max_lines]
    return "\n".join(excerpt)


def first_body_heading(scan: MarkdownScanResult) -> HeadingInfo | None:
    for heading in scan.headings:
        if heading.level >= 2 and heading.text != "目录":
            return heading
    return scan.headings[1] if len(scan.headings) > 1 else None


def build_front_matter_lines(scan: MarkdownScanResult, max_lines: int = 60) -> str:
    body_heading = first_body_heading(scan)
    end_line = body_heading.line_no - 1 if body_heading else len(scan.lines)
    end_line = min(end_line, max_lines)
    lines = []
    for line_no in range(1, end_line + 1):
        lines.append(f"{line_no}: {scan.lines[line_no - 1]}")
    return "\n".join(lines)


def build_first_body_heading_summary(scan: MarkdownScanResult) -> str:
    heading = first_body_heading(scan)
    if heading is None:
        return "none"
    return f"line {heading.line_no}, level {heading.level}, text: {heading.text}"


def build_manual_toc_summary(candidate: ManualTocCandidate | None, limit: int = 12) -> str:
    if candidate is None:
        return "none"
    items = candidate.items[:limit]
    summary = [
        f"title line: {candidate.title_line_no}",
        f"end line: {candidate.end_line_no}",
        f"heading match ratio: {candidate.heading_match_ratio:.2f}",
        "items:",
    ]
    summary.extend(f"- {item}" for item in items)
    if len(candidate.items) > limit:
        summary.append(f"... ({len(candidate.items) - limit} more items omitted)")
    return "\n".join(summary)


def _judge_with_env(scan: MarkdownScanResult, md_text: str) -> HeadingJudgeResult | None:
    judge = OpenAICompatibleHeadingJudge.from_env()
    if judge is None:
        return None
    return judge.judge(
        heading_outline=build_heading_outline(scan.headings),
        context_excerpt=build_context_excerpt(md_text),
        manual_toc_summary=build_manual_toc_summary(scan.manual_toc_candidate),
    )


def _judge_front_matter_with_env(scan: MarkdownScanResult) -> FrontMatterJudgeResult | None:
    judge = OpenAICompatibleFrontMatterJudge.from_env()
    if judge is None:
        return None
    return judge.judge(
        front_matter_lines=build_front_matter_lines(scan),
        heading_outline=build_heading_outline(scan.headings),
        first_body_heading=build_first_body_heading_summary(scan),
    )


def build_rule_result(scan: MarkdownScanResult) -> RuleResult:
    result = RuleResult(
        remove_trailing_notes=scan.trailing_notes_start_line is not None,
        trailing_notes_start_line=scan.trailing_notes_start_line,
    )

    if scan.manual_toc_candidate is not None:
        result.manual_toc_range = (
            scan.manual_toc_candidate.title_line_no,
            scan.manual_toc_candidate.end_line_no,
        )
        result.reasons.append("Detected a manual TOC candidate block.")

    if scan.headings:
        first_heading = scan.headings[0]
        result.title_text = first_heading.text
        h1_headings = [heading for heading in scan.headings if heading.level == 1]
        if len(h1_headings) == 1 and first_heading.level == 1 and first_heading.line_no <= 3:
            if _is_strong_chapter_title(first_heading.text):
                result.has_document_title = False
                result.skip_first_h1_in_body = False
                result.heading_shift = 0
                result.reasons.append("First H1 looks like a strong chapter heading.")

    return result


def build_llm_result(
    scan: MarkdownScanResult,
    md_text: str,
    heading_judge: Callable[[MarkdownScanResult, str], HeadingJudgeResult | None] | None = None,
    front_matter_judge: Callable[[MarkdownScanResult], FrontMatterJudgeResult | None] | None = None,
) -> LLMResult:
    result = LLMResult()

    heading_result = None
    if should_consult_llm(scan):
        heading_result = (heading_judge or _judge_with_env)(scan, md_text)
    if heading_result is not None:
        result.has_document_title = heading_result.has_document_title
        result.heading_shift = heading_result.heading_shift
        result.skip_first_h1_in_body = heading_result.has_document_title
        result.remove_manual_toc = heading_result.remove_manual_toc
        result.title_text = scan.headings[0].text if scan.headings and heading_result.has_document_title else None
        result.confidence = max(result.confidence, heading_result.confidence)
        result.reason = heading_result.reason
        result.source = heading_result.source

    front_matter_result = (front_matter_judge or _judge_front_matter_with_env)(scan)
    if front_matter_result is not None:
        result.subtitle_text = front_matter_result.subtitle_text if front_matter_result.has_subtitle else None
        result.subtitle_line = front_matter_result.subtitle_line if front_matter_result.has_subtitle else None
        if front_matter_result.confidence >= result.confidence:
            result.confidence = front_matter_result.confidence
            if front_matter_result.reason:
                result.reason = front_matter_result.reason
            result.source = front_matter_result.source

    return result


def fuse_decision_results(scan: MarkdownScanResult, rule_result: RuleResult, llm_result: LLMResult) -> FinalResult:
    final = FinalResult(
        remove_trailing_notes=bool(rule_result.remove_trailing_notes),
        trailing_notes_start_line=rule_result.trailing_notes_start_line,
        manual_toc_range=rule_result.manual_toc_range,
        title_text=rule_result.title_text or (scan.headings[0].text if scan.headings else ""),
    )

    reasons: list[str] = []
    sources: list[str] = []

    if rule_result.remove_trailing_notes:
        reasons.append("Rule removed trailing notes block.")
        sources.append("rule")

    if rule_result.has_document_title is not None:
        final.has_document_title = rule_result.has_document_title
        final.skip_first_h1_in_body = bool(rule_result.skip_first_h1_in_body)
        final.heading_shift = rule_result.heading_shift or 0
        reasons.extend(rule_result.reasons)
        sources.append("rule")
    else:
        final.has_document_title = bool(llm_result.has_document_title)
        final.skip_first_h1_in_body = bool(llm_result.skip_first_h1_in_body)
        final.heading_shift = llm_result.heading_shift or 0
        if llm_result.title_text:
            final.title_text = llm_result.title_text
        if llm_result.reason:
            reasons.append(llm_result.reason)
        if llm_result.source != "none":
            sources.append(llm_result.source)

    if rule_result.remove_manual_toc is not None:
        final.remove_manual_toc = rule_result.remove_manual_toc
        sources.append("rule")
    elif rule_result.manual_toc_range is not None and llm_result.remove_manual_toc is True:
        final.remove_manual_toc = True
        reasons.append("Rule located a TOC candidate and LLM confirmed removal.")
        sources.extend(["rule", llm_result.source])
    else:
        final.remove_manual_toc = False

    if llm_result.subtitle_text:
        final.subtitle_text = llm_result.subtitle_text
        final.subtitle_line = llm_result.subtitle_line
        sources.append(llm_result.source)
    else:
        final.subtitle_text = rule_result.subtitle_text or ""
        final.subtitle_line = rule_result.subtitle_line
        if rule_result.subtitle_text:
            sources.append("rule")

    if not final.has_document_title and final.subtitle_text and scan.headings:
        first_heading = scan.headings[0]
        body_heading = first_body_heading(scan)
        if first_heading.level == 1 and first_heading.line_no <= 3 and body_heading is not None and body_heading.level >= 2:
            if not _is_strong_chapter_title(first_heading.text):
                final.has_document_title = True
                final.skip_first_h1_in_body = True
                if final.heading_shift == 0 and body_heading.level >= 2:
                    final.heading_shift = -1
                reasons.append("Promoted first H1 to document title because subtitle exists before body headings.")
                sources.append("rule")

    deduped_sources = [source for i, source in enumerate(sources) if source and source != "none" and source not in sources[:i]]
    final.source = "+".join(deduped_sources) if deduped_sources else "rule"
    final.reason = " ".join(reason for reason in reasons if reason).strip()
    return final


def to_heading_plan(final_result: FinalResult) -> HeadingNormalizationPlan:
    plan = HeadingNormalizationPlan(
        has_document_title=final_result.has_document_title,
        title_text=final_result.title_text,
        heading_shift=final_result.heading_shift,
        reason=final_result.reason,
        source=final_result.source,
        remove_manual_toc=final_result.remove_manual_toc,
        remove_trailing_notes=final_result.remove_trailing_notes,
        trailing_notes_start_line=final_result.trailing_notes_start_line,
        skip_first_h1_in_body=final_result.skip_first_h1_in_body,
    )
    if final_result.manual_toc_range is not None:
        plan.manual_toc_start_line, plan.manual_toc_end_line = final_result.manual_toc_range
    return plan


def to_front_matter_plan(final_result: FinalResult, llm_result: LLMResult) -> FrontMatterPlan:
    return FrontMatterPlan(
        has_subtitle=bool(final_result.subtitle_text),
        subtitle_text=final_result.subtitle_text,
        subtitle_line=final_result.subtitle_line,
        confidence=llm_result.confidence if final_result.subtitle_text else 0.0,
        reason=llm_result.reason if final_result.subtitle_text else "",
        source=llm_result.source if final_result.subtitle_text else "none",
    )


def judge_front_matter_subtitle(md_text: str, scan: MarkdownScanResult | None = None) -> FrontMatterPlan:
    scan = scan or scan_markdown(md_text)
    result = _judge_front_matter_with_env(scan)
    if result is None or not result.has_subtitle or not result.subtitle_text:
        return FrontMatterPlan(
            has_subtitle=False,
            confidence=result.confidence if result else 0.0,
            reason=result.reason if result else "LLM front-matter judge returned no result",
            source=result.source if result else "none",
        )
    return FrontMatterPlan(
        has_subtitle=True,
        subtitle_text=result.subtitle_text,
        subtitle_line=result.subtitle_line,
        confidence=result.confidence,
        reason=result.reason,
        source=result.source,
    )


def analyze_heading_normalization(
    md_text: str,
    judge: Callable[[MarkdownScanResult, str], HeadingJudgeResult | None] | None = None,
) -> HeadingNormalizationPlan:
    decision = build_decision_plan(md_text, heading_judge=judge)
    return decision.heading_plan


def build_decision_plan(
    md_text: str,
    heading_judge: Callable[[MarkdownScanResult, str], HeadingJudgeResult | None] | None = None,
    front_matter_judge: Callable[[MarkdownScanResult], FrontMatterJudgeResult | None] | None = None,
) -> DecisionPlan:
    scan = scan_markdown(md_text)
    rule_result = build_rule_result(scan)
    llm_result = build_llm_result(
        scan,
        md_text,
        heading_judge=heading_judge,
        front_matter_judge=front_matter_judge,
    )
    final_result = fuse_decision_results(scan, rule_result, llm_result)
    heading_plan = to_heading_plan(final_result)
    front_matter_plan = to_front_matter_plan(final_result, llm_result)
    return DecisionPlan(
        scan=scan,
        rule_result=rule_result,
        llm_result=llm_result,
        final_result=final_result,
        heading_plan=heading_plan,
        front_matter_plan=front_matter_plan,
    )


def normalize_markdown_with_decision(md_text: str, decision: DecisionPlan) -> str:
    normalized = normalize_markdown_for_render(md_text, decision.heading_plan)
    if decision.final_result.subtitle_line is not None:
        lines = normalized.splitlines()
        normalized = "\n".join(
            line for idx, line in enumerate(lines, start=1) if idx != decision.final_result.subtitle_line
        )
    return normalized


def normalize_markdown_for_render(md_text: str, plan: HeadingNormalizationPlan) -> str:
    if not any([
        plan.remove_manual_toc,
        plan.remove_trailing_notes,
    ]):
        return md_text

    lines = md_text.splitlines()
    kept: list[str] = []
    for line_no, line in enumerate(lines, start=1):
        if plan.remove_manual_toc and plan.manual_toc_start_line and plan.manual_toc_end_line:
            if plan.manual_toc_start_line <= line_no <= plan.manual_toc_end_line:
                continue
        if plan.remove_trailing_notes and plan.trailing_notes_start_line and line_no >= plan.trailing_notes_start_line:
            continue
        kept.append(line)
    return "\n".join(kept)
