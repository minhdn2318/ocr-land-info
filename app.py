import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_bytes
import re
import streamlit as st
from docxtpl import DocxTemplate
import os
import time

# Chỉ định đường dẫn Tesseract
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
POPPLER_PATH = "/usr/bin"  # Đường dẫn mặc định trên Linux

st.title("📜 Trích xuất thông tin thửa đất từ PDF scanner")

# Hàm chuẩn hóa văn bản, sửa lỗi OCR
def clean_text(text):
    replacements = {
        "m°": "m²",
        "m 2": "m²",
        "lôai": "loại",
        "địạ": "địa",
        "CCCD sô": "CCCD số",
        "GCN:": "Giấy chứng nhận:",
        # Thêm các lỗi OCR phổ biến khác
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    return text.strip()

# Hàm trích xuất văn bản từ PDF scan
def extract_text_from_scanned_pdf(pdf_bytes):
    images = convert_from_bytes(pdf_bytes.read(), poppler_path=POPPLER_PATH)
    extracted_text = ""
    for img in images:
        text = pytesseract.image_to_string(img, lang="vie")  # OCR tiếng Việt
        extracted_text += text + "\n"
    return clean_text(extracted_text)  # Áp dụng sửa lỗi OCR

# Hàm trích xuất thông tin thửa đất và người sử dụng đất
def extract_land_info(text):
    thua_so = re.search(r"Thửa đất số:\s*(\d+)", text, re.IGNORECASE)
    to_ban_do_so = re.search(r"tờ bản đồ số:\s*(\d+)", text, re.IGNORECASE)
    dien_tich = re.search(r"Diện tích:\s*([\d.,]+)\s*m²?", text, re.IGNORECASE)

    # Dùng dấu chấm (.) để kết thúc các trường nhiều dòng
    loai_dat = re.search(r"Loại đất:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    hinh_thuc_su_dung = re.search(r"Hình thức sử dụng đất:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    dia_chi = re.search(r"Địa chỉ:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    thoi_han_su_dung = re.search(r"Thời hạn:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    nguon_goc_su_dung = re.search(r"Nguồn gốc sử dụng:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    thoi_diem_dang_ky = re.search(r"Thời điểm đăng ký vào sổ địa chính:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    so_phat_hanh_GCN = re.search(r"Số phát hành Giấy chứng nhận:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    so_vao_so_cap_GCN = re.search(r"Số vào sổ cấp Giấy chứng nhận:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    thoi_diem_dang_ky_GCN = re.search(r"Thời điểm đăng ký:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    noi_dung = re.search(r"Ghi chú:\s*([\s\S]*?)\.", text, re.IGNORECASE)

    # Xử lý nhiều người sử dụng đất
    nguoi_su_dung_matches = re.findall(
        r"(?:Ông|Bà):\s*([^\n,]+?),\s*CCCD số:\s*(\d+)(?:,\s*Địa chỉ:\s*([\s\S]*?))?\.",
        text
    )
    
    nguoi_su_dung = {}
    for i, (ten, cccd, dia_chi) in enumerate(nguoi_su_dung_matches, start=1):
        nguoi_su_dung[f"TenNguoi_{i}"] = ten.strip()
        nguoi_su_dung[f"SoCCCD_{i}"] = cccd.strip()
        nguoi_su_dung[f"DiaChiNguoi_{i}"] = dia_chi.strip() if dia_chi else ""

    return {
        "SoThua": thua_so.group(1).strip() if thua_so else "",
        "SoToBanDo": to_ban_do_so.group(1).strip() if to_ban_do_so else "",
        "DienTich": dien_tich.group(1).strip() if dien_tich else "",
        "LoaiDat": loai_dat.group(1).strip() if loai_dat else "",
        "HinhThucSuDung": hinh_thuc_su_dung.group(1).strip() if hinh_thuc_su_dung else "",
        "DiaChi": dia_chi.group(1).strip() if dia_chi else "",
        "ThoiHanSuDung": thoi_han_su_dung.group(1).strip() if thoi_han_su_dung else "",
        "NguonGocSuDung": nguon_goc_su_dung.group(1).strip() if nguon_goc_su_dung else "",
        "ThoiDiemDangKy": thoi_diem_dang_ky.group(1).strip() if thoi_diem_dang_ky else "",
        "SoPhatHanhGCN": so_phat_hanh_GCN.group(1).strip() if so_phat_hanh_GCN else "",
        "SoVaoSoCapGCN": so_vao_so_cap_GCN.group(1).strip() if so_vao_so_cap_GCN else "",
        "ThoiDiemDangKyGCN": thoi_diem_dang_ky_GCN.group(1).strip() if thoi_diem_dang_ky_GCN else "",
        "NoiDung": noi_dung.group(1).strip() if noi_dung else ""
    }, nguoi_su_dung

# Hàm điền thông tin vào template DOCX
def fill_template_with_data(template_path, land_info, nguoi_su_dung, new_name=None):
    doc = DocxTemplate(template_path)
    context = {**land_info, **nguoi_su_dung}

    if new_name:
        context["TenNguoi_1"] = new_name.strip()

    doc.render(context)

    # Tạo tên file động theo tên người sử dụng
    ten_nguoi = context.get("TenNguoi_1", "nguoi_su_dung").replace(" ", "_")
    output_path = f"GCN_{ten_nguoi}.docx"
    doc.save(output_path)
    return output_path

# Upload file PDF
uploaded_file = st.file_uploader("📂 Chọn file PDF", type=["pdf"])

if uploaded_file:
    text = extract_text_from_scanned_pdf(uploaded_file)
    land_info, nguoi_su_dung = extract_land_info(text)  # Trích xuất thông tin

    if st.button("📥 Xuất file DOCX và Tải về"):
        with st.spinner("Đang xuất file DOCX..."):
            time.sleep(2)  # Giả lập thời gian xử lý
            template_path = "template.docx"
            docx_file = fill_template_with_data(template_path, land_info, nguoi_su_dung)

        st.success("Xuất file thành công!")
        
        # Cho phép tải file DOCX
        with open(docx_file, "rb") as file:
            st.download_button(
                label="Tải file DOCX",
                data=file.read(),
                file_name=docx_file,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    # Hiển thị kết quả trích xuất
    st.subheader("🏠 Thông tin thửa đất:")
    for key, value in land_info.items():
        st.write(f"**{key}:** {value}")

    # Hiển thị thông tin từng người sử dụng đất
    st.subheader("👤 Người sử dụng đất:")
    for i in range(1, len(nguoi_su_dung) // 3 + 1):
        st.write(f"**Người {i}:** {nguoi_su_dung.get(f'TenNguoi_{i}', '')}")
        st.write(f"**CCCD:** {nguoi_su_dung.get(f'SoCCCD_{i}', '')}")
        st.write(f"**Địa chỉ:** {nguoi_su_dung.get(f'DiaChiNguoi_{i}', '')}")

    with st.expander("📄 Văn bản trích xuất từ PDF (OCR)"):
        st.text_area("Nội dung:", text, height=300)