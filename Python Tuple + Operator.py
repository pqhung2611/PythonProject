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