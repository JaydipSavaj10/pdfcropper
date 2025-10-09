import io
import re
import PyPDF2
from collections import defaultdict
from flask import Flask, render_template, request, send_file, flash, redirect, url_for

app = Flask(__name__)
app.secret_key = "secret123"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'pdf' not in request.files:
        flash("No file uploaded")
        return redirect(url_for('index'))

    file = request.files['pdf']
    if file.filename == '':
        flash("No file selected")
        return redirect(url_for('index'))

    # Read PDF directly from memory
    reader = PyPDF2.PdfReader(file.stream)

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

    # Build output PDF in memory
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

    # Directly return the file (never stored on disk)
    return send_file(
        output,
        as_attachment=True,
        download_name="Sorted_Output.pdf",
        mimetype="application/pdf"
    )

if __name__ == "__main__":
    app.run(debug=True)
