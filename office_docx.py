"""회의 결과를 워드 파일로 만듭니다. 1쪽: 아이디어 한 장, 2쪽: 회의록과 배정."""

import io

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

YALE = RGBColor(0x0F, 0x3B, 0x59)
GOLD = RGBColor(0xDB, 0xA1, 0x2C)
INK = RGBColor(0x14, 0x2C, 0x3C)
MUTED = RGBColor(0x5B, 0x72, 0x82)
FONT = "Paperlogy"


def _font(run, size, bold=False, color=INK):
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def _para(doc, text="", size=10, bold=False, color=INK, space_after=4, align=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = 1.25
    if align:
        p.alignment = align
    if text:
        _font(p.add_run(text), size, bold, color)
    return p


def _rule(paragraph, color="0F3B59", size=12):
    pPr = paragraph._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), color)
    bdr.append(bottom)
    pPr.append(bdr)


def _shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def _section(doc, label):
    _para(doc, label, size=10.5, bold=True, color=YALE, space_after=2)


def _idea_page(doc, idea: dict) -> None:

    # 머리
    head = _para(doc, size=8.5, space_after=2)
    _font(head.add_run("BLUE JEANS PICTURES  ·  STORY OFFICE 발제"), 8.5, True, MUTED)
    _font(head.add_run(f"     No. {int(idea.get('no', 0)):03d}  ·  {idea.get('date', '')}"), 8.5, False, MUTED)
    t = _para(doc, idea["title"], size=22, bold=True, color=YALE, space_after=6)
    _rule(t)

    # Idea Engine 입력 칸
    table = doc.add_table(rows=2, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate([("장르", idea["genre"]), ("타겟 시장", idea["market"]), ("선호 포맷", idea["format"])]):
        c0, c1 = table.cell(0, i), table.cell(1, i)
        _shade(c0, "F7FBFC")
        c0.paragraphs[0].paragraph_format.space_after = Pt(0)
        _font(c0.paragraphs[0].add_run(k), 8, True, MUTED)
        _font(c1.paragraphs[0].add_run(v), 10, True, INK)
    _para(doc, "Idea Engine STEP 1 입력값입니다. 제목·장르·타겟 시장·선호 포맷·원본 아이디어 칸에 그대로 옮기면 됩니다.",
          size=7.5, color=MUTED, space_after=8)

    _section(doc, "로그라인")
    _para(doc, idea["logline"], size=11, bold=True, space_after=8)

    _section(doc, "원본 아이디어")
    _para(doc, idea["raw_idea"], size=10, space_after=8)

    _section(doc, "핵심 장면")
    for i, s in enumerate(idea.get("scenes", [])[:3], 1):
        p = _para(doc, size=10, space_after=2)
        _font(p.add_run(f"{i}.  "), 10, True, GOLD)
        _font(p.add_run(s), 10)
    _para(doc, space_after=6)

    _section(doc, "왜 지금인가")
    _para(doc, idea["why_now"], size=10, space_after=8)

    mats = idea.get("material_ids") or []
    if mats:
        _para(doc, "출발 소재: " + ", ".join(mats) + "  (출처는 회의록 끝)", size=7.5, color=MUTED, space_after=2)

    _para(doc, "발제 담당 작성  ·  검토 Mr. MOON", size=7.5, color=MUTED, space_after=0, align=WD_ALIGN_PARAGRAPH.RIGHT)


def _minutes_page(doc, result: dict, titles: dict) -> None:
    idea, m = result["idea"], result["minutes"]
    v, fmt = m["verdict"], m["format"]
    head = _para(doc, size=8.5, space_after=2)
    _font(head.add_run("BLUE JEANS PICTURES  ·  STORY OFFICE 기획 회의록"), 8.5, True, MUTED)
    _font(head.add_run(f"     {idea.get('date', '')}  ·  검색 {result.get('searches', 0)}회"), 8.5, False, MUTED)
    t = _para(doc, f"「{idea['title']}」 회의 결과", size=18, bold=True, color=YALE, space_after=6)
    _rule(t)

    box = doc.add_table(rows=1, cols=1)
    cell = box.cell(0, 0)
    _shade(cell, "F7FBFC")
    p = cell.paragraphs[0]
    _font(p.add_run("배정 권고  "), 9, True, MUTED)
    _font(p.add_run(m.get("assignment", "")), 13, True, YALE)
    _font(p.add_run(f"   {v['verdict']}"), 11, True, GOLD)
    if m.get("reason"):
        _font(cell.add_paragraph().add_run(m["reason"]), 9.5)
    hook = " · ".join(f"{k} {n}" for k, n in v["hook"].items())
    ranked = " · ".join(f"{k} {n}" for k, n in fmt["ranked"][:3])
    _font(cell.add_paragraph().add_run(
        f"Hook {v['hook_total']}/50 ({hook})  ·  시장성 별 {v['stars'] if v['stars'] is not None else '미정'}  ·  "
        f"치명적 유사작 {'있음' if v['fatal'] else '없음'}  ·  포맷 확신도 {fmt['level']} ({ranked})"), 8, False, MUTED)
    _para(doc, "판정은 Idea Engine 규칙(GO: Hook 35 이상·시장성 3 이상·치명적 유사작 없음 / NOGO: Hook 25 미만·치명적 유사작·시장 부적합). "
               "최종 결정은 Mr. MOON. 회의는 아이디어를 고쳐 쓰지 않습니다.", size=7, color=MUTED, space_after=6)

    _section(doc, "회의 결론")
    _para(doc, m.get("summary", ""), size=9.5, space_after=4)

    _section(doc, "판단 담당 의견  (S번호 = 실제 검색 문서, 인용 = 아이디어 문장, 근거 없는 지적은 싣지 않음)")
    for o in result["opinions"]:
        p = _para(doc, size=9, space_after=0)
        p.paragraph_format.space_before = Pt(3)
        _font(p.add_run(f"{titles.get(o['role'], o['role'])}  "), 9, True, YALE)
        mark = "판정 제외(검색 안 함)" if o.get("excluded") else (o.get("verdict") or o.get("fit") or "")
        _font(p.add_run(f"[{mark}]  "), 9, True, GOLD)
        _font(p.add_run(o.get("one_line", "")), 9)
        pts = [f"{x['text']} ({x['ref'] if x['status'] == '확인됨' else '인용'})" for x in o.get("points", []) if x["status"] != "근거 없음"]
        if pts:
            q = _para(doc, "  ·  ".join(pts), size=8, color=MUTED, space_after=0)
            q.paragraph_format.line_spacing = 1.1
    _para(doc, space_after=2)

    _section(doc, "보완 과제")
    for i, x in enumerate(m.get("tasks", [])[:3], 1):
        p = _para(doc, size=9.5, space_after=1)
        _font(p.add_run(f"{i}.  "), 9.5, True, GOLD)
        _font(p.add_run(x), 9.5)
    _para(doc, space_after=2)

    ei = m.get("engine_input") or {}
    if ei:
        _section(doc, "엔진 입력 준비")
        for k, val in ei.items():
            p = _para(doc, size=8.5, space_after=0)
            p.paragraph_format.line_spacing = 1.1
            _font(p.add_run(f"{k}  "), 8.5, True, MUTED)
            _font(p.add_run(str(val)), 8.5)
        _para(doc, space_after=2)

    srcs = result.get("sources") or []
    used = {x["ref"] for o in result["opinions"] for x in o.get("points", []) if x["status"] == "확인됨"} | set(idea.get("material_ids", []))
    rows = [s for s in srcs if s["id"] in used]
    if rows:
        _section(doc, "출처")
        for s_ in rows:
            q = _para(doc, f"{s_['id']}  {s_['title']}  {s_['url']}", size=7, color=MUTED, space_after=0)
            q.paragraph_format.line_spacing = 1.0


def build_meeting_docx(result: dict, titles: dict) -> bytes:
    doc = Document()
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.top_margin = sec.bottom_margin = Cm(1.8)
    sec.left_margin = sec.right_margin = Cm(2.0)
    _idea_page(doc, result["idea"])
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    _minutes_page(doc, result, titles)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
