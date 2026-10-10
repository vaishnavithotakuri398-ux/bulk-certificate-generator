
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

OUTPUT_DIR = "generated_certificates"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_certificate(name, event_name, certificate_id):
    filename = f"certificate_{certificate_id}.pdf"
    file_path = os.path.join(OUTPUT_DIR, filename)

    pdf = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    pdf.setTitle("Certificate of Participation")

    # Certificate heading
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(
        width / 2, height - 150,
        "CERTIFICATE OF PARTICIPATION"
    )

    # Recipient details
    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(
        width / 2, height - 220,
        "This certificate is presented to"
    )

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawCentredString(
        width / 2, height - 270, name
    )

    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(
        width / 2, height - 320,
        f"For participating in {event_name}"
    )

    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(
        width / 2, 100,
        f"Certificate ID: {certificate_id}"
    )

    pdf.save()
    return file_path
