import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import re
import streamlit as st
import os

# Poppler đã được cài đặt bởi `poppler-utils` từ `packages.txt`
POPPLER_PATH = "/usr/bin"  # Đường dẫn mặc định trên Linux

st.title("📜 Trích xuất thông tin thửa đất từ PDF scanner")

# Hàm trích xuất văn bản từ PDF scan
def extract_text_from_scanned_pdf(pdf_bytes):
    images = convert_from_bytes(pdf_bytes.read(), poppler_path=POPPLER_PATH)
    extracted_text = ""

    for img in images:
        text = pytesseract.image_to_string(img, lang="vie")  # OCR tiếng Việt
        extracted_text += text + "\n"

    return extracted_text

# Hàm trích xuất thông tin thửa đất
def extract_land_info(text):
    thuad_so = re.search(r"Thửa đất số:\s*(\d+)", text)
    to_ban_do_so = re.search(r"Tờ bản đồ số:\s*(\d+)", text)
    dien_tich = re.search(r"Diện tích:\s*([\d.,]+)\s*m²?", text)

    return {
        "Thửa đất số": thuad_so.group(1) if thuad_so else "Không tìm thấy",
        "Tờ bản đồ số": to_ban_do_so.group(1) if to_ban_do_so else "Không tìm thấy",
        "Diện tích": dien_tich.group(1) if dien_tich else "Không tìm thấy",
    }

# Upload file
uploaded_file = st.file_uploader("📂 Chọn file PDF", type=["pdf"])

if uploaded_file:
    text = extract_text_from_scanned_pdf(uploaded_file)
    land_info = extract_land_info(text)

    # Hiển thị kết quả
    st.subheader("🏠 Thông tin thửa đất:")
    st.write(f"**Thửa đất số:** {land_info['Thửa đất số']}")
    st.write(f"**Tờ bản đồ số:** {land_info['Tờ bản đồ số']}")
    st.write(f"**Diện tích:** {land_info['Diện tích']}")

    # Hiển thị toàn bộ văn bản OCR
    st.subheader("📄 Nội dung OCR:")
    st.text_area("Nội dung nhận diện:", text, height=300)
