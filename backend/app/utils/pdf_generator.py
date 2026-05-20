"""
PDF 생성 유틸리티 (reportlab 기반).

급여대장: A4 세로, APPROVED 상태 기준, 합계행 포함
상담일지: A4 세로, 단건/다건
"""
import io
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_STYLES = getSampleStyleSheet()

_TABLE_HEADER_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DAEEF3")),
    ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
    ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
    ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ("GRID",       (0, 0), (-1, -1), 0.5, colors.black),
    ("FONTSIZE",   (0, 0), (-1, -1), 9),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
])

_TITLE_STYLE = _STYLES["Title"]
_TITLE_STYLE.fontSize = 14
_TITLE_STYLE.spaceAfter = 6


# ── 급여대장 PDF ──────────────────────────────────────────────────────────────

def generate_salary_statement_pdf(
    year: int,
    month: int,
    business_unit_name: str,
    records: List[Dict[str, Any]],
) -> bytes:
    """
    급여대장 PDF 생성 (A4 세로).

    records: APPROVED 상태 근무기록
    [{"name": str, "birth_date": str, "worked_hours": float, "amount_paid": int}]
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    title_text = f"{year}년 {month}월 급여대장 — {business_unit_name}"
    elements = [
        Paragraph(title_text, _TITLE_STYLE),
        Spacer(1, 4 * mm),
    ]

    method_label = f"{year}-{month:02d}"
    headers = ["사업단명", "연월", "성명", "생년월일", "근무시간", "지급금액", "서명"]
    data = [headers]

    total_amount = 0
    for rec in records:
        data.append([
            business_unit_name,
            method_label,
            rec.get("name", ""),
            str(rec.get("birth_date", "")),
            str(rec.get("worked_hours", 0)),
            f"{rec.get('amount_paid', 0):,}원",
            "",
        ])
        total_amount += rec.get("amount_paid", 0)

    # 합계행
    data.append(["합계", "", "", "", "", f"{total_amount:,}원", ""])

    col_widths = [35 * mm, 18 * mm, 18 * mm, 22 * mm, 18 * mm, 26 * mm, 20 * mm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle(list(_TABLE_HEADER_STYLE._cmds))
    # 합계 행 굵게
    style.add("FONTNAME", (0, len(data) - 1), (-1, len(data) - 1), "Helvetica-Bold")
    style.add("BACKGROUND", (0, len(data) - 1), (-1, len(data) - 1), colors.HexColor("#F1F3F4"))
    table.setStyle(style)

    elements.append(table)
    doc.build(elements)
    return buf.getvalue()


# ── 상담일지 PDF ──────────────────────────────────────────────────────────────

def generate_consultation_log_pdf(
    logs: List[Dict[str, Any]],
    senior_name: str = "",
) -> bytes:
    """
    상담일지 PDF 생성 (A4 세로).

    logs: [{"consultation_date", "method", "content", "memo",
            "social_worker_name", "default_session_hours"}]
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    title_text = f"상담일지{' — ' + senior_name if senior_name else ''}"
    elements = [
        Paragraph(title_text, _TITLE_STYLE),
        Spacer(1, 4 * mm),
    ]

    method_map = {"phone": "전화", "visit": "방문", "in_person": "내방", "other": "기타"}
    headers = ["상담일시", "상담방법", "상담내용", "담당자", "기본시간", "메모"]
    data = [headers]

    for log in logs:
        method = method_map.get(log.get("method", ""), log.get("method", ""))
        data.append([
            str(log.get("consultation_date", "")),
            method,
            log.get("content", ""),
            log.get("social_worker_name", ""),
            str(log.get("default_session_hours", "")),
            log.get("memo", ""),
        ])

    col_widths = [30 * mm, 18 * mm, 55 * mm, 22 * mm, 16 * mm, 30 * mm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle(list(_TABLE_HEADER_STYLE._cmds))
    # 내용 열은 좌측 정렬
    style.add("ALIGN", (2, 1), (2, -1), "LEFT")
    style.add("ALIGN", (5, 1), (5, -1), "LEFT")
    table.setStyle(style)

    elements.append(table)
    doc.build(elements)
    return buf.getvalue()
