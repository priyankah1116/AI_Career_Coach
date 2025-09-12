from fpdf import FPDF
from fpdf.enums import XPos, YPos

pdf = FPDF()
pdf.add_page()
pdf.set_font("Helvetica", size=12)
pdf.cell(200, 10, text="PDF generation works!", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
pdf.output("test.pdf")