"""Plaintext board-ready governance exports; protect files after creation."""
from __future__ import annotations
from pathlib import Path
from xml.sax.saxutils import escape
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from .reports import _safe_excel
from functools import partial
from .report_branding import for_report
from .report_style import pdf_styles, pdf_table_style, pdf_page, style_workbook

DISCLAIMER="Local operator-entered records. Reviewer names are not authenticated electronic signatures. Not a certification or independent audit."

def board_packet(service,org,path):
    path=Path(path)
    snap=service.board_snapshot(org);brand=for_report(service,org)
    m=snap["governance"];e=snap["enterprise"]
    cards=[
        ("Active frameworks",snap["frameworks_enabled"]),
        ("Verified items",snap["implementation_counts"]["verified"]),
        ("High/critical open findings",m["findings_high_critical"]),
        ("Overdue audit findings",m["findings_overdue"]),
        ("Changes awaiting CAB",m["changes_pending_cab"]),
        ("Rolled-back changes",m["changes_rolled_back"]),
        ("Verified evidence",e["evidence_verified"]),
        ("Expired evidence",e["evidence_expired"]),
        ("Open audits",m["audits_open"]),
    ]
    if path.suffix.lower()==".xlsx":
        wb=Workbook();sheet=wb.active;sheet.title="Board Summary"
        sheet.append(["Cybersecurity Governance | Board Packet",snap["as_of"]])
        sheet.append(["Metric","Value"])
        for key,value in cards:sheet.append([key,value])
        sheet.append(["Disclaimer",DISCLAIMER])
        for cell in sheet[1]+sheet[2]:
            cell.font=Font(bold=True,color="FFFFFF")
            cell.fill=PatternFill("solid",fgColor="203D5B")
        sheet.column_dimensions["A"].width=49;sheet.column_dimensions["B"].width=78
        for label,items,fields in (
            ("Changes",service.changes(org),["title","change_type","risk_level","owner","start_at","end_at","status"]),
            ("Audits",service.audits(org),["title","audit_type","framework","lead","start_date","end_date","status"]),
            ("Findings",service.findings(org),["title","severity","owner","due_date","status"]),
            ("Evidence",service.evidence_inventory(org),["title","classification","sha256","review_state","expires_on"])):
            ws=wb.create_sheet(label);ws.append(fields)
            for obj in items:ws.append([_safe_excel(str(obj.get(f,""))) for f in fields])
            ws.freeze_panes="A2";ws.auto_filter.ref=ws.dimensions
            for col in "ABCDEFG":ws.column_dimensions[col].width=28
        style_workbook(wb,summary_header=2,brand=brand)
        sheet.row_dimensions[sheet.max_row].height=64
        wb.save(path)
    elif path.suffix.lower()==".pdf":
        styles=pdf_styles(brand)
        story=[Paragraph(escape(brand["display_name"]),styles["Title"]), Paragraph("Governance | Board Packet",styles["Heading2"]),
               Paragraph("As of: "+escape(snap["as_of"]),styles["Normal"]),
               Spacer(1,16)]
        grid=[["Governance metric","Current value"]]+[[str(a),str(b)] for a,b in cards]
        t=Table(grid,colWidths=[310,175],repeatRows=1)
        t.setStyle(pdf_table_style(brand))
        story.extend([t,Spacer(1,18),Paragraph("Priority audit findings",styles["Heading2"])])
        for f in service.findings(org):
            if f["severity"] in {"high","critical"} and f["status"] not in {"closed","accepted"}:
                story.append(Paragraph(escape(f["severity"].upper()+" | "+f["title"]+" | "+f["owner"]),styles["BodyText"]))
        story.extend([Spacer(1,18),Paragraph("Management caveat",styles["Heading2"]),
                      Paragraph(DISCLAIMER,styles["BodyText"])])
        SimpleDocTemplate(str(path),pagesize=letter,leftMargin=46,rightMargin=46,topMargin=112,bottomMargin=64,title="Governance Board Packet").build(story,onFirstPage=partial(pdf_page,brand=brand),onLaterPages=partial(pdf_page,brand=brand))
    else:
        raise ValueError("Board report requires .pdf or .xlsx")
    return path
