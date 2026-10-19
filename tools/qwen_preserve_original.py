#!/usr/bin/env python3
"""Preserve original source pixels while applying localized Qwen editing.

Modes:
  recolor: conservative white -> safety-yellow recolor inside an explicit polygon
  patch: paste a real Qwen-generated ROI crop only within the explicit polygon
No change is made outside the mask; no faces are regenerated.
"""
import argparse, base64, io, json
from pathlib import Path
import cv2, numpy as np
from PIL import Image, ImageOps

def open_source(path):
    p=Path(path)
    if p.name.endswith(".b64"):
        b=base64.b64decode("".join(p.read_text().split()),validate=True)
        im=Image.open(io.BytesIO(b))
    else:
        im=Image.open(p)
    return ImageOps.exif_transpose(im).convert("RGB")

def mask_for(size,polygon,feather):
    w,h=size
    pts=np.asarray(polygon,dtype=np.float32)
    if pts.ndim!=2 or pts.shape[1]!=2 or len(pts)<3:
        raise ValueError("polygon must have 3+ XY points")
    if not np.isfinite(pts).all() or (pts[:,0]<0).any() or (pts[:,0]>w).any() or (pts[:,1]<0).any() or (pts[:,1]>h).any():
        raise ValueError("polygon outside original dimensions")
    mask=np.zeros((h,w),dtype=np.uint8)
    cv2.fillPoly(mask,[np.round(pts).astype(np.int32)],255)
    if feather>0:
        kernel=(int(feather*4)|1)
        mask=cv2.GaussianBlur(mask,(kernel,kernel),feather)
    return mask.astype(np.float32)/255

def composite(src, config, qwen=None):
    arr=np.asarray(src,dtype=np.uint8)
    roi=mask_for(src.size,config["polygon"],float(config.get("feather",1.5)))
    if config["mode"]=="recolor":
        hsv=cv2.cvtColor(arr,cv2.COLOR_RGB2HSV)
        v=hsv[...,2].astype(np.float32)
        s=hsv[...,1].astype(np.float32)
        white=np.clip((v-float(config.get("white_value_min",126)))/65.,0,1)
        desat=1-np.clip((s-float(config.get("max_saturation",65)))/38.,0,1)
        alpha=roi*white*desat
        yellow=hsv.copy()
        yellow[...,0]=int(config.get("yellow_hue_cv",23))
        yellow[...,1]=np.maximum(hsv[...,1],int(config.get("yellow_saturation_cv",218))).astype(np.uint8)
        replacement=cv2.cvtColor(yellow,cv2.COLOR_HSV2RGB)
        result=np.rint(arr.astype(np.float32)*(1-alpha[...,None])+replacement.astype(np.float32)*alpha[...,None]).clip(0,255).astype(np.uint8)
    elif config["mode"]=="patch":
        if qwen is None:raise ValueError("Qwen edited crop must be supplied for patch mode")
        x0,y0,x1,y1=map(int,config["crop_box"])
        if not (0<=x0<x1<=src.width and 0<=y0<y1<=src.height):raise ValueError("crop_box outside source")
        replacement=np.asarray(qwen.resize((x1-x0,y1-y0),Image.Resampling.LANCZOS),dtype=np.uint8)
        alpha=roi[y0:y1,x0:x1]
        result=arr.copy()
        base=result[y0:y1,x0:x1].astype(np.float32)
        result[y0:y1,x0:x1]=np.rint(base*(1-alpha[...,None])+replacement.astype(np.float32)*alpha[...,None]).clip(0,255).astype(np.uint8)
    else: raise ValueError("Unsupported mode: "+str(config["mode"]))
    # Zero-difference guard: outside selected polygon means exactly original pixels.
    if not np.array_equal(arr[roi==0],result[roi==0]):
        raise AssertionError("Original pixels outside edit region changed")
    if src.size != (result.shape[1],result.shape[0]):
        raise AssertionError("Unexpected output resolution")
    return Image.fromarray(result,"RGB"),int(np.count_nonzero(roi))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--config",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--qwen-crop")
    args=p.parse_args()
    src=open_source(args.source)
    cfg=json.loads(Path(args.config).read_text(encoding="utf-8"))
    crop=open_source(args.qwen_crop) if args.qwen_crop else None
    result,mask_pixels=composite(src,cfg,crop)
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    result.save(out,format="PNG",optimize=True)
    print(json.dumps({"status":"SUCCEEDED","mode":cfg["mode"],"source_size":list(src.size),
                      "output_size":list(result.size),"mask_pixels":mask_pixels},ensure_ascii=False))

if __name__=="__main__":main()
