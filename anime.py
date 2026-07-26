import tkinter as tk

root = tk.Tk()
root.title("1:1色块复刻")
W = 700
H = 700
root.geometry(f"{W}x{H}")
root.resizable(False, False)

# 画布底色和CSS完全一致 #b8a8c8
canvas = tk.Canvas(root, width=W, height=H, bg="#b8a8c8")
canvas.pack()

# 1.外层白色底板（最底层白色面板）
canvas.create_rectangle(5,5,W-5,H-5,fill="#f5f5f5",outline="#e8e8e8")

# 2.顶部紫色横条 高度26%
h_top = int(H * 0.26)
canvas.create_rectangle(5,5,W-5,h_top,fill="#cbb8d8",outline="")

# 3.左侧深紫色 top=26% 宽34% 高38%
x1 = 5
y1 = int(H * 0.26)
x2 = int(W * 0.34)
y2 = int(H * (0.26 + 0.38))
canvas.create_rectangle(x1,y1,x2,y2,fill="#4a3c5a",outline="")

# 4.中间粉色文字区 left34% 宽42%
x1 = int(W * 0.34)
y1 = int(H * 0.26)
x2 = int(W * (0.34 + 0.42))
y2 = int(H * (0.26 + 0.38))
canvas.create_rectangle(x1,y1,x2,y2,fill="#d888a8",outline="")

# 5.右侧灰色竖条 宽24%
x1 = int(W * (1 - 0.24))
y1 = int(H * 0.26)
x2 = W-5
y2 = int(H * (0.26 + 0.38))
canvas.create_rectangle(x1,y1,x2,y2,fill="#919191",outline="")

# 6.底部白色区域 高度36%
y1 = int(H * (1 - 0.36))
canvas.create_rectangle(5,y1,W-5,H-5,fill="#ffffff",outline="")

# 7.底部黑色横条 高度10%
y1 = int(H * (1 - 0.10))
canvas.create_rectangle(5,y1,W-5,H-5,fill="#111111",outline="")


# 文字靠左摆放，和原排版对齐
font_text = ("Consolas",9)
#粉色区域文字，左对齐，增加左边距
canvas.create_text(
    int(W*0.35)+12, int(H*0.28),
    anchor="nw",
    text="""44‑55行
root.children["etc"].children["passwd"]
root.children["etc"].children["hostname"]
root.children["etc"].children["motd"]
root.children["bin"]
root.children["usr"].children["bin"]""",
    font=font_text,fill="#222222"
)

#底部白色区代码文字
canvas.create_text(
    15, int(H*0.66),
    anchor="nw",
    text="""build virtual directory tree
root = FSNode(is_dir=True)
root.children["etc"] = FSNode(is_dir=True)
root.children["etc"].children["passwd"] = FSNode(is_dir=False)""",
    font=font_text,fill="#222222"
)

root.mainloop()