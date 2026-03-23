"""
Food Adulteration Detection - Real-Photo Compatible Model v3
============================================================
Key fix: Uses HSV colour analysis + centre-crop to work with real photos.
Ignores backgrounds, containers, lighting by focusing on colour signature.
"""

import numpy as np
import os, pickle, random
from PIL import Image, ImageFilter, ImageEnhance

IMG_SIZE  = 128
CROP_FRAC = 0.6
SAMPLES   = 600

CLASSES = [
    "pure_turmeric","adulterated_turmeric",
    "pure_chilli","adulterated_chilli",
    "pure_milk","adulterated_milk",
    "pure_honey","adulterated_honey",
    "pure_sugar","adulterated_sugar",
    "pure_coriander","adulterated_coriander",
    "non_food",
]
CLASS_INDEX = {c:i for i,c in enumerate(CLASSES)}

def rn(lo,hi): return random.uniform(lo,hi)

def add_realism(img, bv=0.25, bp=0.3):
    pil = Image.fromarray(img)
    pil = ImageEnhance.Brightness(pil).enhance(rn(1-bv,1+bv))
    pil = ImageEnhance.Contrast(pil).enhance(rn(0.85,1.2))
    pil = ImageEnhance.Color(pil).enhance(rn(0.8,1.3))
    if random.random()<bp: pil=pil.filter(ImageFilter.GaussianBlur(rn(0.3,1.0)))
    arr = np.array(pil)
    noise=(np.random.randn(*arr.shape)*rn(2,8)).astype(np.int16)
    return np.clip(arr.astype(np.int16)+noise,0,255).astype(np.uint8)

def powder(base, ns=18, ng=120, gv=30):
    img=np.clip(np.full((IMG_SIZE,IMG_SIZE,3),base,np.float32)+np.random.randn(IMG_SIZE,IMG_SIZE,3)*ns,0,255).astype(np.uint8)
    for _ in range(ng):
        x,y=random.randint(0,IMG_SIZE-5),random.randint(0,IMG_SIZE-5); r=random.randint(1,4)
        img[y:y+r,x:x+r]=np.clip(np.array(base)+np.random.randn(3)*gv,0,255).astype(np.uint8)
    return add_realism(img)

def liquid(base, sc=6, ns=5):
    img=np.clip(np.full((IMG_SIZE,IMG_SIZE,3),base,np.float32)+np.random.randn(IMG_SIZE,IMG_SIZE,3)*ns,0,255).astype(np.uint8)
    for _ in range(sc):
        x=random.randint(5,IMG_SIZE-5)
        img[:,x:x+random.randint(1,3)]=np.clip(np.array(base,np.float32)*rn(1.05,1.15),0,255).astype(np.uint8)
    return add_realism(img,bv=0.15,bp=0.5)

# ── generators ──────────────────────────────────────────────

def generate_pure_turmeric(n=SAMPLES):
    return np.array([powder([int(rn(185,215)),int(rn(120,155)),int(rn(5,25))],ns=16,gv=25) for _ in range(n)])

def generate_adulterated_turmeric(n=SAMPLES):
    imgs=[]
    for _ in range(n):
        img=powder([int(rn(205,230)),int(rn(175,205)),int(rn(70,110))],ns=12,gv=20)
        for _ in range(random.randint(5,15)):
            px,py=random.randint(0,IMG_SIZE-12),random.randint(0,IMG_SIZE-12); pw,ph=random.randint(4,12),random.randint(4,12)
            img[py:py+ph,px:px+pw]=np.clip(np.full((ph,pw,3),[230,228,215])+np.random.randn(ph,pw,3)*8,0,255).astype(np.uint8)
        imgs.append(img)
    return np.array(imgs)

def generate_pure_chilli(n=SAMPLES):
    return np.array([powder([int(rn(195,225)),int(rn(20,55)),int(rn(10,35))],ns=18,gv=28) for _ in range(n)])

def generate_adulterated_chilli(n=SAMPLES):
    imgs=[]
    for _ in range(n):
        img=powder([int(rn(150,180)),int(rn(55,85)),int(rn(20,45))],ns=15,gv=22)
        for _ in range(random.randint(8,18)):
            px,py=random.randint(0,IMG_SIZE-10),random.randint(0,IMG_SIZE-10); pw,ph=random.randint(3,10),random.randint(3,10)
            img[py:py+ph,px:px+pw]=np.clip(np.full((ph,pw,3),[int(rn(110,145)),int(rn(45,70)),int(rn(15,35))])+np.random.randn(ph,pw,3)*12,0,255).astype(np.uint8)
        imgs.append(img)
    return np.array(imgs)

def generate_pure_milk(n=SAMPLES):
    imgs=[]
    for _ in range(n):
        v=int(rn(238,252)); imgs.append(liquid([min(v+3,255),v,max(v-4,0)],sc=random.randint(3,8),ns=4))
    return np.array(imgs)

def generate_adulterated_milk(n=SAMPLES):
    imgs=[]
    for _ in range(n):
        v=int(rn(220,240)); imgs.append(liquid([max(v-8,0),v,min(v+8,255)],sc=random.randint(5,12),ns=3))
    return np.array(imgs)

def generate_pure_honey(n=SAMPLES):
    return np.array([liquid([int(rn(200,230)),int(rn(120,155)),int(rn(5,25))],sc=random.randint(2,6),ns=6) for _ in range(n)])

def generate_adulterated_honey(n=SAMPLES):
    return np.array([liquid([int(rn(230,248)),int(rn(185,215)),int(rn(70,110))],sc=random.randint(4,9),ns=4) for _ in range(n)])

def generate_pure_sugar(n=SAMPLES):
    imgs=[]
    for _ in range(n):
        v=int(rn(248,255)); img=powder([v,v,v],ns=5,ng=80,gv=8)
        for _ in range(random.randint(20,50)):
            px,py=random.randint(0,IMG_SIZE-3),random.randint(0,IMG_SIZE-3); img[py:py+2,px:px+2]=255
        imgs.append(img)
    return np.array(imgs)

def generate_adulterated_sugar(n=SAMPLES):
    imgs=[]
    for _ in range(n):
        v=int(rn(225,242)); img=powder([min(v+2,255),v,max(v-5,0)],ns=8,ng=60,gv=12)
        for _ in range(random.randint(4,10)):
            px,py=random.randint(0,IMG_SIZE-10),random.randint(0,IMG_SIZE-10); pw,ph=random.randint(4,10),random.randint(4,10)
            img[py:py+ph,px:px+pw]=np.clip(np.full((ph,pw,3),[int(rn(200,220)),int(rn(198,218)),int(rn(195,215))])+np.random.randn(ph,pw,3)*8,0,255).astype(np.uint8)
        imgs.append(img)
    return np.array(imgs)

def generate_pure_coriander(n=SAMPLES):
    return np.array([powder([int(rn(125,160)),int(rn(105,135)),int(rn(40,65))],ns=14,gv=20) for _ in range(n)])

def generate_adulterated_coriander(n=SAMPLES):
    imgs=[]
    for _ in range(n):
        img=powder([int(rn(95,130)),int(rn(65,95)),int(rn(20,45))],ns=16,gv=22)
        for _ in range(random.randint(10,20)):
            px,py=random.randint(0,IMG_SIZE-6),random.randint(0,IMG_SIZE-6); pw,ph=random.randint(1,5),random.randint(1,3)
            img[py:py+ph,px:px+pw]=np.clip(np.full((ph,pw,3),[int(rn(50,80)),int(rn(35,60)),int(rn(10,28))])+np.random.randn(ph,pw,3)*8,0,255).astype(np.uint8)
        imgs.append(img)
    return np.array(imgs)

def generate_non_food(n=SAMPLES):
    imgs=[]
    for _ in range(n):
        c=random.randint(0,7)
        if c==0:
            r2,g2,b2=random.randint(0,255),random.randint(0,255),random.randint(0,255)
            img=np.clip(np.full((IMG_SIZE,IMG_SIZE,3),[r2,g2,b2],np.float32)+np.random.randn(IMG_SIZE,IMG_SIZE,3)*25,0,255).astype(np.uint8)
        elif c==1:
            img=np.zeros((IMG_SIZE,IMG_SIZE,3),np.uint8)
            for i in range(IMG_SIZE): img[i,:]=[int(i*255/IMG_SIZE),random.randint(80,180),random.randint(80,220)]
        elif c==2:
            img=np.clip(np.full((IMG_SIZE,IMG_SIZE,3),[int(rn(90,130)),int(rn(65,100)),int(rn(30,60))],np.float32)+np.random.randn(IMG_SIZE,IMG_SIZE,3)*15,0,255).astype(np.uint8)
        elif c==3:
            img=np.clip(np.full((IMG_SIZE,IMG_SIZE,3),[int(rn(30,80)),int(rn(100,180)),int(rn(20,60))],np.float32)+np.random.randn(IMG_SIZE,IMG_SIZE,3)*20,0,255).astype(np.uint8)
        elif c==4:
            r2,g2,b2=int(rn(180,230)),int(rn(130,180)),int(rn(90,140))
            img=np.clip(np.full((IMG_SIZE,IMG_SIZE,3),[r2,g2,b2],np.float32)+np.random.randn(IMG_SIZE,IMG_SIZE,3)*18,0,255).astype(np.uint8)
        elif c==5:
            img=np.clip(np.full((IMG_SIZE,IMG_SIZE,3),[int(rn(30,80)),int(rn(80,150)),int(rn(160,230))],np.float32)+np.random.randn(IMG_SIZE,IMG_SIZE,3)*20,0,255).astype(np.uint8)
        elif c==6:
            img=np.zeros((IMG_SIZE,IMG_SIZE,3),np.uint8); sz=random.randint(4,12)
            for yy in range(0,IMG_SIZE,sz):
                for xx in range(0,IMG_SIZE,sz):
                    img[yy:yy+sz,xx:xx+sz]=220 if((xx//sz+yy//sz)%2==0) else 35
        else:
            img=np.clip(np.full((IMG_SIZE,IMG_SIZE,3),[128,128,128],np.float32)+np.random.randn(IMG_SIZE,IMG_SIZE,3)*50,0,255).astype(np.uint8)
        imgs.append(add_realism(img,bv=0.2,bp=0.2))
    return np.array(imgs)

# ── feature extraction ────────────────────────────────────────

def centre_crop(img, frac=CROP_FRAC):
    h,w=img.shape[:2]; ch,cw=int(h*frac),int(w*frac)
    y0,x0=(h-ch)//2,(w-cw)//2
    return img[y0:y0+ch,x0:x0+cw]

def rgb_to_hsv(img_f):
    r,g,b=img_f[:,:,0],img_f[:,:,1],img_f[:,:,2]
    Cmax=np.maximum(np.maximum(r,g),b); Cmin=np.minimum(np.minimum(r,g),b); d=Cmax-Cmin+1e-8
    V=Cmax; S=np.where(Cmax>0,d/(Cmax+1e-8),0.0)
    H=np.zeros_like(r)
    mr=(Cmax==r); mg=(Cmax==g)&~mr; mb=~mr&~mg
    H[mr]=(60*((g[mr]-b[mr])/d[mr]))%360
    H[mg]=(60*((b[mg]-r[mg])/d[mg])+120)%360
    H[mb]=(60*((r[mb]-g[mb])/d[mb])+240)%360
    return H,S,V

def extract_features(img_array):
    features=[]
    for img in img_array:
        crop=centre_crop(img); img_f=crop.astype(np.float32)/255.0
        r,g,b=img_f[:,:,0],img_f[:,:,1],img_f[:,:,2]
        H,S,V=rgb_to_hsv(img_f); feat=[]

        # RGB stats (6)
        for ch in [r,g,b]: feat+=[ch.mean(),ch.std()]
        # HSV stats (6)
        feat+=[H.mean(),H.std(),S.mean(),S.std(),V.mean(),V.std()]
        # HSV percentiles (9)
        for arr in [H,S,V]: feat+=[float(np.percentile(arr,25)),float(np.percentile(arr,50)),float(np.percentile(arr,75))]
        # RGB ratios (3)
        feat+=[r.mean()/(g.mean()+1e-6),r.mean()/(b.mean()+1e-6),g.mean()/(b.mean()+1e-6)]
        # Colour histograms 16 bins (48)
        for ch in [r,g,b]:
            h2,_=np.histogram(ch,bins=16,range=(0,1)); feat+=(h2/h2.sum()).tolist()
        # Hue histogram 12 bins (12)
        hh,_=np.histogram(H,bins=12,range=(0,360)); feat+=(hh/(hh.sum()+1e-8)).tolist()
        # Texture (2)
        gx=np.gradient(img_f[:,:,0],axis=1); gy=np.gradient(img_f[:,:,0],axis=0)
        feat+=[np.sqrt(gx**2+gy**2).mean(),np.sqrt(gx**2+gy**2).std()]
        # Food colour masks (12)
        feat.append(((H>=15)&(H<=40)&(S>0.55)&(V>0.55)).mean())   # deep yellow (turmeric)
        feat.append(((H>=25)&(H<=55)&(S<0.45)&(V>0.75)).mean())   # pale yellow (chalk)
        feat.append(((H<=15)&(S>0.60)&(V>0.50)).mean())            # vivid red (chilli)
        feat.append(((H>=12)&(H<=30)&(S>0.35)&(S<0.75)&(V<0.70)).mean()) # brownish (brick)
        feat.append((S<0.08).mean())                                # near-white
        feat.append(((H>=180)&(H<=260)&(S<0.15)&(V>0.80)).mean()) # blue-white (watered milk)
        feat.append(((H>=20)&(H<=45)&(S>0.70)&(V>0.65)).mean())   # deep amber (honey)
        feat.append(((H>=30)&(H<=55)&(S<0.55)&(V>0.85)).mean())   # pale amber (adulterated honey)
        feat.append(((H>=50)&(H<=100)&(S>0.20)&(V>0.30)&(V<0.75)).mean()) # olive-green (coriander)
        feat.append(((H>=15)&(H<=45)&(S>0.30)&(V<0.45)).mean())   # dark brown (adulterated coriander)
        feat.append((V>0.97).mean())                                # sparkle (pure sugar)
        feat.append((V<0.12).mean())                                # very dark (non-food)
        # Saturation zones (3)
        feat+=[(S<0.1).mean(),((S>=0.1)&(S<0.5)).mean(),(S>=0.5).mean()]
        # Value zones (3)
        feat+=[(V<0.3).mean(),((V>=0.3)&(V<0.7)).mean(),(V>=0.7).mean()]
        features.append(feat)
    return np.array(features,dtype=np.float32)

# ── train ─────────────────────────────────────────────────────

def train():
    print("Generating realistic synthetic dataset (13 classes)...")
    generators=[
        generate_pure_turmeric,generate_adulterated_turmeric,
        generate_pure_chilli,generate_adulterated_chilli,
        generate_pure_milk,generate_adulterated_milk,
        generate_pure_honey,generate_adulterated_honey,
        generate_pure_sugar,generate_adulterated_sugar,
        generate_pure_coriander,generate_adulterated_coriander,
        generate_non_food,
    ]
    X_imgs,y=[],[]
    for label,gen in enumerate(generators):
        imgs=gen(SAMPLES); X_imgs.append(imgs); y+=[label]*SAMPLES
        print(f"  [{label:02d}] {CLASSES[label]}: {SAMPLES} samples")
    X_imgs=np.concatenate(X_imgs,axis=0); y=np.array(y)
    print(f"\nTotal: {len(X_imgs)} images")
    print("Extracting HSV + colour features...")
    X=extract_features(X_imgs)
    idx=np.random.permutation(len(X)); X,y=X[idx],y[idx]
    split=int(0.85*len(X)); X_train,X_test=X[:split],X[split:]; y_train,y_test=y[:split],y[split:]
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import classification_report,accuracy_score
    print("Training model...")
    model=Pipeline([
        ('scaler',StandardScaler()),
        ('clf',RandomForestClassifier(n_estimators=500,max_depth=None,min_samples_split=2,random_state=42,n_jobs=-1,class_weight='balanced'))
    ])
    model.fit(X_train,y_train)
    y_pred=model.predict(X_test); acc=accuracy_score(y_test,y_pred)
    print(f"\nTest Accuracy: {acc*100:.2f}%")
    print(classification_report(y_test,y_pred,target_names=CLASSES))
    model_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'food_model.pkl')
    with open(model_path,'wb') as f:
        pickle.dump({'model':model,'classes':CLASSES,'class_index':CLASS_INDEX,'img_size':IMG_SIZE,'crop_frac':CROP_FRAC,'accuracy':acc,'version':'v3_real_photo'},f)
    print(f"Model saved: {model_path}")
    return model_path,acc

if __name__=='__main__':
    np.random.seed(42); random.seed(42); train()