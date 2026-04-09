"""Generate app icon for 등기부 OCR app"""
from PIL import Image, ImageDraw
import os

def make_icon(size=512):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = size // 10; r = size // 5
    draw.rounded_rectangle([pad, pad, size-pad, size-pad], radius=r, fill="#1A2744")
    doc_x, doc_y = size*0.22, size*0.15
    doc_w, doc_h  = size*0.56, size*0.70
    fold = size*0.14
    draw.polygon([(doc_x,doc_y),(doc_x+doc_w-fold,doc_y),(doc_x+doc_w,doc_y+fold),
                  (doc_x+doc_w,doc_y+doc_h),(doc_x,doc_y+doc_h)], fill="#F0EDE6")
    draw.polygon([(doc_x+doc_w-fold,doc_y),(doc_x+doc_w,doc_y+fold),
                  (doc_x+doc_w-fold,doc_y+fold)], fill="#C8C3B8")
    lx1,lx2 = doc_x+size*0.06, doc_x+doc_w-size*0.06
    for i,frac in enumerate([0.38,0.48,0.58,0.68,0.78]):
        y = doc_y+doc_h*frac
        draw.line([(lx1,y),(lx2,y)], fill="#1A2744", width=3 if i==0 else 2)
    vx = doc_x+doc_w*0.38
    draw.line([(vx,doc_y+doc_h*0.35),(vx,doc_y+doc_h*0.85)], fill="#1A2744", width=2)
    arr_cx,arr_cy = size*0.72,size*0.72; arr_r=size*0.14
    draw.ellipse([arr_cx-arr_r,arr_cy-arr_r,arr_cx+arr_r,arr_cy+arr_r], fill="#217346")
    ax,ay = arr_cx-arr_r*0.35,arr_cy
    draw.line([(ax,ay),(ax+arr_r*0.65,ay)], fill="white", width=max(3,size//80))
    hw=arr_r*0.28
    draw.polygon([(ax+arr_r*0.55,ay-hw*0.7),(ax+arr_r*0.55+hw,ay),(ax+arr_r*0.55,ay+hw*0.7)], fill="white")
    return img

def save_icon(path="icon.png"):
    make_icon(512).save(path,"PNG")
    print(f"Icon saved: {path}")
    return path

if __name__ == "__main__":
    save_icon()
