"""Shared visual styling for existing management report exports."""
from io import BytesIO
from reportlab.lib.utils import ImageReader
from openpyxl.drawing.image import Image as ExcelImage
from .reports import _safe_excel
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.chart import BarChart, Reference
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import TableStyle

NAVY='112C3A'
TEAL='0C827D'
PALE='F0F6F7'

def ink(color):
    rgb=[int(color[i:i+2],16)/255 for i in (0,2,4)]
    linear=[c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4 for c in rgb]
    return 'FFFFFF' if sum(c*w for c,w in zip(linear,(.2126,.7152,.0722)))<.179 else '000000'

def pdf_styles(brand=None):
    styles=getSampleStyleSheet()
    for name in ('Title','Heading1','Heading2'):
        styles[name].textColor=colors.HexColor('#'+((brand or {}).get('primary_color',NAVY) if ink((brand or {}).get('primary_color',NAVY))=='FFFFFF' else NAVY))
    styles['Title'].fontSize=23
    styles['Title'].leading=28
    styles['Heading2'].fontSize=12
    styles['Heading2'].spaceBefore=14
    styles['BodyText'].fontSize=9
    styles['BodyText'].leading=14
    styles['Normal'].fontSize=9
    styles['Normal'].leading=14
    return styles

def pdf_table_style(brand=None):
    primary=(brand or {}).get('primary_color',NAVY);accent=(brand or {}).get('accent_color',TEAL)
    return TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#'+primary)),
        ('TEXTCOLOR',(0,0),(-1,0),colors.HexColor('#'+ink(primary))),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,-1),9),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#'+PALE)]),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),
        ('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9),
        ('ALIGN',(-1,1),(-1,-1),'RIGHT'),
        ('LINEBELOW',(0,0),(-1,0),2,colors.HexColor('#'+accent)),
    ])

def pdf_page(canvas,doc,brand=None):
    canvas.saveState()
    width,height=doc.pagesize
    canvas.setFillColor(colors.HexColor('#'+(brand or {}).get('accent_color',TEAL)))
    canvas.rect(0,height-10,width,10,fill=1,stroke=0)
    canvas.setFont('Helvetica-Bold',8)
    canvas.setFillColor(colors.HexColor('#'+NAVY))
    if brand:
        left=46
        if brand.get('logo'):
            image=ImageReader(BytesIO(brand['logo']))
            canvas.drawImage(image,46,height-91,width=110,height=54,preserveAspectRatio=True,anchor='c',mask='auto')
            left=174
        canvas.setFont('Helvetica-Bold',11)
        heading=brand['display_name']
        while canvas.stringWidth(heading,'Helvetica-Bold',11)>width-left-46:heading=heading[:-2]+'…'
        canvas.drawString(left,height-46,heading)
        canvas.setFont('Helvetica',8)
        subtitle=brand.get('tagline','')
        while canvas.stringWidth(subtitle,'Helvetica',8)>width-left-46:subtitle=subtitle[:-2]+'…'
        canvas.drawString(left,height-63,subtitle)
    else:
        canvas.drawString(46,height-32,'CSOS  /  CYBER SECURITY OPERATIONS ONLINE STUDIO')
    canvas.setStrokeColor(colors.HexColor('#DCE5E8'))
    canvas.line(46,48,width-46,48)
    canvas.setFont('Helvetica',7)
    note=(brand or {}).get('footer_note','Confidential management records')
    while canvas.stringWidth(note,'Helvetica',7)>width-92:note=note[:-2]+'…'
    canvas.drawString(46,36,note)
    canvas.drawString(46,25,'Program Owner - Matthew Harris')
    canvas.drawRightString(width-46,25,f'{doc.page}')
    canvas.restoreState()

def style_workbook(wb,summary_header=5,brand=None):
    """Preserve cell values and sheet schemas; add accessible report formatting."""
    primary=(brand or {}).get('primary_color',NAVY);accent=(brand or {}).get('accent_color',TEAL)
    for index,ws in enumerate(wb):
        header=summary_header if index==0 else 1
        ws.sheet_view.showGridLines=False
        ws.sheet_properties.tabColor=accent if index==0 else primary
        ws.freeze_panes=f'A{header+1}'
        ws.auto_filter.ref=f'A{header}:{ws.cell(ws.max_row,ws.max_column).coordinate}'
        ws.print_title_rows=f'1:{header}'
        ws.sheet_properties.pageSetUpPr.fitToPage=True
        ws.page_setup.orientation='landscape';ws.page_setup.paperSize=ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth=1;ws.page_setup.fitToHeight=0
        ws.oddFooter.center.text='Program Owner - Matthew Harris | Confidential | Page &P of &N'
        for column in ws.columns:
            width=min(56,max(18,max(len(str(c.value or '')) for c in column[:80])+3))
            ws.column_dimensions[column[0].column_letter].width=width
            for cell in column:
                cell.font=Font(name='Calibri',size=11,color=NAVY)
                cell.alignment=Alignment(vertical='top',wrap_text=True)
                if cell.row>header and cell.row%2==0:cell.fill=PatternFill('solid',fgColor=PALE)
        for cell in ws[header]:
            cell.font=Font(name='Calibri',bold=True,color=ink(primary),size=11)
            cell.fill=PatternFill('solid',fgColor=primary)
        ws.row_dimensions[header].height=28
        for row in range(header+1,ws.max_row+1):ws.row_dimensions[row].height=34
        if index==0:
            for cell in ws[1]:
                cell.font=Font(name='Calibri',size=18,bold=True,color=ink(primary))
                cell.fill=PatternFill('solid',fgColor=primary)
            ws.row_dimensions[1].height=42
            ws.column_dimensions['A'].width=58;ws.column_dimensions['B'].width=65
            for row in range(2,header):ws.row_dimensions[row].height=54 if row==4 else 28
            end=ws.max_row-(1 if ws.cell(ws.max_row,1).value=='Disclaimer' else 0)
            if end>header and any(isinstance(ws.cell(r,2).value,(int,float)) for r in range(header+1,end+1)):
                chart=BarChart();chart.type='bar';chart.style=13
                chart.title='Current management indicators';chart.y_axis.title='Metric';chart.x_axis.title='Count'
                chart.add_data(Reference(ws,min_col=2,min_row=header,max_row=end),titles_from_data=True)
                chart.set_categories(Reference(ws,min_col=1,min_row=header+1,max_row=end))
                chart.height=15;chart.width=25;chart.legend=None
                if chart.series:chart.series[0].graphicalProperties.solidFill=accent
                ws.add_chart(chart,'D2')

    if brand:
        summary=wb.worksheets[0]
        identity=wb.create_sheet('Report Identity',0)
        identity.sheet_view.showGridLines=False;identity.sheet_properties.tabColor=accent
        for row in [[_safe_excel(brand['display_name'])],[_safe_excel(brand.get('tagline',''))],
                    ['Report',_safe_excel(str(summary.cell(1,1).value))],
                    ['Organization',_safe_excel(brand['display_name'])],
                    ['Handling',_safe_excel(brand.get('footer_note',''))],
                    ['Program owner','Matthew Harris'],
                    ['Contents','Use the worksheet tabs for the executive summary and detailed management records.']]:identity.append(row)
        identity.column_dimensions['A'].width=25;identity.column_dimensions['B'].width=65
        identity.merge_cells('A1:B1');identity.merge_cells('A2:B2')
        for cell in identity[1]:cell.fill=PatternFill('solid',fgColor=primary);cell.font=Font(name='Calibri',size=22,bold=True,color=ink(primary))
        identity.row_dimensions[1].height=50;identity.row_dimensions[2].height=40
        for row in range(3,8):
            identity.row_dimensions[row].height=36
            for cell in identity[row]:cell.alignment=Alignment(wrap_text=True,vertical='center');cell.font=Font(name='Calibri',size=11,color=NAVY)
        if brand.get('logo'):
            image=ExcelImage(BytesIO(brand['logo']));ratio=min(260/image.width,110/image.height)
            image.width*=ratio;image.height*=ratio;identity.add_image(image,'A10')
        identity.print_options.horizontalCentered=True;identity.print_area='A1:B17'
        identity.page_setup.orientation='portrait';identity.page_setup.fitToWidth=1;identity.page_setup.fitToHeight=1
        identity.sheet_properties.pageSetUpPr.fitToPage=True
        for ws in wb:
            ws.oddHeader.center.text=brand['display_name'].replace('&','&&')
            ws.oddFooter.left.text=brand.get('footer_note','').replace('&','&&')
            ws.oddFooter.center.text='Program Owner - Matthew Harris'
            ws.oddFooter.right.text='Page &P of &N'
