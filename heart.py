import tkinter as tk
import math
import random

root = tk.Tk()
root.title("卡片跳动爱心")
W = 900
H = 800
root.geometry(f"{W}x{H}")
root.configure(bg="#121218")

canvas = tk.Canvas(root, width=W, height=H, bg="#121218", highlightthickness=0)
canvas.pack()

# 爱心参数方程，生成轮廓点位
def heart(t):
    x = 16 * math.pow(math.sin(t), 3)
    y = 13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t)
    return x, -y

point_list = []
color_list = ["#ff7b7b","#ffd17b","#fff47b","#9aff7b","#7be8ff","#b39aff","#ff9ad6"]
# 采集爱心轮廓坐标
for i in range(0, 628, 12):
    t = i / 100
    px, py = heart(t)
    point_list.append([px,py,random.choice(color_list)])

beat_count = 0
def animate():
    global beat_count
    canvas.delete("all")
    beat_count +=1
    # 心跳缩放正弦函数
    scale = 1 + 0.11 * math.sin(beat_count * 0.028)
    cx = W//2
    cy = H//2 -60
    card_w = 34
    card_h = 22
    for px,py,color in point_list:
        x1 = cx + px * scale * 11 - card_w//2
        y1 = cy + py * scale *11 - card_h//2
        x2 = x1 + card_w
        y2 = y1 + card_h
        canvas.create_rectangle(x1,y1,x2,y2,fill=color,outline="#ffffff",width=1)
    root.after(30,animate)

animate()
root.mainloop()