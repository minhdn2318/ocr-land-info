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

def clean_text(text):
    replacements = {
        "m°": "m²",
        "m 2": "m²",
        "lôai": "loại",
        "địạ": "địa",
        "CCCD sô": "CCCD số",
        "GCN:": "Giấy chứng nhận:",
        # Các lỗi OCR phổ biến về ngày tháng
        "<t": "1",                  # ví dụ <t3 -> 13
        "t3": "13",                 # fallback nếu OCR bỏ mất dấu
        "tháng .": "tháng ",
        "năm²": "năm ",
        "năm:": "năm ",
        "tháng:": "tháng ",
        "ngày:": "ngày ",
        "²": "",                    # loại bỏ ký tự mũ (thường OCR nhầm)
    }

    for wrong, right in replacements.items():
        text = text.replace(wrong, right)

    # Thay vì xoá tất cả \n, ta chuẩn hoá từng dòng
    lines = text.split("\n")
    cleaned_lines = [re.sub(r"\s+", " ", line).strip() for line in lines if line.strip()]
    return "\n".join(cleaned_lines).strip()

def normalize_vietnamese_date(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    match = re.search(r"ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", text)
    if match:
        day, month, year = match.groups()
        return f"{int(day):02}/{int(month):02}/{year}"
    return ""


# Hàm trích xuất văn bản từ PDF scan
def extract_text_from_scanned_pdf(pdf_bytes):
    images = convert_from_bytes(pdf_bytes.read(), poppler_path=POPPLER_PATH)
    extracted_text = ""
    for img in images:
        text = pytesseract.image_to_string(img, lang="vie")  # OCR tiếng Việt
        extracted_text += text + "\n"
    return clean_text(extracted_text)  # Áp dụng sửa lỗi OCR

def extract_clean_field(text, field_label, stop_labels=None):
    if stop_labels:
        stop_pattern = '|'.join([rf"{re.escape(label)}(?:[:\-])?" for label in stop_labels])
        pattern = rf"{re.escape(field_label)}[:\-]?\s*(.*?)(?=\n\s*(?:{stop_pattern})|\n|$)"
    else:
        # Dừng tại dấu chấm nếu đứng cuối câu (theo sau là xuống dòng hoặc kết thúc file)
        pattern = rf"{re.escape(field_label)}[:\-]?\s*(.*?)(?=\.\s*\n|\n|$)"

    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        result = match.group(1).strip()

        # # Nếu kết thúc bằng dấu ngoặc kép lạ hoặc ký tự lỗi → xoá
        # result = re.sub(r'[”"\'›»]+$', '', result)
        # result = re.sub(r"\s*[\dđa]{1,2}\s*$", "", result)

        return result.strip()
    return ""


def extract_loai_dat(text):
    pattern = r"Loại đất[:\-]?\s*(.*?)(?=\.)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        content = match.group(1).strip()
        return content.strip(";: \n")
    return ""

# def extract_field(text, field_label):
#     pattern = rf"({field_label}[:\-]?\s*[\w\s,/.]+(?:\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*m²?)?)"  # Regex sửa lại cho phù hợp với Loại đất
#     match = re.search(pattern, text, re.IGNORECASE)
#     return match.group(1).strip() if match else ""

def extract_land_info(text):
    text = clean_text(text)

    thua_so = re.search(r"Thửa đất số:\s*(\d+)", text, re.IGNORECASE)
    to_ban_do_so = re.search(r"tờ bản đồ số:\s*(\d+)", text, re.IGNORECASE)
    dien_tich = re.search(r"Diện tích:\s*([\d.,]+)\s*m²?", text, re.IGNORECASE)

    loai_dat = extract_loai_dat(text)
    hinh_thuc_su_dung = extract_clean_field(text, "Hình thức sử dụng đất", ["Địa chỉ", "Thời hạn"])
    dia_chi = extract_clean_field(text, "Địa chỉ", ["Thời hạn", "Nguồn gốc", "Tên tài sản"])
    thoi_han_su_dung = extract_loai_dat(text)
    nguon_goc_su_dung = extract_clean_field(text, "Nguồn gốc sử dụng", ["Thời điểm đăng ký", "Số vào sổ"])
    thoi_diem_dang_ky = extract_clean_field(text, "Thời điểm đăng ký vào sổ địa chính", ["Số vào sổ", "Ghi chú"])
    so_vao_so_cap_GCN = extract_clean_field(text, "Số vào sổ cấp Giấy chứng nhận", ["Ghi chú", "Chi nhánh"])
    noi_dung = re.search(r"Ghi chú[:\-]?\s*(.*?)(?=\.)", text, re.IGNORECASE | re.DOTALL)

    thoi_diem_dang_ky_GCN_raw = re.search(r"(ngày\s*\d{0,2}[\s\S]{0,60}năm\s*\d{4})", text, re.IGNORECASE)

    context_match = re.search(r"(CHI NHÁNH[\s\S]{0,300})", text, re.IGNORECASE)
    so_phat_hanh_GCN = None
    if context_match:
        context_block = context_match.group(1)
        so_phat_hanh_GCN = re.search(r"\b([A-Z]{2}\s*\d{6,})\b", context_block)

    nguoi_su_dung_matches = re.findall(
        r"(?:Ông|Bà):\s*([^\n,]+?),\s*CCCD số:\s*(\d+)(?:,\s*Địa chỉ:\s*([\s\S]*?))?\.",
        text
    )
    nguoi_su_dung = {}
    for i, (ten, cccd, dia_chi_nguoi) in enumerate(nguoi_su_dung_matches, start=1):
        nguoi_su_dung[f"TenNguoi_{i}"] = ten.strip()
        nguoi_su_dung[f"SoCCCD_{i}"] = cccd.strip()
        nguoi_su_dung[f"DiaChiNguoi_{i}"] = dia_chi_nguoi.strip() if dia_chi_nguoi else ""

    return {
        "SoThua": thua_so.group(1).strip() if thua_so else "",
        "SoToBanDo": to_ban_do_so.group(1).strip() if to_ban_do_so else "",
        "DienTich": dien_tich.group(1).strip() if dien_tich else "",
        "LoaiDat": loai_dat,
        "HinhThucSuDung": hinh_thuc_su_dung,
        "DiaChi": dia_chi,
        "ThoiHanSuDung": thoi_han_su_dung,
        "NguonGocSuDung": nguon_goc_su_dung,
        "ThoiDiemDangKy": thoi_diem_dang_ky,
        "SoPhatHanhGCN": so_phat_hanh_GCN.group(1).strip() if so_phat_hanh_GCN else "",
        "SoVaoSoCapGCN": so_vao_so_cap_GCN,
        "ThoiDiemDangKyGCN": normalize_vietnamese_date(thoi_diem_dang_ky_GCN_raw.group(1)) if thoi_diem_dang_ky_GCN_raw else "",
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