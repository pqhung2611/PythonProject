text = "Tất toán một phần Tiền Gửi Có Kỳ Hạn"
teams = ["CHEL","MU","LIV","ARS"]
scores = [63,69,67,55,98,45]

#upper lower
print(text.upper())
print(text.lower())
print(text.title()) #Viết hoa toàn bộ chữ cái đầu trong text
print(text.capitalize()) #Viết hoa only chữ cái đầu dòng
print(text.swapcase()) #Ngược lại với text (hoa -> thường)

#Độ dài của text
print(len(text))

#In text từ vị trí
print(text[1])
print(text[2:])

#Kiếm vị trí của text
print(text.index("o"))

#Thay thế
print(text.replace("một","hai"))

#Xuống dòng trong Python
print("Dòng 1\nDòng 2")
print("""Dòng 3
Dòng 4""")

#In list
print(teams[0])
print(teams[1:3]) #search vị trí 1 đến 2
teams.append(scores[0])
print(teams)
teams.insert(1,"REAL")
print(teams)
teams.remove(teams[1])
print(teams)
print(teams.index("ARS"))
print(teams.count("ARS"))
teams.reverse()
print(teams)
teams2 = teams.copy()
print(teams2)