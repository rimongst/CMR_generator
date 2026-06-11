"""
CMR International Consignment Note PDF Generator
Generates a filled CMR waybill using ReportLab
"""
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

W, H = A4  # 210 x 297 mm

def pt(x_mm, y_mm):
    """Convert mm to points, y from top"""
    return x_mm * mm, H - y_mm * mm

def generate_cmr_pdf(data: dict, copy_number: int = 1) -> bytes:
    """
    Generate a single CMR page (one copy).
    copy_number: 1=Sender, 2=Consignee, 3=Carrier
    """
    copy_labels = {1: "Exemplaire de l'expéditeur / Copy for sender",
                   2: "Exemplaire du destinataire / Copy for consignee",
                   3: "Exemplaire du transporteur / Copy for carrier"}

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    # ── helpers ──────────────────────────────────────────────────────────────
    def rect(x, y, w, h, fill=0):
        c.rect(x * mm, H - (y + h) * mm, w * mm, h * mm, fill=fill)

    def label(text, x, y, size=5.5, bold=False):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(x * mm, (H - y * mm), text)

    def value(text, x, y, size=8, max_width=None):
        """Draw user-supplied value in a slightly larger font."""
        c.setFont("Helvetica", size)
        text = str(text) if text else ""
        if max_width:
            # simple truncation – improve with textwrap if needed
            while c.stringWidth(text, "Helvetica", size) > max_width * mm and len(text) > 1:
                text = text[:-1]
        c.drawString(x * mm, (H - y * mm), text)

    def multiline_value(text, x, y, max_width, line_height=4, size=7.5):
        """Draw wrapped text."""
        c.setFont("Helvetica", size)
        text = str(text) if text else ""
        words = text.split()
        lines, line = [], ""
        for w2 in words:
            test = (line + " " + w2).strip()
            if c.stringWidth(test, "Helvetica", size) <= max_width * mm:
                line = test
            else:
                if line:
                    lines.append(line)
                line = w2
        if line:
            lines.append(line)
        for i, l in enumerate(lines[:3]):
            c.drawString(x * mm, (H - (y + i * line_height) * mm), l)

    # ── outer border ─────────────────────────────────────────────────────────
    c.setLineWidth(1.2)
    rect(5, 5, 200, 287)
    c.setLineWidth(0.5)

    # ── Title bar ─────────────────────────────────────────────────────────────
    rect(5, 5, 200, 10, fill=0)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(W / 2, H - 12 * mm, "LETTRE DE VOITURE INTERNATIONALE / INTERNATIONAL CONSIGNMENT NOTE")
    note_no = data.get("note_number", "")
    c.setFont("Helvetica-Bold", 8)
    c.drawRightString(204 * mm, H - 12 * mm, f"No {note_no}")

    # ── CMR convention notice (right column, top) ─────────────────────────────
    rect(140, 15, 65, 18)
    c.setFont("Helvetica", 5)
    notice = (
        "Ce transport est soumis, nonobstant toute clause contraire à la Convention relative\n"
        "au contrat de transport international de marchandises par route (CMR).\n"
        "This carriage is subject, notwithstanding any clause to the contrary, to the Convention\n"
        "on the Contract for the International Carriage of goods by road (CMR)."
    )
    text_obj = c.beginText(141 * mm, H - 17 * mm)
    text_obj.setFont("Helvetica", 5)
    for ln in notice.split("\n"):
        text_obj.textLine(ln)
    c.drawText(text_obj)

    # ── Box 1 – Sender ────────────────────────────────────────────────────────
    rect(5, 15, 135, 22)
    label("1  Expéditeur (nom, adresse, pays) / Sender (name, address, country)", 6, 17.5)
    multiline_value(data.get("sender", ""), 6, 21, 132)

    # ── Box 2 – Consignee ─────────────────────────────────────────────────────
    rect(5, 37, 135, 22)
    label("2  Destinataire (nom, adresse, pays) / Consignee (name, address, country)", 6, 39.5)
    multiline_value(data.get("consignee", ""), 6, 43, 132)

    # ── Box 3 – Place of delivery ─────────────────────────────────────────────
    rect(5, 59, 135, 14)
    label("3  Lieu prévu pour la livraison (lieu, pays) / Place of delivery (place, country)", 6, 61)
    multiline_value(data.get("delivery_place", ""), 6, 64, 132)

    # ── Box 4 – Place & date of taking over ───────────────────────────────────
    rect(5, 73, 135, 14)
    label("4  Lieu et date de la prise en charge (lieu, pays, date) / Place and date of taking over (place, country, date)", 6, 75)
    multiline_value(data.get("pickup_place", ""), 6, 78, 132)

    # ── Box 5 – Documents attached ────────────────────────────────────────────
    rect(140, 33, 65, 14)
    label("5  Documents annexés / Documents attached", 141, 35)
    multiline_value(data.get("documents", ""), 141, 38, 62)

    # ── Box 16 – Carrier ──────────────────────────────────────────────────────
    rect(140, 47, 65, 22)
    label("16  Transporteur (nom, adresse, pays) / Carrier (name, address, country)", 141, 49)
    multiline_value(data.get("carrier", ""), 141, 52, 62)

    # ── Box 17 – Successive carriers ──────────────────────────────────────────
    rect(140, 69, 65, 18)
    label("17  Transporteurs successifs (nom, adresse, pays) / Successive carriers", 141, 71)
    multiline_value(data.get("successive_carriers", ""), 141, 74, 62)

    # ── Goods table header ────────────────────────────────────────────────────
    cols = [5, 25, 45, 65, 100, 130, 150, 165, 180]
    col_widths = [20, 20, 20, 35, 30, 20, 15, 15, 25]
    table_top = 87
    table_h = 35

    # Header row
    rect(5, table_top, 200, 8, fill=0)
    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.rect(5 * mm, H - (table_top + 8) * mm, 200 * mm, 8 * mm, fill=1, stroke=1)
    c.setFillColorRGB(0, 0, 0)

    headers = [
        ("6\nMarques et\nnuméro\nMarks & Nos", 5, 20),
        ("7\nNbre colis\nNb packages", 25, 20),
        ("8\nEmballage\nPacking", 45, 20),
        ("9\nNature marchandise\nNature of goods", 65, 35),
        ("10\nNo statistique\nStat. No", 100, 30),
        ("11\nPoids brut kg\nGross weight", 130, 20),
        ("12\nVolume m³\nVolume", 150, 15),
        ("Cl.\nClass", 165, 15),
        ("Chiffre\nNumber\nLettre\nLetter", 180, 25),
    ]
    for htxt, hx, hw in headers:
        lines2 = htxt.split("\n")
        for li, ln in enumerate(lines2):
            c.setFont("Helvetica", 4.5)
            c.drawString((hx + 0.5) * mm, (H - (table_top + 2 + li * 1.5) * mm), ln)

    # Draw vertical lines for columns
    for cx in [25, 45, 65, 100, 130, 150, 165, 180]:
        c.line(cx * mm, H - table_top * mm, cx * mm, H - (table_top + table_h) * mm)
    rect(5, table_top, 200, table_h)

    # Goods data rows
    goods_list = data.get("goods", [{}])
    for gi, g in enumerate(goods_list[:3]):
        gy = table_top + 8 + gi * 9
        c.line(5 * mm, H - gy * mm, 205 * mm, H - gy * mm)
        value(g.get("marks", ""), 5.5, gy + 2)
        value(g.get("packages", ""), 25.5, gy + 2)
        value(g.get("packing", ""), 45.5, gy + 2)
        value(g.get("description", ""), 65.5, gy + 2, size=7)
        value(g.get("stat_no", ""), 100.5, gy + 2)
        value(g.get("weight", ""), 130.5, gy + 2)
        value(g.get("volume", ""), 150.5, gy + 2)
        value(g.get("adr_class", ""), 165.5, gy + 2)
        value(g.get("adr_number", ""), 180.5, gy + 2)

    # ── Box 13 – Sender's instructions ────────────────────────────────────────
    rect(5, 122, 100, 14)
    label("13  Instructions de l'expéditeur / Sender's Instructions", 6, 124)
    multiline_value(data.get("sender_instructions", ""), 6, 127, 98)

    # ── Box 18 – Carrier's reservations ───────────────────────────────────────
    rect(105, 122, 100, 14)
    label("18  Réserves et observations du transporteur / Carrier's reservations", 106, 124)
    multiline_value(data.get("carrier_reservations", ""), 106, 127, 98)

    # ── Box 14 – Special agreements ───────────────────────────────────────────
    rect(5, 136, 200, 12)
    label("14  Conventions particulières / Special agreements", 6, 138)
    multiline_value(data.get("special_agreements", ""), 6, 141, 198)

    # ── Payment instructions (Box 15) ─────────────────────────────────────────
    rect(5, 148, 135, 10)
    label("15  Prescriptions d'affranchissement / Instructions as to payment for carriage", 6, 150)
    carriage_paid = data.get("carriage_paid", True)
    c.setFont("Helvetica", 7)
    c.drawString(10 * mm, H - 154 * mm, "[X] Franco / Carriage paid" if carriage_paid else "[ ] Franco / Carriage paid")
    c.drawString(70 * mm, H - 154 * mm, "[ ] Non franco / Carriage forward" if carriage_paid else "[X] Non franco / Carriage forward")

    # ── Freight charges table (Box 19–24) ─────────────────────────────────────
    rect(140, 148, 65, 50)
    label("Prescriptions d'affranchissement / Payment", 141, 150)

    charge_rows = [
        ("Prix de transport / Carriage charges", data.get("carriage_charges", "")),
        ("Réductions / Deductions (-)", data.get("deductions", "")),
        ("Solde / Balance", data.get("balance", "")),
        ("Suppléments / Suppl. charges", data.get("supplementary_charges", "")),
        ("Frais accessoires / Other charges (+)", data.get("other_charges", "")),
        ("TOTAL", data.get("total", "")),
    ]
    for ri, (rlabel, rval) in enumerate(charge_rows):
        ry = 153 + ri * 7
        c.line(140 * mm, H - ry * mm, 205 * mm, H - ry * mm)
        c.setFont("Helvetica", 5.5)
        c.drawString(141 * mm, H - (ry + 5) * mm, rlabel)
        c.setFont("Helvetica-Bold", 8)
        c.drawRightString(204 * mm, H - (ry + 5) * mm, str(rval))

    currency = data.get("currency", "EUR")
    label(f"Monnaie / Currency: {currency}", 141, 196, size=6)

    # ── Cash on delivery ──────────────────────────────────────────────────────
    rect(140, 198, 65, 8)
    label("Remboursement / Cash on delivery:", 141, 200)
    value(data.get("cash_on_delivery", ""), 141, 203, size=7)

    # ── Established at / date ─────────────────────────────────────────────────
    rect(5, 158, 135, 10)
    label("Etablie à / Established in:", 6, 160)
    value(data.get("established_at", ""), 40, 163)
    label("le / on:", 85, 160)
    value(data.get("established_date", ""), 98, 163)

    # ── Signatures ────────────────────────────────────────────────────────────
    rect(5, 168, 67, 25)
    label("Signature et timbre de l'expéditeur / Signature and stamp of the sender", 6, 170, size=5)
    multiline_value(data.get("sender_signature", ""), 6, 174, 64, size=6.5)

    rect(72, 168, 68, 25)
    label("Signature et timbre du transporteur / Signature and stamp of the carrier", 73, 170, size=5)
    multiline_value(data.get("carrier_signature", ""), 73, 174, 65, size=6.5)

    # ── Goods received (consignee) ─────────────────────────────────────────────
    rect(5, 193, 135, 25)
    label("Marchandises reçues / Goods received", 6, 195, size=5.5, bold=True)
    label("Lieu / Place:", 6, 199)
    value(data.get("received_place", ""), 25, 202)
    label("le / on:", 6, 207)
    value(data.get("received_date", ""), 18, 210)
    label("Signature et timbre du destinataire / Signature and stamp of the consignee", 6, 213, size=5)
    multiline_value(data.get("consignee_signature", ""), 6, 216, 132, size=6.5)

    # ── Notes ─────────────────────────────────────────────────────────────────
    rect(5, 218, 200, 16)
    c.setFont("Helvetica", 4.5)
    notes = (
        "Les parties encadrées de lignes grasses doivent être remplies par le transporteur. "
        "The space framed with heavy lines must be filled in by the carrier. | "
        "En cas de marchandises dangereuses indiquer, outre la certification éventuelle, à la dernière ligne du cadre: le chiffre et le cas échéant, la lettre. "
        "In case of dangerous goods mention the class, number and letter (ADR)."
    )
    text_obj = c.beginText(6 * mm, H - 220 * mm)
    text_obj.setFont("Helvetica", 4.5)
    text_obj.setTextOrigin(6 * mm, H - 220 * mm)
    # wrap manually
    words3 = notes.split()
    ln3, lines3 = "", []
    for w3 in words3:
        test3 = (ln3 + " " + w3).strip()
        if c.stringWidth(test3, "Helvetica", 4.5) < 196 * mm:
            ln3 = test3
        else:
            lines3.append(ln3)
            ln3 = w3
    lines3.append(ln3)
    for li3, l3 in enumerate(lines3[:4]):
        c.drawString(6 * mm, H - (220 + li3 * 3.5) * mm, l3)

    # ── Copy label (bottom) ───────────────────────────────────────────────────
    rect(5, 234, 200, 8)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(W / 2, H - 239 * mm, copy_labels.get(copy_number, ""))

    c.showPage()
    c.save()
    return buf.getvalue()


def generate_full_cmr(data: dict) -> bytes:
    """Generate all 3 copies of the CMR as one PDF."""
    from pypdf import PdfWriter, PdfReader
    writer = PdfWriter()
    for copy_num in [1, 2, 3]:
        page_bytes = generate_cmr_pdf(data, copy_number=copy_num)
        reader = PdfReader(io.BytesIO(page_bytes))
        writer.add_page(reader.pages[0])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
