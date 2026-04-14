x = 10
y = 10
n = 3
text = "Hello World, n = {2}, x = {0}, y = {1}"

def chu_vi(x,y):
    return (x+y)*2

def dien_tich(x,y):
    return x*y

def kiem_tra_chan_le(n):
    if n % 2 == 0:
        return "Chẵn"
    else:
        return "Lẻ"

def kiem_tra_so_lon_hon(x,y):
    if x > y:
        return x
    elif y > x:
        return y
    else: return "Hai số bằng nhau"

def tim_so_nho_nhat(*so):
    return min(so)

def tong_day_so_tang_dan(n):
    i = 1
    summary = 0
    while i <= n:
        summary = i + summary
        i = i +1
    return summary

print(text.format(x,y,n))
print(f"Số nhỏ nhấy trong dãy là: {tim_so_nho_nhat(x,y,n)}")
print(f"Tổng dãy số tăng dần: {tong_day_so_tang_dan(n)}")
print(f"Số lớn hơn: {kiem_tra_so_lon_hon(x,y)}")
print(f"Kiểm tra chẵn lẻ: {kiem_tra_chan_le(n)}")
print(f"Chu vi: {chu_vi(x,y)}")
print(f"Diện tích: {dien_tich(x,y)}")

#in bảng cửu chương từ 1 đến 9
#for i in range(1, 10):
#    for j in range(1, 11):
#        print(f"{i} x {j} = {i*j}")
#    print()  # dòng trống giữa các bảng
#