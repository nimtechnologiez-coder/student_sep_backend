import io
import os
from datetime import datetime
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

def generate_invoice_pdf(
    student_name: str,
    student_id: str,
    course_name: str,
    amount_paid: float,
    transaction_id: str,
    invoice_number: str,
    payment_date: str = None,
    order_id: str = None,
    payment_option: str = "Full Payment",
    total_fee: float = None,
    balance_due: float = 0.0,
    email: str = "",
    phone: str = "",
    batch_timing: str = "Morning"
) -> bytes:
    """
    Generates a professional, branded PDF invoice for student registration.
    Returns bytes of the generated PDF document.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    if not payment_date:
        payment_date = datetime.now().strftime("%d-%b-%Y")
    if total_fee is None:
        total_fee = amount_paid

    styles = getSampleStyleSheet()

    # Custom typography styles
    brand_blue = colors.HexColor("#0066fe")
    dark_slate = colors.HexColor("#0f172a")
    text_muted = colors.HexColor("#64748b")
    emerald_green = colors.HexColor("#059669")
    light_bg = colors.HexColor("#f8fafc")
    border_color = colors.HexColor("#e2e8f0")

    title_style = ParagraphStyle(
        'BrandTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=brand_blue
    )

    sub_title_style = ParagraphStyle(
        'BrandSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=text_muted
    )

    header_inv_title = ParagraphStyle(
        'InvoiceHeaderTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        alignment=TA_RIGHT,
        textColor=dark_slate
    )

    badge_style = ParagraphStyle(
        'VerifiedBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        alignment=TA_RIGHT,
        textColor=emerald_green
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=dark_slate
    )

    cell_label = ParagraphStyle(
        'CellLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=text_muted
    )

    cell_val = ParagraphStyle(
        'CellValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=dark_slate
    )

    cell_val_bold = ParagraphStyle(
        'CellValueBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=dark_slate
    )

    cell_val_mono = ParagraphStyle(
        'CellValueMono',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=9,
        leading=12,
        textColor=brand_blue
    )

    footer_text = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        alignment=TA_CENTER,
        textColor=text_muted
    )

    story = []

    # 1. Header: Left Brand Info with nimlogo.webp & Right Invoice Number / Badge
    brand_text_p = [
        Paragraph("NIM ACADEMY", title_style),
        Paragraph("School of Advanced AI & Technology Learning", sub_title_style),
        Paragraph("admissions@nim.edu | +91 98765 43210 | www.nimacademy.edu", sub_title_style),
    ]

    base_dir = getattr(settings, 'BASE_DIR', None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_candidates = [
        os.path.join(base_dir, 'studentsapp', 'static', 'images', 'nimlogo.webp'),
        os.path.join(base_dir, 'staticfiles', 'images', 'nimlogo.webp'),
        os.path.join(base_dir, '..', 'frontend', 'nim-portel', 'public', 'nimlogo.webp'),
        r'C:\Users\ADMIN\Documents\Student_portel\backend\studentsapp\static\images\nimlogo.webp',
        r'C:\Users\ADMIN\Documents\Student_portel\frontend\nim-portel\public\nimlogo.webp',
    ]

    logo_img = None
    for cand in logo_candidates:
        if cand and os.path.exists(cand):
            try:
                # Maintain aspect ratio (447x559 -> 0.8:1) at 32x40 pt
                logo_img = RLImage(cand, width=32, height=40)
                break
            except Exception:
                pass

    if logo_img:
        left_brand_table = Table([[logo_img, brand_text_p]], colWidths=[38, 292])
        left_brand_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        left_brand_content = left_brand_table
    else:
        left_brand_content = brand_text_p

    right_inv_p = [
        Paragraph("TAX INVOICE / RECEIPT", header_inv_title),
        Paragraph(f"<b>Invoice #:</b> {invoice_number}", ParagraphStyle('InvNum', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, alignment=TA_RIGHT, textColor=dark_slate)),
        Paragraph("STATUS: PAID &amp; VERIFIED", badge_style)
    ]

    header_table = Table([[left_brand_content, right_inv_p]], colWidths=[330, 210])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)

    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2, color=brand_blue, spaceBefore=4, spaceAfter=10))

    # 2. Key Transaction Metadata Bar (Invoice Date, Registration ID, Razorpay ID, Payment Option)
    meta_data = [
        [
            Paragraph("REGISTRATION ID", cell_label),
            Paragraph("PAYMENT DATE", cell_label),
            Paragraph("RAZORPAY PAYMENT ID", cell_label),
            Paragraph("PAYMENT OPTION", cell_label),
        ],
        [
            Paragraph(student_id, cell_val_mono),
            Paragraph(str(payment_date), cell_val_bold),
            Paragraph(str(transaction_id), cell_val_mono),
            Paragraph(str(payment_option), cell_val_bold),
        ]
    ]
    meta_table = Table(meta_data, colWidths=[135, 125, 150, 130])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)

    story.append(Spacer(1, 12))

    # 3. Two-Column Student Information & Course Information
    student_details_data = [
        [Paragraph("STUDENT DETAILS", section_heading), Paragraph("PROGRAM DETAILS", section_heading)],
        [
            Paragraph(f"<b>Name:</b> {student_name}", cell_val),
            Paragraph(f"<b>Course:</b> {course_name}", cell_val_bold)
        ],
        [
            Paragraph(f"<b>Email:</b> {email or '-'}", cell_val),
            Paragraph(f"<b>Batch Timing:</b> {batch_timing} Batch", cell_val)
        ],
        [
            Paragraph(f"<b>Phone:</b> {phone or '-'}", cell_val),
            Paragraph(f"<b>Admission Status:</b> Confirmed &amp; Enrolled", cell_val)
        ],
    ]
    student_table = Table(student_details_data, colWidths=[270, 270])
    student_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), light_bg),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(student_table)

    story.append(Spacer(1, 14))

    # 4. Itemized Tuition & Payment Breakdown
    headers = [
        Paragraph("<b>#</b>", cell_val_bold),
        Paragraph("<b>ITEM / DESCRIPTION</b>", cell_val_bold),
        Paragraph("<b>ENROLLED PROGRAM</b>", cell_val_bold),
        Paragraph("<b>PAYMENT TYPE</b>", cell_val_bold),
        Paragraph("<b>AMOUNT (INR)</b>", cell_val_bold)
    ]
    
    install_desc = "Full Course Fee Payment" if "full" in str(payment_option).lower() else "1st Installment Fee Payment"
    item_row = [
        Paragraph("1", cell_val),
        Paragraph(f"Course Admission &amp; Tuition Fee<br/><font color='#64748b' size='7.5'>Transaction Ref: {transaction_id}</font>", cell_val),
        Paragraph(course_name, cell_val),
        Paragraph(install_desc, cell_val),
        Paragraph(f"₹{amount_paid:,.2f}", cell_val_bold)
    ]

    subtotal_row = [
        Paragraph("", cell_val),
        Paragraph("", cell_val),
        Paragraph("", cell_val),
        Paragraph("<b>Total Course Fee:</b>", cell_val_bold),
        Paragraph(f"₹{total_fee:,.2f}", cell_val_bold)
    ]

    paid_row = [
        Paragraph("", cell_val),
        Paragraph("", cell_val),
        Paragraph("", cell_val),
        Paragraph("<b>Amount Paid (Razorpay):</b>", cell_val_bold),
        Paragraph(f"<font color='#059669'><b>₹{amount_paid:,.2f}</b></font>", cell_val_bold)
    ]

    balance_row = [
        Paragraph("", cell_val),
        Paragraph("", cell_val),
        Paragraph("", cell_val),
        Paragraph("<b>Remaining Balance Due:</b>", cell_val_bold),
        Paragraph(f"₹{balance_due:,.2f}", cell_val_bold)
    ]

    items_data = [headers, item_row, subtotal_row, paid_row, balance_row]
    items_table = Table(items_data, colWidths=[25, 205, 120, 110, 80])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
        ('BACKGROUND', (3, 3), (4, 3), colors.HexColor("#ecfdf5")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)

    story.append(Spacer(1, 18))

    # 5. Security & Verification Stamp Box
    stamp_content = [
        [
            Paragraph(
                "<b>PAYMENT AUTHENTICATION VERIFIED</b><br/>"
                f"<font size='8' color='#334155'>Cryptographic Signature Verified by Razorpay Webhook &amp; Server-Side Verification Key.<br/>"
                f"Razorpay Order ID: {order_id or 'Verified Sandbox'} | Transaction Reference: {transaction_id}</font>",
                cell_val
            ),
            Paragraph(
                f"<font color='#059669'><b>STATUS: SUCCESS</b></font><br/>"
                f"<font size='8' color='#64748b'>Authorized &amp; Recorded</font>",
                ParagraphStyle('StampRight', parent=styles['Normal'], alignment=TA_RIGHT)
            )
        ]
    ]
    stamp_table = Table(stamp_content, colWidths=[410, 130])
    stamp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#ecfdf5")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#a7f3d0")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(stamp_table)

    story.append(Spacer(1, 18))

    # 6. Terms & Computer-Generated Notice
    story.append(HRFlowable(width="100%", thickness=0.5, color=border_color, spaceBefore=4, spaceAfter=8))
    story.append(Paragraph(
        "This is an official computer-generated Tax Invoice and Admission Receipt issued upon successful verification of fees.<br/>"
        "No physical signature is required. For any admission or billing inquiries, please contact NIM Academy Admissions at <b>admissions@nim.edu</b>.",
        footer_text
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph("© 2026 NIM Academy. All rights reserved.", footer_text))

    doc.build(story)
    return buf.getvalue()
