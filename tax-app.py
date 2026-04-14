import streamlit as st


# ====== TÍNH THUẾ LŨY TIẾN ======
def tinh_thue_luy_tien_nam(thu_nhap_tinh_thue):
    bac_thue = [
        (60_000_000, 0.05),
        (120_000_000, 0.10),
        (216_000_000, 0.15),
        (384_000_000, 0.20),
        (624_000_000, 0.25),
        (960_000_000, 0.30),
        (float('inf'), 0.35),
    ]

    thue = 0
    thu_nhap_con_lai = thu_nhap_tinh_thue
    muc_truoc = 0

    for muc, ty_le in bac_thue:
        if thu_nhap_con_lai <= 0:
            break

        muc_chiu_thue = min(thu_nhap_con_lai, muc - muc_truoc)
        thue += muc_chiu_thue * ty_le

        thu_nhap_con_lai -= muc_chiu_thue
        muc_truoc = muc

    return thue


# ====== GIAO DIỆN ======
st.set_page_config(page_title="Quyết Toán Thuế TNCN", page_icon="💰",layout="centered")

st.title("💰 App Quyết Toán Thuế TNCN")
#st.text("hungpq7")
st.write("Nhập thông tin để tính số thuế phải nộp / hoàn lại")

# Input
tong_thu_nhap = st.number_input("Tổng thu nhập chịu thuế (VND/năm)", min_value=0, step=1_000_000,placeholder="Nhập tổng thu nhập chịu thuế (VND/năm)")

so_nguoi_phu_thuoc = st.number_input("Số người phụ thuộc", min_value=0, step=1,placeholder="Nhập số người phụ thuộc")

auto_giam_tru = st.checkbox("Tự động tính giảm trừ gia cảnh", value=True)

if auto_giam_tru:
    giam_tru = 132_000_000 + so_nguoi_phu_thuoc * 52_800_000
    st.info(f"Giảm trừ gia cảnh: {giam_tru:,.0f} VND")
else:
    giam_tru = st.number_input("Tổng giảm trừ gia cảnh (VND/năm)", min_value=0, step=1_000_000,placeholder="Nhập số tiền giảm trừ gia cảnh")

bao_hiem = st.number_input("Bảo hiểm được trừ (VND/năm)", min_value=0, step=1_000_000,placeholder="Nhập số tiền bảo hiểm được trừ (VND/năm)")

thue_da_khau_tru = st.number_input("Thuế đã khấu trừ (VND/năm)", min_value=0, step=1_000_000,placeholder="Nhập số thuế đã khấu trừ (VND/năm)")


# Button
if st.button("Tính toán"):
    thu_nhap_tinh_thue = tong_thu_nhap - giam_tru - bao_hiem

    if thu_nhap_tinh_thue <= 0:
        thue_phai_nop = 0
    else:
        thue_phai_nop = tinh_thue_luy_tien_nam(thu_nhap_tinh_thue)

    chenhlech = thue_da_khau_tru - thue_phai_nop

    st.subheader("📊 Kết quả")
    st.write(f"Thu nhập tính thuế: {thu_nhap_tinh_thue:,.0f} VND")
    st.write(f"Thuế phải nộp: {thue_phai_nop:,.0f} VND")

    if chenhlech > 0:
        st.success(f"✅ Bạn được hoàn thuế: {chenhlech:,.0f} VND")
    elif chenhlech < 0:
        st.error(f"⚠️ Bạn cần nộp thêm: {-chenhlech:,.0f} VND")
    else:
        st.info("Bạn không phải nộp thêm hoặc hoàn thuế")