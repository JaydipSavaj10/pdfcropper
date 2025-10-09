from flask import Flask, request, send_file, render_template
import PyPDF2
import io
import re
from collections import defaultdict
from datetime import datetime

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def upload_pdf():
    if request.method == "POST":
        if "pdf_file" not in request.files:
            return render_template("index.html", message="No file selected")
        
        file = request.files["pdf_file"]
        if file.filename == "":
            return render_template("index.html", message="No file selected")

        reader = PyPDF2.PdfReader(file)

        # courier -> sku -> size -> qty -> [pages]
        courier_pages = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

        for page in reader.pages:
            text = page.extract_text() or ""

            # Detect courier
            if "ValmoPlus" in text:
                courier = "ValmoPlus"
            elif "Valmo Pickup" in text:
                courier = "Valmo"
            elif "Delhivery" in text:
                courier = "Delhivery"
            elif "Xpress Bees" in text:
                courier = "XpressBees"
            else:
                courier = "Others"

            # Extract SKU
            sku_match = re.search(r"Product Details\s*[\s\S]*?\n(.+?)\s+Size", text)
            sku = sku_match.group(1).strip() if sku_match else "UnknownSKU"

            # Extract Size
            size_match = re.search(r"Size\s+([^\s]+)", text)
            size = size_match.group(1).strip() if size_match else "UnknownSize"

            # Extract Qty
            qty_match = re.search(r"Qty\s+(\d+)", text)
            qty = int(qty_match.group(1)) if qty_match else 0

            courier_pages[courier][sku][size][qty].append(page)

        # Build sorted PDF
        writer = PyPDF2.PdfWriter()
        for courier in ["ValmoPlus", "Valmo", "Delhivery", "XpressBees", "Others"]:
            if courier not in courier_pages:
                continue
            for sku in sorted(courier_pages[courier].keys()):
                for size in sorted(courier_pages[courier][sku].keys()):
                    for qty in sorted(courier_pages[courier][sku][size].keys()):
                        for p in courier_pages[courier][sku][size][qty]:
                            writer.add_page(p)

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)

        # Unique filename with timestamp
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        filename = f"Sorted_Output_{timestamp}.pdf"

        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf"
        )

    return render_template("index.html", message=None)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
