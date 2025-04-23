import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_bytes
import re
import os
import pandas as pd
from io import BytesIO

# Cấu hình đường dẫn cho pytesseract và poppler (nếu cần)
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
POPPLER_PATH = "/usr/bin"  # Thay nếu dùng Windows

st.set_page_config(page_title="OCR Sổ Địa Chính", layout="wide")
st.title("📜 Trích xuất thông tin thửa đất từ nhiều file PDF")

def clean_text(text):
    replacements = {
        "m°": "m²", "m 2": "m²", "lôai": "loại", "địạ": "địa", "CCCD sô": "CCCD số",
        "GCN:": "Giấy chứng nhận:", "<t": "1", "t3": "13", "tháng .": "tháng ",
        "năm²": "năm ", "năm:": "năm ", "tháng:": "tháng ", "ngày:": "ngày ", "²": ""
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    lines = text.split("\n")
    cleaned_lines = [re.sub(r"\s+", " ", line).strip() for line in lines if line.strip()]
    return "\n".join(cleaned_lines).strip()

def extract_text_from_scanned_pdf(pdf_bytes):
    images = convert_from_bytes(pdf_bytes.read(), poppler_path=POPPLER_PATH)
    extracted_text = ""
    for img in images:
        text = pytesseract.image_to_string(img, lang="vie")
        extracted_text += text + "\n"
    return clean_text(extracted_text)

def extract_loai_dat(text):
    match = re.search(r"Loại đất[:\-]?\s*(.*?)(?=\.)", text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip(";: \n") if match else ""

def extract_clean_field(text, field_label, stop_labels=None):
    if stop_labels:
        stop_pattern = '|'.join([rf"{re.escape(label)}(?:[:\-])?" for label in stop_labels])
        pattern = rf"{re.escape(field_label)}[:\-]?\s*(.*?)(?=\n\s*(?:{stop_pattern})|\n|$)"
    else:
        pattern = rf"{re.escape(field_label)}[:\-]?\s*(.*?)(?=\.\s*\n|\n|$)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""

def extract_xa_from_diachi(dia_chi):
    match = re.search(r"(xã|phường|thị trấn)\s+[^\-,\n]+", dia_chi, re.IGNORECASE)
    return match.group(0).strip().title() if match else ""

def extract_land_info_for_excel(text):
    thua_so = re.search(r"Thửa đất số:\s*(\d+)", text, re.IGNORECASE)
    to_ban_do_so = re.search(r"tờ bản đồ số:\s*(\d+)", text, re.IGNORECASE)
    dien_tich = re.search(r"Diện tích:\s*([\d.,]+)\s*m²?", text, re.IGNORECASE)
    dia_chi = extract_clean_field(text, "Địa chỉ", ["Thời hạn", "Nguồn gốc", "Tên tài sản"])
    so_phat_hanh_GCN = ""
    context_match = re.search(r"(CHI NHÁNH[\s\S]{0,300})", text, re.IGNORECASE)
    if context_match:
        context_block = context_match.group(1)
        match = re.search(r"\b([A-Z]{2}\s*\d{6,})\b", context_block)
        if match:
            so_phat_hanh_GCN = match.group(1).strip()

    nguoi_su_dung_matches = re.findall(
        r"(?:Ông|Bà):\s*([^\n,]+?),\s*CCCD số:\s*(\d+)", text
    )
    nguoi_su_dung = nguoi_su_dung_matches[0][0].strip() if nguoi_su_dung_matches else ""

    return {
        "Chủ sở hữu": nguoi_su_dung,
        "Thửa": thua_so.group(1).strip() if thua_so else "",
        "Tờ": to_ban_do_so.group(1).strip() if to_ban_do_so else "",
        "Diện tích": dien_tich.group(1).strip() if dien_tich else "",
        "Xã": extract_xa_from_diachi(dia_chi),
        "Số phát hành": so_phat_hanh_GCN
    }

# Giao diện upload
uploaded_files = st.file_uploader("📂 Chọn nhiều file PDF", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    results = []
    with st.spinner("🔍 Đang xử lý các file..."):
        for uploaded_file in uploaded_files:
            text = extract_text_from_scanned_pdf(uploaded_file)
            info = extract_land_info_for_excel(text)
            info["Tên file"] = uploaded_file.name
            results.append(info)

    df = pd.DataFrame(results)
    st.success("✅ Đã trích xuất xong!")

    # Hiển thị bảng kết quả
    st.dataframe(df)

    # Xuất Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name="ThongTinDat")
    st.download_button(
        label="📥 Tải Excel",
        data=output.getvalue(),
        file_name="ThongTinThuaDat.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
