import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_bytes
import re
import streamlit as st
from docx import Document
import os

# Chỉ định đường dẫn Tesseract
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
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
    thuad_so = re.search(r"Thửa đất số:\s*(\d+)", text, re.IGNORECASE)
    to_ban_do_so = re.search(r"tờ bản đồ số:\s*(\d+)", text, re.IGNORECASE)
    dien_tich = re.search(r"Diện tích:\s*([\d.,]+)\s*m²?", text, re.IGNORECASE)
    loai_dat = re.search(r"Loại đất:\s*(.*)", text, re.IGNORECASE)
    hinh_thuc_su_dung = re.search(r"Hình thức sử dụng:\s*(.*)", text, re.IGNORECASE)
    dia_chi = re.search(r"Địa chỉ thửa đất:\s*(.*)", text, re.IGNORECASE)
    thoi_han_su_dung = re.search(r"Thời hạn sử dụng:\s*(.*)", text, re.IGNORECASE)
    nguon_goc_su_dung = re.search(r"Nguồn gốc sử dụng:\s*(.*)", text, re.IGNORECASE)
    nguoi_su_dung = re.search(r"Người sử dụng đất:\s*(.*)", text, re.IGNORECASE)
    thoi_diem_dang_ky = re.search(r"Thời điểm đăng ký vào sổ địa chính:\s*(.*)", text, re.IGNORECASE)
    so_phat_hanh_GCN = re.search(r"Số phát hành GCN:\s*(.*)", text, re.IGNORECASE)
    so_vao_so_cap_GCN = re.search(r"Số vào sổ cấp GCN:\s*(.*)", text, re.IGNORECASE)
    thoi_diem_dang_ky_GCN = re.search(r"Thời điểm đăng ký:\s*(.*)", text, re.IGNORECASE)
    noi_dung = re.search(r"Nội dung:\s*(.*)", text, re.IGNORECASE)

    return {
        "SoThua": thuad_so.group(1) if thuad_so else "Không tìm thấy",
        "SoToBanDo": to_ban_do_so.group(1) if to_ban_do_so else "Không tìm thấy",
        "DienTich": dien_tich.group(1) if dien_tich else "Không tìm thấy",
        "LoaiDat": loai_dat.group(1) if loai_dat else "Không tìm thấy",
        "HinhThucSuDung": hinh_thuc_su_dung.group(1) if hinh_thuc_su_dung else "Không tìm thấy",
        "DiaChi": dia_chi.group(1) if dia_chi else "Không tìm thấy",
        "ThoiHanSuDung": thoi_han_su_dung.group(1) if thoi_han_su_dung else "Không tìm thấy",
        "NguonGocSuDung": nguon_goc_su_dung.group(1) if nguon_goc_su_dung else "Không tìm thấy",
        "NguoiSuDung": nguoi_su_dung.group(1) if nguoi_su_dung else "Không tìm thấy",
        "ThoiDiemDangKy": thoi_diem_dang_ky.group(1) if thoi_diem_dang_ky else "Không tìm thấy",
        "SoPhatHanhGCN": so_phat_hanh_GCN.group(1) if so_phat_hanh_GCN else "Không tìm thấy",
        "SoVaoSoCapGCN": so_vao_so_cap_GCN.group(1) if so_vao_so_cap_GCN else "Không tìm thấy",
        "ThoiDiemDangKyGCN": thoi_diem_dang_ky_GCN.group(1) if thoi_diem_dang_ky_GCN else "Không tìm thấy",
        "NoiDung": noi_dung.group(1) if noi_dung else "Không tìm thấy"
    }

# Hàm điền thông tin vào template DOCX
def fill_template_with_data(template_path, land_info):
    doc = Document(template_path)
    
    # Thay thế các placeholder trong template bằng dữ liệu
    for paragraph in doc.paragraphs:
        for key, value in land_info.items():
            if f"{{{{{key}}}}}" in paragraph.text:
                paragraph.text = paragraph.text.replace(f"{{{{{key}}}}}", value)
    
    # Lưu file DOCX đã điền thông tin
    output_path = "output_land_info.docx"
    doc.save(output_path)
    return output_path

# Upload file
uploaded_file = st.file_uploader("📂 Chọn file PDF", type=["pdf"])

if uploaded_file:
    text = extract_text_from_scanned_pdf(uploaded_file)
    land_info = extract_land_info(text)

    # Hiển thị kết quả
    st.subheader("🏠 Thông tin thửa đất:")
    for key, value in land_info.items():
        st.write(f"**{key}:** {value}")

    # Hiển thị toàn bộ văn bản OCR
    st.subheader("📄 Nội dung OCR:")
    st.text_area("Nội dung nhận diện:", text, height=300)

    # Thêm nút xuất file DOCX
    if st.button("📥 Xuất file DOCX"):
        template_path = "template.docx"  # Đảm bảo rằng template.docx có trong thư mục hiện tại
        docx_file = fill_template_with_data(template_path, land_info)
        st.download_button(
            label="Tải file DOCX",
            data=open(docx_file, "rb").read(),
            file_name=docx_file,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
