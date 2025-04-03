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

# Hàm trích xuất văn bản từ PDF scan
def extract_text_from_scanned_pdf(pdf_bytes):
    images = convert_from_bytes(pdf_bytes.read(), poppler_path=POPPLER_PATH)
    extracted_text = ""
    for img in images:
        text = pytesseract.image_to_string(img, lang="vie")  # OCR tiếng Việt
        extracted_text += text + "\n"
    return extracted_text

# Hàm trích xuất thông tin thửa đất, hỗ trợ xuống dòng và dấu chấm kết thúc
def extract_land_info(text):
    thua_so = re.search(r"Thửa đất số:\s*(\d+)", text, re.IGNORECASE)
    to_ban_do_so = re.search(r"tờ bản đồ số:\s*(\d+)", text, re.IGNORECASE)
    dien_tich = re.search(r"Diện tích:\s*([\d.,]+)\s*m²?", text, re.IGNORECASE)

    # Sử dụng dấu chấm (.) làm điểm kết thúc cho các trường nhiều dòng
    loai_dat = re.search(r"Loại đất:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    hinh_thuc_su_dung = re.search(r"Hình thức sử dụng đất:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    dia_chi = re.search(r"Địa chỉ:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    thoi_han_su_dung = re.search(r"Thời hạn:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    nguon_goc_su_dung = re.search(r"Nguồn gốc sử dụng:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    nguoi_su_dung = re.search(r"Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    thoi_diem_dang_ky = re.search(r"Thời điểm đăng ký vào sổ địa chính:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    so_phat_hanh_GCN = re.search(r"Số phát hành Giấy chứng nhận:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    so_vao_so_cap_GCN = re.search(r"Số vào sổ cấp Giấy chứng nhận:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    thoi_diem_dang_ky_GCN = re.search(r"Thời điểm đăng ký:\s*([\s\S]*?)\.", text, re.IGNORECASE)
    noi_dung = re.search(r"Ghi chú:\s*([\s\S]*?)\.", text, re.IGNORECASE)

    # Trả về dữ liệu, loại bỏ khoảng trắng thừa
    return {
        "SoThua": thua_so.group(1).strip() if thua_so else "Không tìm thấy",
        "SoToBanDo": to_ban_do_so.group(1).strip() if to_ban_do_so else "Không tìm thấy",
        "DienTich": dien_tich.group(1).strip() if dien_tich else "Không tìm thấy",
        "LoaiDat": loai_dat.group(1).strip() if loai_dat else "Không tìm thấy",
        "HinhThucSuDung": hinh_thuc_su_dung.group(1).strip() if hinh_thuc_su_dung else "Không tìm thấy",
        "DiaChi": dia_chi.group(1).strip() if dia_chi else "Không tìm thấy",
        "ThoiHanSuDung": thoi_han_su_dung.group(1).strip() if thoi_han_su_dung else "Không tìm thấy",
        "NguonGocSuDung": nguon_goc_su_dung.group(1).strip() if nguon_goc_su_dung else "Không tìm thấy",
        "NguoiSuDung": nguoi_su_dung.group(1).strip() if nguoi_su_dung else "Không tìm thấy",
        "ThoiDiemDangKy": thoi_diem_dang_ky.group(1).strip() if thoi_diem_dang_ky else "Không tìm thấy",
        "SoPhatHanhGCN": so_phat_hanh_GCN.group(1).strip() if so_phat_hanh_GCN else "Không tìm thấy",
        "SoVaoSoCapGCN": so_vao_so_cap_GCN.group(1).strip() if so_vao_so_cap_GCN else "Không tìm thấy",
        "ThoiDiemDangKyGCN": thoi_diem_dang_ky_GCN.group(1).strip() if thoi_diem_dang_ky_GCN else "Không tìm thấy",
        "NoiDung": noi_dung.group(1).strip() if noi_dung else "Không tìm thấy"
    }


# Hàm điền thông tin vào template DOCX
def fill_template_with_data(template_path, land_info):
    doc = DocxTemplate(template_path)
    
    # Thay thế các placeholder trong template bằng dữ liệu
    context = {key: value for key, value in land_info.items()}
    doc.render(context)

    # Lưu file DOCX đã điền thông tin
    output_path = "output_land_info.docx"
    doc.save(output_path)
    return output_path

# Upload file
uploaded_file = st.file_uploader("📂 Chọn file PDF", type=["pdf"])

if uploaded_file:
    text = extract_text_from_scanned_pdf(uploaded_file)
    land_info = extract_land_info(text)

    # Thêm nút xuất file DOCX lên đầu
    if st.button("📥 Xuất file DOCX và Tải về"):
        # Hiển thị progress bar
        with st.spinner("Đang xuất file DOCX..."):
            time.sleep(2)  # Giả lập thời gian xuất file
            template_path = "template.docx"  # Đảm bảo rằng template.docx có trong thư mục hiện tại
            docx_file = fill_template_with_data(template_path, land_info)

        st.success("Xuất file thành công!")
        
        # Tải file DOCX ngay lập tức
        with open(docx_file, "rb") as file:
            st.download_button(
                label="Tải file DOCX",
                data=file.read(),
                file_name=docx_file,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    # Hiển thị kết quả thông tin thửa đất
    st.subheader("🏠 Thông tin thửa đất:")
    for key, value in land_info.items():
        # Nếu không tìm thấy, không yêu cầu nhập lại thông tin
        st.write(f"**{key}:** {value}")

    # Hiển thị toàn bộ văn bản OCR
    st.subheader("📄 Nội dung OCR:")
    st.text_area("Nội dung nhận diện:", text, height=300)
