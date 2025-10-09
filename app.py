import streamlit as st
import PyPDF2
import io
import re
from collections import defaultdict

st.set_page_config(page_title="PDF Cropper & Sorter", page_icon="📄")

st.title("📄 PDF Sorter (Courier → SKU → Size → Qty)")

uploaded_file = st.file_uploader("Upload your PDF", type="pdf")

if uploaded_file is not None:
    reader = PyPDF2.PdfReader(uploaded_file)

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

    st.success("✅ PDF Sorted Successfully!")
    st.download_button(
        label="📥 Download Sorted PDF",
        data=output,
        file_name="Sorted_Output.pdf",
        mime="application/pdf"
    )
