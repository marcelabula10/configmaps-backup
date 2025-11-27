from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle


def export_pdf(results, output_pdf):
    """
    Generates a PDF formatted report using the same rules
    as the Excel version. Colors are applied to full rows
    based on the change type: Removed / Modified / Added.
    """

    doc = SimpleDocTemplate(output_pdf, pagesize=landscape(A4))

    # Header row
    data = [["ConfigMap", "Key", "Before", "After", "Status", "BeforeTime", "AfterTime"]]

    # Append diff rows
    for r in results:
        data.append(r)

    table = Table(data, repeatRows=1)

    # Base table style
    style = TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.25, colors.black),
    ])

    # Apply color highlights
    for i in range(1, len(data)):
        status = data[i][4]

        if status == "Removed":
            style.add('BACKGROUND', (0,i), (-1,i), colors.red)

        elif status == "Modified":
            style.add('BACKGROUND', (0,i), (-1,i), colors.yellow)

        elif status == "Added":
            style.add('BACKGROUND', (0,i), (-1,i), colors.green)

    table.setStyle(style)
    doc.build([table])

    print(f"✔ PDF saved → {output_pdf}")
