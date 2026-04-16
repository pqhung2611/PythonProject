#Tuple là list cố định, không chỉnh sửa, thay đổi được. Dùng ()
a = 300
b = 200
c = 200
#and or not
if a > b and a > c:
    print("a lon nhat")
else:
    print("a khong phai so lon nhat")

x = float(input("Nhập x = "))
ope = input("Nhập toán tử: ")
y = float(input("Nhập y = "))

if ope == "+":
    print(x+y)
elif ope == "-":
    print(x-y)
elif ope == "*":
    print(x*y)
elif ope == "/":
    print(x//y)
else: print("Vui lòng nhập toán tử hợp lệ (+ - * /)")

# Count.py
def load_mapping():
    url = "https://docs.google.com/spreadsheets/d/1psWXuucE_IX_JBi5iG_m96sKuvY5xzEXYLU5BE7ug7w/gviz/tq?tqx=out:csv"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except:
        st.warning("Mapping sheet not loaded → using empty mapping")
        return pd.DataFrame(columns=["code", "name"])

mapping_df = load_mapping()
mapping_df.columns = mapping_df.columns.str.strip().str.lower()
MODULE_MAP = dict(zip(mapping_df["code"], mapping_df["name"]))