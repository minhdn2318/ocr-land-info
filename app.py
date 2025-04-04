import pytesseract
from pdf2image import convert_from_bytes
import cv2
import numpy as np
import re
import streamlit as st
from docxtpl import DocxTemplate
import os
import time
import unicodedata
import unidecode

# Chỉ định đường dẫn Tesseract
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
POPPLER_PATH = "/usr/bin"  # Đường dẫn mặc định trên Linux

st.title("📜 Trích xuất thông tin thửa đất từ PDF scanner")

# Hàm tiền xử lý ảnh để tăng chất lượng OCR
def preprocess_image(img):
    img = np.array(img)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

# Chuẩn hóa văn bản đầu ra từ OCR (bỏ dấu, lowercase, xóa ký tự thừa)
def normalize_text(text):
    text = unidecode.unidecode(text)
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r"\s+", " ", text)  # Gộp nhiều khoảng trắng
    return text.lower().strip()

# Trích xuất văn bản từ PDF scan
def extract_text_from_scanned_pdf(pdf_bytes):
    images = convert_from_bytes(pdf_bytes.read(), dpi=300, poppler_path=POPPLER_PATH)
    extracted_text = ""
    for img in images:
        processed_img = preprocess_image(img)
        text = pytesseract.image_to_string(processed_img, lang="vie+eng", config="--oem 3 --psm 6")
        extracted_text += text + "\n"
    return extracted_text.strip()

# Hàm trích xuất thông tin từ text đã normalize
def extract_land_info(text):
    patterns = {
        "SoThua": r"thua dat so\s*(\d+)",
        "SoToBanDo": r"to ban do so\s*(\d+)",
        "DienTich": r"dien tich\s*([\d.,]+)\s*m2?",
        "LoaiDat": r"loai dat\s*([\w\s\-]+)",
        "HinhThucSuDung": r"hinh thuc su dung\s*([\w\s\-]+)",
        "DiaChi": r"dia chi\s*([\w\s\d\-,/.]+)",
        "ThoiHanSuDung": r"thoi han\s*([\w\s\-]+)",
        "NguonGocSuDung": r"nguon goc su dung\s*([\w\s\-]+)",
        "ThoiDiemDangKy": r"thoi diem dang ky vao so dia chinh\s*([\w\s\d\-/.]+)",
        "SoPhatHanhGCN": r"so phat hanh giay chung nhan\s*([\w\d\-/.]+)",
        "SoVaoSoCapGCN": r"so vao so cap giay chung nhan\s*([\w\d\-/.]+)",
        "ThoiDiemDangKyGCN": r"thoi diem dang ky\s*([\w\s\d\-/.]+)",
        "NoiDung": r"ghi chu\s*([\w\s\d\-/.]+)"
    }

    extracted_info = {key: (re.search(pattern, text).group(1).strip() if re.search(pattern, text) else "") for key, pattern in patterns.items()}

    # Trích xuất thông tin người sử dụng đất
    nguoi_su_dung_matches = re.findall(r"(?:ong|ba)\s*[:\-]?\s*([\w\s]+),\s*cccd so[:\-]?\s*(\d+)(?:,\s*dia chi[:\-]?\s*([\w\s\d\-,/.]+))?", text)
    nguoi_su_dung = {f"TenNguoi_{i+1}": ten.strip() for i, (ten, _, _) in enumerate(nguoi_su_dung_matches)}
    nguoi_su_dung.update({f"SoCCCD_{i+1}": cccd.strip() for i, (_, cccd, _) in enumerate(nguoi_su_dung_matches)})
    nguoi_su_dung.update({f"DiaChiNguoi_{i+1}": dia_chi.strip() if dia_chi else "" for i, (_, _, dia_chi) in enumerate(nguoi_su_dung_matches)})

    return extracted_info, nguoi_su_dung

# Điền vào template DOCX
def fill_template_with_data(template_path, land_info, nguoi_su_dung):
    doc = DocxTemplate(template_path)
    context = {**land_info, **nguoi_su_dung}
    output_path = "output_land_info.docx"
    doc.render(context)
    doc.save(output_path)
    return output_path

# Giao diện Streamlit
uploaded_file = st.file_uploader("📂 Chọn file PDF", type=["pdf"])

if uploaded_file:
    text = extract_text_from_scanned_pdf(uploaded_file)
    normalized_text = normalize_text(text)
    land_info, nguoi_su_dung = extract_land_info(normalized_text)

    if st.button("📥 Xuất file DOCX và Tải về"):
        with st.spinner("Đang xuất file DOCX..."):
            time.sleep(2)
            template_path = "template.docx"
            docx_file = fill_template_with_data(template_path, land_info, nguoi_su_dung)

        st.success("Xuất file thành công!")
        with open(docx_file, "rb") as file:
            st.download_button(
                label="📥 Tải file DOCX",
                data=file.read(),
                file_name=docx_file,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    st.subheader("🏠 Thông tin thửa đất:")
    for key, value in land_info.items():
        st.write(f"**{key}:** {value}")

    st.subheader("👤 Người sử dụng đất:")
    for i in range(1, len(nguoi_su_dung) // 3 + 1):
        st.write(f"**Người {i}:** {nguoi_su_dung.get(f'TenNguoi_{i}', '')}")
        st.write(f"**CCCD:** {nguoi_su_dung.get(f'SoCCCD_{i}', '')}")
        st.write(f"**Địa chỉ:** {nguoi_su_dung.get(f'DiaChiNguoi_{i}', '')}")
