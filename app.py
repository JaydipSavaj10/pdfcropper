from flask import Flask, request, send_file, render_template
import PyPDF2, io, re
from collections import defaultdict
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def upload_pdf():
    if request.method == "POST":
        files = request.files.getlist("pdf_file")
        if not files:
            return render_template("index.html", message="No files selected")
        
        # Options (example, can be added as checkboxes in HTML)
        keep_invoice = True
        crop_invoice = False
        merge_files = True
        print_datetime = True

        courier_pages = defaultdict(lambda: defaultdict(list))  # courier -> sold_by -> pages
        picklist_data = []

        for file in files:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text = page.extract_text() or ""

                # Courier detection
                courier = "Others"
                if "ValmoPlus" in text: courier = "ValmoPlus"
                elif "Valmo Pickup" in text or "ValmoExpress" in text: courier = "Valmo"
                elif "Delhivery" in text: courier = "Delhivery"
                elif "Xpress Bees" in text: courier = "XpressBees"

                # Sold By
                sold_match = re.search(r"Sold\s*By[:\s-]*([^\n\r]+)", text, re.I)
                sold_by = sold_match.group(1).strip() if sold_match else "UnknownSeller"

                # Invoice handling
                is_invoice = bool(re.search(r"Invoice\b", text, re.I))
                if is_invoice and not keep_invoice:
                    continue

                # Append page to sorted dict
                courier_pages[courier][sold_by].append(page)

                # Collect picklist data
                sku_match = re.search(r"Product Details\s*[\s\S]*?\n(.+?)\s+Size", text)
                sku = sku_match.group(1).strip() if sku_match else "UnknownSKU"
                qty_match = re.search(r"Qty\s+(\d+)", text)
                qty = int(qty_match.group(1)) if qty_match else 0
                picklist_data.append({"Courier": courier, "Sold By": sold_by, "SKU": sku, "Qty": qty})

        # Build final PDF
        writer = PyPDF2.PdfWriter()
        for courier in sorted(courier_pages.keys()):
            for seller in sorted(courier_pages[courier].keys()):
                for page in courier_pages[courier][seller]:
                    # Add datetime watermark
                    if print_datetime:
                        watermark = datetime.now().strftime("%Y-%m-%d %H:%M")
                        try:
                            page.add_annotation({
                                "subtype": "/Text",
                                "contents": watermark,
                                "rect": [50, 750, 200, 770]
                            })
                        except: pass
                    writer.add_page(page)

        # Add picklist page at end
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=A4)
        can.setFont("Helvetica", 10)
        y = 800
        can.drawString(50, y+20, "Picklist Summary")
        for item in picklist_data:
            line = f"{item['Courier']} | {item['Sold By']} | {item['SKU']} | {item['Qty']}"
            can.drawString(50, y, line)
            y -= 15
            if y < 50:  # new page
                can.showPage()
                y = 800
        can.save()
        packet.seek(0)
        picklist_pdf = PyPDF2.PdfReader(packet)
        for page in picklist_pdf.pages:
            writer.add_page(page)

        # Save output with timestamp
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        filename = f"Sorted_Output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return send_file(output, as_attachment=True, download_name=filename, mimetype="application/pdf")

    return render_template("index.html", message=None)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
