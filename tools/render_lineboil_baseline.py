#!/usr/bin/env python3
"""MOVIC approved line-boil baseline v1 (2026-11-13).

Creates 30 individually displaced drawing cels, holds each for 6 frames,
keeps the paper/background fixed, and exports actual 4K H.264 MP4.
The line/color masks are tuned to the approved orange-and-black artwork.
Other scenes must be visually reviewed.
"""
import argparse
import json
import subprocess
from fractions import Fraction
from pathlib import Path
import cv2
import numpy as np

def render(input_path, output_path, test_size=None):
    img = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Input image not readable: {input_path}")
    if test_size:
        iw, ih = test_size
        img = cv2.resize(img, (iw, ih), interpolation=cv2.INTER_AREA)
    h,w=img.shape[:2]
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    orange=((hsv[:,:,0]>=4)&(hsv[:,:,0]<=24)&(hsv[:,:,1]>=18)&(hsv[:,:,2]>=90)).astype(np.uint8)*255
    dark=(gray<=145).astype(np.uint8)*255
    orange=cv2.medianBlur(orange,3)
    dark=cv2.medianBlur(dark,3)
    border=np.zeros((h,w),np.uint8)
    bw=max(3,int(round(h/170)))
    border[:bw,:]=255; border[-bw:,:]=255; border[:,:bw]=255; border[:,-bw:]=255
    border_dark=cv2.threshold(gray,185,255,cv2.THRESH_BINARY_INV)[1]
    dark=cv2.bitwise_or(dark,cv2.bitwise_and(border,border_dark))
    combined=cv2.bitwise_or(dark,orange)
    combined=cv2.dilate(combined,np.ones((3,3),np.uint8),1)
    fixed_bg=cv2.inpaint(img,combined,3,cv2.INPAINT_TELEA)
    alpha_dark=cv2.GaussianBlur(dark.astype(np.float32)/255.0,(0,0),0.8)
    alpha_orange=cv2.GaussianBlur(orange.astype(np.float32)/255.0,(0,0),0.8)
    dark_layer=img.copy(); dark_layer[dark==0]=0
    orange_layer=img.copy(); orange_layer[orange==0]=0
    Y,X=np.mgrid[0:h,0:w].astype(np.float32)
    rng=np.random.default_rng(2026111304)
    def random_field(cap_lo=1.9,cap_hi=2.8):
        gh=rng.integers(10,18); gw=rng.integers(15,28)
        fx=rng.normal(size=(gh,gw)).astype(np.float32)
        fy=rng.normal(size=(gh,gw)).astype(np.float32)
        fx=cv2.resize(fx,(w,h),interpolation=cv2.INTER_CUBIC)
        fy=cv2.resize(fy,(w,h),interpolation=cv2.INTER_CUBIC)
        sig=float(rng.uniform(14,30))
        fx=cv2.GaussianBlur(fx,(0,0),sig)
        fy=cv2.GaussianBlur(fy,(0,0),sig)
        fx/=max(1e-6,np.std(fx)); fy/=max(1e-6,np.std(fy))
        gx=float(rng.uniform(-0.7,0.7)); gy=float(rng.uniform(-0.7,0.7))
        amp=float(rng.uniform(0.8,1.35))
        dx=(fx*amp+gx).astype(np.float32)
        dy=(fy*amp+gy).astype(np.float32)
        mag=np.sqrt(dx*dx+dy*dy)
        cap=float(rng.uniform(cap_lo,cap_hi))
        scale=min(1.0,cap/max(1e-6,np.percentile(mag,99.4)))
        return dx*scale,dy*scale
    def alpha_variant(alpha):
        u=(alpha*255).astype(np.uint8)
        k=rng.choice([0,0,0,0,0,1,-1])
        if k>0: u=cv2.dilate(u,np.ones((2,2),np.uint8),1)
        elif k<0: u=cv2.erode(u,np.ones((2,2),np.uint8),1)
        sig=float(rng.uniform(0.72,0.88))
        a=cv2.GaussianBlur(u.astype(np.float32)/255.0,(0,0),sig)
        gain=float(rng.uniform(0.992,1.008))
        noise=rng.normal(0,0.003,size=alpha.shape).astype(np.float32)
        return np.clip(a*gain+noise*(a>0.08),0,1)
    def remap_layer(layer,dx,dy):
        mapx=(X+dx).astype(np.float32);mapy=(Y+dy).astype(np.float32)
        return cv2.remap(layer,mapx,mapy,interpolation=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0))
    def remap_alpha(alpha,dx,dy):
        mapx=(X+dx).astype(np.float32);mapy=(Y+dy).astype(np.float32)
        wa=cv2.remap(alpha.astype(np.float32),mapx,mapy,interpolation=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=0)
        return np.clip(wa,0,1)
    def composite(bg,layers):
        out=bg.astype(np.float32).copy()
        for lay,a in layers:
            aa=a[...,None];out=lay.astype(np.float32)*aa+out*(1-aa)
        return np.clip(out,0,255).astype(np.uint8)
    CELS=30;HOLD=6
    states=[]
    for i in range(CELS):
        dxo,dyo=random_field(1.8,2.6)
        dxd,dyd=random_field(2.1,2.9)
        sharedx,sharedy=random_field(1.8,2.4)
        dxd=0.55*dxd+0.45*sharedx
        dyd=0.55*dyd+0.45*sharedy
        dxo=0.55*dxo+0.45*sharedx
        dyo=0.55*dyo+0.45*sharedy
        ad=alpha_variant(alpha_dark);ao=alpha_variant(alpha_orange)
        layo=remap_layer(orange_layer,dxo,dyo)
        layd=remap_layer(dark_layer,dxd,dyd)
        wao=remap_alpha(ao,dxo,dyo)
        wad=remap_alpha(ad,dxd,dyd)
        states.append(composite(fixed_bg,[(layo,wao),(layd,wad)]))
    states[-1]=states[0].copy()
    
    width,height=(test_size if test_size else (3840,2160))
    # RGB24 native frames streamed through FFmpeg; no intermediate mp4v codec.
    command=["ffmpeg","-y","-hide_banner","-loglevel","error",
        "-f","rawvideo","-pixel_format","bgr24",
        "-video_size",f"{w}x{h}","-framerate","60","-i","pipe:0",
        "-vf",f"scale={width}:{height}:flags=lanczos",
        "-frames:v","180","-an","-c:v","libx264",
        "-preset","medium","-crf","16","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(output_path)]
    proc=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for cel in states:
            for _ in range(HOLD):
                proc.stdin.write(cel.tobytes())
        proc.stdin.close()
        err=proc.stderr.read()
        code=proc.wait()
        if code: raise RuntimeError(err.decode(errors="replace"))
    except Exception:
        if proc.poll() is None: proc.kill();proc.wait()
        output_path.unlink(missing_ok=True)
        raise
    probe=subprocess.run(["ffprobe","-v","error","-count_frames",
        "-select_streams","v:0","-show_entries",
        "stream=codec_name,width,height,avg_frame_rate,nb_read_frames,pix_fmt:format=duration",
        "-of","json",str(output_path)],check=True,capture_output=True,text=True)
    data=json.loads(probe.stdout)
    stream=data["streams"][0]
    assert stream["codec_name"]=="h264"
    assert (stream["width"],stream["height"])==(width,height)
    assert Fraction(stream["avg_frame_rate"])==60
    assert int(stream["nb_read_frames"])==180
    assert stream["pix_fmt"]=="yuv420p"
    assert abs(float(data["format"]["duration"])-3.0)<0.03
    return data

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("input",type=Path,help="Approved source PNG/JPEG")
    p.add_argument("--output",required=True,type=Path,help="Output MP4")
    p.add_argument("--test-size",help="Preview only, e.g. 640x360")
    args=p.parse_args()
    if not args.input.is_file(): p.error("Input image not found")
    if args.output.suffix.lower()!=".mp4": p.error("Output must be MP4")
    if args.output.exists(): p.error("Refusing to overwrite existing output")
    test_size=None
    if args.test_size:
        try: test_size=tuple(map(int,args.test_size.lower().split("x")))
        except ValueError: p.error("--test-size must be WIDTHxHEIGHT")
        if len(test_size)!=2 or min(test_size)<=0 or any(v%2 for v in test_size): p.error("Even positive dimensions required")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    result=render(args.input,args.output,test_size)
    print(json.dumps(result,ensure_ascii=False))
