"""Generates reviewable DOCX and selectable PDFs, not pre-approved application files."""
from __future__ import annotations
from pathlib import Path
import re,xml.sax.saxutils as xml

COBALT='#0047AB'
from .core import ROOT
import json

def profile():
    return json.loads((ROOT/'profile.json').read_text(encoding='utf-8'))


def clean(t):return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',str(t or '')).strip()

def make_docx(path,title,body,kind):
    from docx import Document
    from docx.shared import Inches,Pt,RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.style import WD_STYLE_TYPE
    doc=Document()
    sec=doc.sections[0]
    sec.top_margin=Inches(.58);sec.bottom_margin=Inches(.58)
    sec.left_margin=Inches(.75);sec.right_margin=Inches(.75)
    styles=doc.styles
    normal=styles['Normal'];normal.font.name='Aptos';normal.font.size=Pt(10.7 if kind=='resume' else 11)
    normal.paragraph_format.space_after=Pt(3)
    for nm in ('Heading 1','Heading 2'):
        sty=styles[nm];sty.font.name='Aptos';sty.font.color.rgb=RGBColor(0,71,171)
        sty.font.size=Pt(12 if nm=='Heading 1' else 11)
    person=profile()
    header=doc.add_paragraph(person['name']);header.style=styles['Title']
    header.runs[0].font.name='Aptos';header.runs[0].font.color.rgb=RGBColor(0,0,0)
    header.runs[0].font.size=Pt(18)
    doc.add_paragraph(' | '.join(filter(None,[person.get('location'),person.get('email'),person.get('phone'),person.get('linkedin')])))
    if kind=='letter':
        for para in clean(body).split('\n'):
            if para.strip():doc.add_paragraph(clean(para))
    elif kind=='resume':
        data=body
        doc.add_heading(clean(data.get('headline')),level=1)
        doc.add_paragraph(clean(data.get('summary')))
        doc.add_heading('Selected evidence',level=1)
        for b in data.get('selected_achievements',[]):doc.add_paragraph(clean(b),style='List Bullet')
        doc.add_heading('Professional Experience',level=1)
        for item in data.get('experience',[]):
            h=' | '.join(filter(None,[clean(item.get('title')),clean(item.get('company')),clean(item.get('dates')),clean(item.get('location'))]))
            doc.add_heading(h,level=2)
            for b in item.get('bullets',[]):doc.add_paragraph(clean(b),style='List Bullet')
        doc.add_heading('Skills',level=1)
        doc.add_paragraph(' • '.join(clean(x) for x in data.get('skills',[])))
        doc.add_heading('Education',level=1)
        for ed in person['education']:doc.add_paragraph(clean(ed))
    else:
        doc.add_heading(clean(title),level=1)
        for par in clean(body).split('\n'):
            if par.strip():doc.add_paragraph(clean(par))
    doc.core_properties.title=title
    doc.core_properties.author=person.get('name','')
    doc.save(path)


def register_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    candidates=[
       '/System/Library/Fonts/Supplemental/Arial.ttf',
       '/Library/Fonts/Arial.ttf',
       '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
       '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']
    for s in candidates:
        if Path(s).exists():
            pdfmetrics.registerFont(TTFont('JobRadarFont',s))
            return 'JobRadarFont'
    return 'Helvetica'


def make_pdf(path,title,body,kind):
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,KeepTogether
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.colors import HexColor,black
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    font=register_fonts()
    st={'name':ParagraphStyle('Name',fontName=font,fontSize=17,leading=19,spaceAfter=13,textColor=black),
        'head':ParagraphStyle('Header',fontName=font,fontSize=12,leading=16,spaceBefore=10,spaceAfter=5,textColor=HexColor(COBALT)),
        'sub':ParagraphStyle('Sub',fontName=font,fontSize=10.7,leading=14,spaceBefore=6,spaceAfter=3,textColor=HexColor(COBALT)),
        'body':ParagraphStyle('Body',fontName=font,fontSize=10.6 if kind=='resume' else 11,leading=14.5,spaceAfter=7),
        'bullet':ParagraphStyle('Bullet',fontName=font,fontSize=10.5,leading=14,leftIndent=12,firstLineIndent=-9,spaceAfter=4)}
    def p(s,style='body'):return Paragraph(xml.escape(clean(s)).replace('\n',' '),st[style])
    person=profile()
    story=[p(person['name'],'name'),p(' | '.join(filter(None,[person.get('location'),person.get('email'),person.get('phone'),person.get('linkedin')])))]
    if kind=='letter':
        for item in clean(body).split('\n'):
            if item.strip():story.append(p(item))
    elif kind=='resume':
        story.extend([p(body.get('headline',''),'head'),p(body.get('summary','')),
                      p('Selected evidence','head')])
        for item in body.get('selected_achievements',[]):story.append(p('• '+clean(item),'bullet'))
        story.append(p('Professional Experience','head'))
        for exp in body.get('experience',[]):
            hdr=' | '.join(filter(None,[clean(exp.get('title')),clean(exp.get('company')),clean(exp.get('dates')),clean(exp.get('location'))]))
            story.append(p(hdr,'sub'))
            for item in exp.get('bullets',[]):story.append(p('• '+clean(item),'bullet'))
        story.append(p('Skills','head'))
        story.append(p(' • '.join(clean(x) for x in body.get('skills',[]))))
        story.append(p('Education','head'))
        for ed in person['education']:story.append(p(ed))
    else:
        story.append(p(title,'head'))
        for item in clean(body).split('\n'):
            if item.strip():story.append(p(item))
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont(font,8);canvas.setFillColor(HexColor('#555555'))
        canvas.drawRightString(560,27,f'DRAFT – human verification required · {doc.page}')
        canvas.restoreState()
    pdf=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=49,leftMargin=49,topMargin=46,bottomMargin=49,
                          title=title,author=person.get('name',''))
    pdf.build(story,onFirstPage=footer,onLaterPages=footer)


def build_documents(dest,data,job):
    from pypdf import PdfReader,PdfWriter
    dest=Path(dest)
    outputs=[('01_Cover_Letter',f'Cover Letter — {job["company"]}',data['cover_letter'],'letter'),
             ('02_Resume',f'Resume — {job["title"]}',data['resume'],'resume')]
    support=data.get('supporting_document')
    if isinstance(support,dict) and support.get('body'):
        outputs.append(('03_'+re.sub(r'\W+','_',str(support.get('type','Bluebook'))),
                         clean(support.get('title') or 'Work Sample'),support['body'],'support'))
    writer=PdfWriter()
    lines=['# Release QA — NOT APPROVED','All material is provisional. Verify against authoritative resume and actual job post.',
        'Check exact application history, personal ownership, outcome evidence, dates, location, ATS fields, and employer-contribution test.',
        'Review page PNGs or open PDFs before sending; automatically extracted text is not visual approval.','']
    combined_pages=0
    for name,title,body,kind in outputs:
        path_docx=dest/(name+'_DRAFT.docx');path_pdf=dest/(name+'_DRAFT.pdf')
        make_docx(path_docx,title,body,kind)
        make_pdf(path_pdf,title,body,kind)
        reader=PdfReader(str(path_pdf));pages=len(reader.pages);combined_pages+=pages
        read_text='\n'.join((pg.extract_text() or '') for pg in reader.pages)
        readable=profile()['name'] in read_text and len(read_text)>100
        lines.append(f'- {name}: {pages} page(s), selectable-text check: {"OK" if readable else "REVIEW"}')
        if kind=='letter' and pages!=1:lines.append('  - **REVISE**: letter must be one page.')
        if kind=='resume' and pages!=2:lines.append('  - **REVIEW**: resume should normally be two pages; no arbitrary page fill or downsizing.')
        if kind=='support' and pages!=1:lines.append('  - **REVIEW**: supporting page is normally one page.')
        if not readable:lines.append('  - **BLOCKER**: extracted PDF text missing/inadequate.')
        for pg in reader.pages:writer.add_page(pg)
    combined=dest/'00_Combined_Application_DRAFT.pdf'
    with combined.open('wb') as f:writer.write(f)
    for claim in data.get('claim_audit',[]):
        if 'UNVERIFIED' in str(claim.get('evidence_source','')).upper():
            lines.append('**CLAIM REVIEW**: '+clean(claim.get('claim',''))+' — UNVERIFIED')
    lines.extend(['',f'Combined package: {combined_pages} page(s), cover letter first, resume next.',
                  'Status stays **PREPARED ONLY**. A user must inspect every rendered page and verify every claim.',
                  'No employer submission, automated applying or recruiter outreach is performed.'])
    return '\n'.join(lines)+'\n'
