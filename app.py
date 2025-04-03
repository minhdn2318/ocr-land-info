import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_bytes
import cv2
import numpy as np
import re
import streamlit as st
from docxtpl import DocxTemplate
import os
import time

# Chỉ định đường dẫn Tesseract
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
POPPLER_PATH = "/usr/bin"  # Đường dẫn mặc định trên Linux

st.title("📜 Trích xuất thông tin thửa đất từ PDF scanner")

# Hàm tiền xử lý ảnh để tăng chất lượng OCR
def preprocess_image(img):
    img = np.array(img)  # Chuyển đổi ảnh từ PIL sang NumPy
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)  # Chuyển về ảnh xám
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)  # Nhị phân hóa ảnh
    return thresh

# Hàm trích xuất văn bản từ PDF scan với tối ưu hóa OCR
def extract_text_from_scanned_pdf(pdf_bytes):
    images = convert_from_bytes(pdf_bytes.read(), dpi=300, poppler_path=POPPLER_PATH)  # Tăng DPI để sắc nét hơn
    extracted_text = ""
    for img in images:
        processed_img = preprocess_image(img)  # Tiền xử lý ảnh
        text = pytesseract.image_to_string(processed_img, lang="vie+eng", config="--oem 3 --psm 6")  # Tối ưu nhận diện
        extracted_text += text + "\n"
    return extracted_text.strip()

# Hàm trích xuất thông tin thửa đất
def extract_land_info(text):
    patterns = {
        "SoThua": r"thửa đất số:\s*(\d+)",
        "SoToBanDo": r"tờ bản đồ số:\s*(\d+)",
        "DienTich": r"Diện tích:\s*([\d.,]+)\s*m²?",
        "LoaiDat": r"Loại đất:\s*([\s\S]*?)\.",
        "HinhThucSuDung": r"Hình thức sử dụng đất:\s*([\s\S]*?)\.",
        "DiaChi": r"Địa chỉ:\s*([\s\S]*?)\.",
        "ThoiHanSuDung": r"Thời hạn:\s*([\s\S]*?)\.",
        "NguonGocSuDung": r"Nguồn gốc sử dụng:\s*([\s\S]*?)\.",
        "ThoiDiemDangKy": r"Thời điểm đăng ký vào sổ địa chính:\s*([\s\S]*?)\.",
        "SoPhatHanhGCN": r"Số phát hành Giấy chứng nhận:\s*([\s\S]*?)\.",
        "SoVaoSoCapGCN": r"Số vào sổ cấp Giấy chứng nhận:\s*([\s\S]*?)\.",
        "ThoiDiemDangKyGCN": r"Thời điểm đăng ký:\s*([\s\S]*?)\.",
        "NoiDung": r"Ghi chú:\s*([\s\S]*?)\."
    }

    extracted_info = {key: (re.search(pattern, text, re.IGNORECASE).group(1).strip() if re.search(pattern, text, re.IGNORECASE) else "") for key, pattern in patterns.items()}

    # Xử lý nhiều người sử dụng đất
    nguoi_su_dung_matches = re.findall(r"(?:Ông|Bà):\s*([\w\s]+),\s*CCCD số:\s*(\d+)(?:,\s*Địa chỉ:\s*([\s\S]*?))?\.", text)
    nguoi_su_dung = {f"TenNguoi_{i+1}": ten.strip() for i, (ten, _, _) in enumerate(nguoi_su_dung_matches)}
    nguoi_su_dung.update({f"SoCCCD_{i+1}": cccd.strip() for i, (_, cccd, _) in enumerate(nguoi_su_dung_matches)})
    nguoi_su_dung.update({f"DiaChiNguoi_{i+1}": dia_chi.strip() if dia_chi else "" for i, (_, _, dia_chi) in enumerate(nguoi_su_dung_matches)})

    return extracted_info, nguoi_su_dung

# Hàm điền thông tin vào template DOCX
def fill_template_with_data(template_path, land_info, nguoi_su_dung):
    doc = DocxTemplate(template_path)
    context = {**land_info, **nguoi_su_dung}
    doc.render(context)
    output_path = "output_land_info.docx"
    doc.save(output_path)
    return output_path

# Upload file PDF
uploaded_file = st.file_uploader("📂 Chọn file PDF", type=["pdf"])

if uploaded_file:
    text = extract_text_from_scanned_pdf(uploaded_file)
    land_info, nguoi_su_dung = extract_land_info(text)

    if st.button("📥 Xuất file DOCX và Tải về"):
        with st.spinner("Đang xuất file DOCX..."):
            time.sleep(2)
            template_path = "template.docx"
            docx_file = fill_template_with_data(template_path, land_info, nguoi_su_dung)

        st.success("Xuất file thành công!")
        
        with open(docx_file, "rb") as file:
            st.download_button(
                label="Tải file DOCX",
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
