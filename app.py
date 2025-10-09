import streamlit as st
import PyPDF2
import io, re
from datetime import datetime
from collections import defaultdict

st.set_page_config(page_title="PDF Sorter", page_icon="📄")
st.title("📄 Advanced PDF Sorter & Merger")

# Options
keep_invoice = st.checkbox("Keep Invoice", value=True)
crop_invoice = st.checkbox("Crop Invoice (Fit for 4x4 Label)", value=False)
include_tax_invoice = st.checkbox("Include TAX INVOICE", value=True)
merge_files = st.checkbox("Merge Files", value=True)
print_datetime = st.checkbox("Print Date/Time on Label", value=True)

uploaded_files = st.file_uploader("Upload PDF(s)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    courier_pages = defaultdict(lambda: defaultdict(list))

    for uploaded_file in uploaded_files:
        reader = PyPDF2.PdfReader(uploaded_file)
        for page in reader.pages:
            text = page.extract_text() or ""

            # Extract Courier
            m = re.search(r"(Delivery\s*Partner|Courier)[:\s-]*([^\n\r]+)", text, re.I)
            courier = m.group(2).strip() if m else "Others"
            if "valmoexpress" in courier.lower():
                courier = "Valmo"

            # Extract Sold By
            sold_match = re.search(r"Sold\s*By[:\s-]*([^\n\r]+)", text, re.I)
            sold_by = sold_match.group(1).strip() if sold_match else "UnknownSeller"

            # Skip TAX INVOICE if not selected
            if not include_tax_invoice and "TAX INVOICE" in text.upper():
                continue

            # Add datetime watermark
            if print_datetime:
                watermark = datetime.now().strftime("%Y-%m-%d %H:%M")
                page.add_annotation({
                    "subtype": "/Text",
                    "contents": watermark,
                    "rect": [50, 750, 200, 770]
                })

            courier_pages[courier][sold_by].append(page)

    # Build output PDF
    writer = PyPDF2.PdfWriter()
    for courier in sorted(courier_pages.keys()):
        for seller in sorted(courier_pages[courier].keys()):
            for p in courier_pages[courier][seller]:
                writer.add_page(p)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)

    st.success("✅ PDF Processed & Sorted!")
    st.download_button(
        "📥 Download Final PDF",
        data=output,
        file_name=f"Sorted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf"
    )
