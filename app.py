"""
Food Adulteration Detection - Flask Backend (v2 Enhanced)
New: Admin panel, PDF reports, CSV export, user stats, profile management,
     contact messages stored in DB, rate limiting, image save.
"""

import os, json, hashlib, pickle, datetime, base64, io, csv, re, secrets
from io import BytesIO

import numpy as np
from PIL import Image
import sqlite3

from flask import (Flask, request, jsonify, send_from_directory,
                   session, make_response, send_file)

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR  = os.path.join(BASE_DIR, 'uploads')
DB_PATH     = os.path.join(BASE_DIR, 'instance', 'app.db')
MODEL_PATH  = os.path.join(BASE_DIR, 'model', 'food_model.pkl')
IMG_SIZE    = 128
ADMIN_PASS_HASH = hashlib.sha256(b'admin123').hexdigest()

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

app = Flask(__name__, static_folder='static')
app.secret_key = 'foodpure_v2_secret_2024_abc_xyz'

with open(MODEL_PATH, 'rb') as f:
    model_data = pickle.load(f)

ML_MODEL = model_data['model']
CLASSES  = model_data['classes']

LABEL_INFO = {
    "pure_turmeric": {
        "display": "Pure Turmeric", "status": "PURE", "icon": "✅", "color": "#2ecc71",
        "short": "Genuine turmeric powder. Deep yellow with uniform texture.",
        "desc": "The turmeric powder appears genuine. Color distribution is consistent with authentic deep yellow pigment. No white or pale patches detected. Granular texture is uniform.",
        "tips": "Store in airtight container away from sunlight."
    },
    "adulterated_turmeric": {
        "display": "Adulterated Turmeric", "status": "ADULTERATED", "icon": "⚠️", "color": "#e74c3c",
        "short": "Chalk powder detected — pale patches visible.",
        "desc": "Chalk powder adulteration detected. White and pale patches are visible across the sample. The yellow saturation is lower than expected for pure turmeric. Color distribution is non-uniform.",
        "tips": "Do not consume. Report to FSSAI helpline: 1800-112-100."
    },
    "pure_chilli": {
        "display": "Pure Chilli Powder", "status": "PURE", "icon": "✅", "color": "#2ecc71",
        "short": "Genuine chilli powder. Vibrant red, uniform texture.",
        "desc": "The chilli powder appears genuine. Red channel intensity is high and consistent. Particle distribution is fine and uniform with no brownish clusters detected.",
        "tips": "Store in a cool dry place. Check expiry date."
    },
    "adulterated_chilli": {
        "display": "Adulterated Chilli Powder", "status": "ADULTERATED", "icon": "⚠️", "color": "#e74c3c",
        "short": "Brick powder detected — brownish clusters present.",
        "desc": "Brick powder adulteration detected. Brownish-red clusters inconsistent with chilli pigment are visible. The overall color is duller and less vibrant. Texture shows coarse irregular particles.",
        "tips": "Do not consume. Report to FSSAI helpline: 1800-112-100."
    },
    "pure_milk": {
        "display": "Pure Milk", "status": "PURE", "icon": "✅", "color": "#2ecc71",
        "short": "Genuine milk. Creamy white, uniform opacity.",
        "desc": "The milk sample appears pure. Brightness is uniformly high with a warm creamy white tone. No blue tinge or transparency streaks detected. Light refraction is consistent with full-fat milk.",
        "tips": "Keep refrigerated and consume before expiry."
    },
    "adulterated_milk": {
        "display": "Adulterated Milk (Water)", "status": "ADULTERATED", "icon": "⚠️", "color": "#e74c3c",
        "short": "Water dilution detected — bluish tint, reduced opacity.",
        "desc": "Water adulteration detected. The sample exhibits a bluish tint and reduced opacity. Vertical transparency streaks detected in the light refraction pattern, characteristic of diluted milk.",
        "tips": "Do not consume. Report to FSSAI helpline: 1800-112-100."
    },
    "pure_honey": {
        "display": "Pure Honey", "status": "PURE", "icon": "✅", "color": "#2ecc71",
        "short": "Genuine honey. Deep amber colour, thick consistency.",
        "desc": "The honey sample appears genuine. Deep amber hue with high saturation is consistent with natural honey. Colour distribution is uniform with characteristic golden-orange tones.",
        "tips": "Store at room temperature in a sealed jar. Natural crystallisation is normal."
    },
    "adulterated_honey": {
        "display": "Adulterated Honey", "status": "ADULTERATED", "icon": "⚠️", "color": "#e74c3c",
        "short": "Sugar syrup detected — pale colour, low saturation.",
        "desc": "Sugar syrup adulteration detected. The sample is paler and less saturated than genuine honey. The amber hue is washed out, indicating dilution with sugar syrup or artificial sweeteners.",
        "tips": "Do not consume. Report to FSSAI helpline: 1800-112-100."
    },
    "pure_sugar": {
        "display": "Pure Sugar", "status": "PURE", "icon": "✅", "color": "#2ecc71",
        "short": "Genuine sugar. Bright white, crystalline texture.",
        "desc": "The sugar sample appears pure. Brightness is at maximum levels consistent with refined white sugar crystals. Sparkle highlights from crystal facets are detected. No grey or off-white patches present.",
        "tips": "Store in an airtight container away from moisture."
    },
    "adulterated_sugar": {
        "display": "Adulterated Sugar", "status": "ADULTERATED", "icon": "⚠️", "color": "#e74c3c",
        "short": "Chalk or starch detected — off-white, dull appearance.",
        "desc": "Adulteration detected in sugar sample. The sample shows an off-white or slightly grey tone instead of pure bright white. Dull patches indicate chalk powder or starch adulteration reducing crystal clarity.",
        "tips": "Do not consume. Report to FSSAI helpline: 1800-112-100."
    },
    "pure_coriander": {
        "display": "Pure Coriander Powder", "status": "PURE", "icon": "✅", "color": "#2ecc71",
        "short": "Genuine coriander powder. Olive-green, uniform texture.",
        "desc": "The coriander powder appears genuine. Characteristic olive-green to khaki hue is consistent with pure dried coriander. Colour saturation and brightness are within expected ranges.",
        "tips": "Store in an airtight container away from heat and light."
    },
    "adulterated_coriander": {
        "display": "Adulterated Coriander Powder", "status": "ADULTERATED", "icon": "⚠️", "color": "#e74c3c",
        "short": "Sawdust or dried stems detected — dark, dull colour.",
        "desc": "Adulteration detected in coriander powder. The sample appears darker and duller than genuine coriander. Dark brownish patches and reduced green hue indicate sawdust, dried stems, or other foreign matter.",
        "tips": "Do not consume. Report to FSSAI helpline: 1800-112-100."
    },
    "non_food": {
        "display": "Non-Food Image", "status": "INVALID", "icon": "❌", "color": "#f39c12",
        "short": "Not a recognizable food sample image.",
        "desc": "This image does not appear to be a food sample. Please upload a clear, well-lit image of turmeric, chilli powder, milk, honey, sugar, or coriander powder.",
        "tips": "Try again with a clearer close-up image of the food placed on a white or neutral background."
    }
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            food_type TEXT, result TEXT, status TEXT,
            confidence REAL, image_name TEXT, image_b64 TEXT,
            created TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, email TEXT, message TEXT,
            resolved INTEGER DEFAULT 0,
            created TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS rate_limit (
            user_id INTEGER, window TEXT, count INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, window)
        );
        """)
        try:
            conn.execute("INSERT INTO users (username,email,password,role) VALUES (?,?,?,?)",
                         ('admin','admin@foodpure.local', ADMIN_PASS_HASH, 'admin'))
        except sqlite3.IntegrityError:
            pass
    print("DB ready:", DB_PATH)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def check_rate(user_id):
    window = datetime.datetime.utcnow().strftime('%Y-%m-%d-%H')
    with get_db() as conn:
        row = conn.execute("SELECT count FROM rate_limit WHERE user_id=? AND window=?", (user_id, window)).fetchone()
        count = row['count'] if row else 0
        if count >= 30: return False
        if row: conn.execute("UPDATE rate_limit SET count=count+1 WHERE user_id=? AND window=?", (user_id, window))
        else:   conn.execute("INSERT INTO rate_limit (user_id,window,count) VALUES (?,?,1)", (user_id, window))
    return True

CROP_FRAC = 0.6

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
        for ch in [r,g,b]: feat+=[ch.mean(),ch.std()]
        feat+=[H.mean(),H.std(),S.mean(),S.std(),V.mean(),V.std()]
        for arr in [H,S,V]: feat+=[float(np.percentile(arr,25)),float(np.percentile(arr,50)),float(np.percentile(arr,75))]
        feat+=[r.mean()/(g.mean()+1e-6),r.mean()/(b.mean()+1e-6),g.mean()/(b.mean()+1e-6)]
        for ch in [r,g,b]:
            h2,_=np.histogram(ch,bins=16,range=(0,1)); feat+=(h2/h2.sum()).tolist()
        hh,_=np.histogram(H,bins=12,range=(0,360)); feat+=(hh/(hh.sum()+1e-8)).tolist()
        gx=np.gradient(img_f[:,:,0],axis=1); gy=np.gradient(img_f[:,:,0],axis=0)
        feat+=[np.sqrt(gx**2+gy**2).mean(),np.sqrt(gx**2+gy**2).std()]
        feat.append(((H>=15)&(H<=40)&(S>0.55)&(V>0.55)).mean())
        feat.append(((H>=25)&(H<=55)&(S<0.45)&(V>0.75)).mean())
        feat.append(((H<=15)&(S>0.60)&(V>0.50)).mean())
        feat.append(((H>=12)&(H<=30)&(S>0.35)&(S<0.75)&(V<0.70)).mean())
        feat.append((S<0.08).mean())
        feat.append(((H>=180)&(H<=260)&(S<0.15)&(V>0.80)).mean())
        feat.append(((H>=20)&(H<=45)&(S>0.70)&(V>0.65)).mean())
        feat.append(((H>=30)&(H<=55)&(S<0.55)&(V>0.85)).mean())
        feat.append(((H>=50)&(H<=100)&(S>0.20)&(V>0.30)&(V<0.75)).mean())
        feat.append(((H>=15)&(H<=45)&(S>0.30)&(V<0.45)).mean())
        feat.append((V>0.97).mean())
        feat.append((V<0.12).mean())
        feat+=[(S<0.1).mean(),((S>=0.1)&(S<0.5)).mean(),(S>=0.5).mean()]
        feat+=[(V<0.3).mean(),((V>=0.3)&(V<0.7)).mean(),(V>=0.7).mean()]
        features.append(feat)
    return np.array(features,dtype=np.float32)

def preprocess_image(pil_img):
    # Convert and resize to 128px (matches new training)
    img = pil_img.convert('RGB')
    # Auto-enhance: stretch contrast so real photos have full dynamic range
    from PIL import ImageEnhance, ImageFilter
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Color(img).enhance(1.10)
    img = img.resize((128, 128), Image.LANCZOS)
    return np.array(img, dtype=np.uint8)

def rule_based_predict(arr):
    """
    Colour-rule classifier that works directly on real photos.
    Returns (label, confidence) based on HSV analysis of the centre crop.
    This is used to OVERRIDE the ML model when the ML model says non_food
    but colour rules strongly suggest a food type.
    """
    crop  = centre_crop(arr, frac=0.5)
    img_f = crop.astype(np.float32) / 255.0
    H, S, V = rgb_to_hsv(img_f)

    # Compute colour zone percentages
    deep_yellow   = ((H>=10)&(H<=42)&(S>0.40)&(V>0.45)).mean()   # turmeric
    pale_yellow   = ((H>=25)&(H<=60)&(S<0.50)&(V>0.70)).mean()   # chalk/adulterated turmeric
    vivid_red     = ((H<=18)&(S>0.50)&(V>0.40)).mean()            # chilli
    brown_red     = ((H>=10)&(H<=32)&(S>0.25)&(V<0.72)).mean()   # brick/adulterated chilli
    near_white    = (S<0.12).mean()                                 # milk/sugar
    blue_white    = ((H>=185)&(H<=270)&(S<0.18)&(V>0.78)).mean() # watered milk
    warm_white    = ((H<=40)&(S<0.12)&(V>0.88)).mean()            # pure milk/sugar
    deep_amber    = ((H>=18)&(H<=48)&(S>0.55)&(V>0.55)).mean()   # honey
    pale_amber    = ((H>=28)&(H<=60)&(S<0.50)&(V>0.82)).mean()   # adulterated honey
    olive_green   = ((H>=48)&(H<=105)&(S>0.15)&(V>0.25)&(V<0.80)).mean()  # coriander
    dark_brown    = ((H>=12)&(H<=50)&(S>0.20)&(V<0.48)).mean()   # adulterated coriander
    bright_white  = (V>0.94).mean()                                # pure sugar crystals

    mean_S = float(S.mean())
    mean_V = float(V.mean())
    mean_H = float(H.mean())

    scores = {}

    # ── TURMERIC ──
    if deep_yellow > 0.25:
        scores['pure_turmeric']        = min(0.92, 0.55 + deep_yellow * 1.2)
    if pale_yellow > 0.20 and deep_yellow < 0.35:
        scores['adulterated_turmeric'] = min(0.88, 0.50 + pale_yellow * 1.0)

    # ── CHILLI ──
    if vivid_red > 0.20:
        scores['pure_chilli']          = min(0.92, 0.55 + vivid_red * 1.4)
    if brown_red > 0.15 and vivid_red < 0.30:
        scores['adulterated_chilli']   = min(0.88, 0.50 + brown_red * 1.1)

    # ── MILK ──
    if near_white > 0.60 and mean_V > 0.82:
        if blue_white > 0.05:
            scores['adulterated_milk'] = min(0.88, 0.55 + blue_white * 3.0)
        else:
            scores['pure_milk']        = min(0.92, 0.55 + warm_white * 1.5)

    # ── HONEY ──
    if deep_amber > 0.20 and mean_S > 0.35:
        scores['pure_honey']           = min(0.90, 0.52 + deep_amber * 1.3)
    if pale_amber > 0.18 and mean_S < 0.50:
        scores['adulterated_honey']    = min(0.86, 0.50 + pale_amber * 1.1)

    # ── SUGAR ──
    if near_white > 0.75 and bright_white > 0.30:
        scores['pure_sugar']           = min(0.90, 0.55 + bright_white * 1.2)
    if near_white > 0.55 and bright_white < 0.25 and mean_S < 0.12:
        scores['adulterated_sugar']    = min(0.82, 0.50 + (near_white - bright_white))

    # ── CORIANDER ──
    if olive_green > 0.15:
        scores['pure_coriander']       = min(0.90, 0.52 + olive_green * 1.5)
    if dark_brown > 0.15 and olive_green < 0.20:
        scores['adulterated_coriander']= min(0.86, 0.50 + dark_brown * 1.1)

    if not scores:
        return None, 0.0

    best_label = max(scores, key=scores.get)
    return best_label, scores[best_label]

def predict(pil_img):
    arr   = preprocess_image(pil_img)
    feat  = extract_features([arr])
    pred  = ML_MODEL.predict(feat)[0]
    proba = ML_MODEL.predict_proba(feat)[0]
    ml_label = CLASSES[pred]
    ml_conf  = float(proba[pred]) * 100

    # Run rule-based classifier on the real image
    rule_label, rule_conf = rule_based_predict(arr)

    # Decision logic:
    # 1. If ML says non_food but rules found a food match → use rules
    # 2. If ML is confident (>55%) on a food class → trust ML
    # 3. If ML confidence is low (<45%) → prefer rules if rules found something
    # 4. If both agree → use ML label with boosted confidence
    non_food_idx = CLASSES.index('non_food')
    non_food_prob = float(proba[non_food_idx]) * 100

    if ml_label == 'non_food' and rule_label is not None and rule_conf > 0.52:
        # ML said non-food but colour rules strongly say it's food → trust rules
        label = rule_label
        conf  = round(rule_conf * 100, 1)
    elif ml_conf >= 55 and ml_label != 'non_food':
        # ML is confident on a food class → trust ML
        label = ml_label
        conf  = round(ml_conf, 1)
    elif rule_label is not None and rule_conf > 0.55 and non_food_prob > 35:
        # ML is uncertain and non_food probability is high, but rules say food
        label = rule_label
        conf  = round(rule_conf * 100, 1)
    elif ml_label != 'non_food' and rule_label == ml_label:
        # Both agree on same food class → boost confidence
        label = ml_label
        conf  = round(min(95, (ml_conf + rule_conf * 100) / 2 + 10), 1)
    else:
        label = ml_label
        conf  = round(ml_conf, 1)

    top3_idx = np.argsort(proba)[::-1][:3]
    top3     = [(CLASSES[i], round(float(proba[i])*100, 1)) for i in top3_idx]

    # If rule label differs from top3[0], inject it
    if rule_label and rule_label != ml_label:
        top3[0] = (label, conf)

    arr_f = arr.astype(np.float32)/255.0
    r, g, b = arr_f[:,:,0], arr_f[:,:,1], arr_f[:,:,2]
    metrics = {
        "mean_r": round(float(r.mean()*255),1), "mean_g": round(float(g.mean()*255),1),
        "mean_b": round(float(b.mean()*255),1),
        "white_pct": round(float(((r>0.85)&(g>0.85)&(b>0.85)).mean()*100),2),
        "texture_grad": round(float(np.sqrt(np.gradient(arr_f[:,:,0],axis=1)**2+np.gradient(arr_f[:,:,0],axis=0)**2).mean()*100),3),
        "brightness": round(float((0.299*r+0.587*g+0.114*b).mean()*255),1),
    }
    info = LABEL_INFO[label]
    return {"label":label,"display":info["display"],"status":info["status"],"icon":info["icon"],
            "color":info["color"],"short":info["short"],"desc":info["desc"],"tips":info["tips"],
            "confidence":round(conf,1),"top3":top3,"metrics":metrics}

def generate_pdf_report(result, username, timestamp):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    body   = ParagraphStyle('body', parent=styles['Normal'], fontSize=10, leading=15, textColor=colors.HexColor('#333333'))
    h2     = ParagraphStyle('h2', parent=styles['Heading2'], fontSize=13, textColor=colors.HexColor('#2c3e50'), spaceBefore=14, spaceAfter=6)
    sc     = colors.HexColor('#27ae60') if result['status']=='PURE' else colors.HexColor('#e74c3c') if result['status']=='ADULTERATED' else colors.HexColor('#f39c12')

    story = []
    hdr = Table([[Paragraph('<font color="white"><b>FoodPure — Food Adulteration Detection Report</b></font>', body)]], colWidths=[17*cm])
    hdr.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#1a1a2e')),
                               ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),
                               ('LEFTPADDING',(0,0),(-1,-1),14)]))
    story += [hdr, Spacer(1,14)]
    story.append(Paragraph(f'<b>Analysed by:</b> {username} &nbsp;&nbsp; <b>Date:</b> {timestamp}', body))
    story += [Spacer(1,10), HRFlowable(width='100%',thickness=0.5,color=colors.HexColor('#cccccc')), Spacer(1,10)]

    story.append(Paragraph('Analysis Result', h2))
    t1 = Table([['Sample Type', result['display']],['Status', result['status']],
                ['Confidence', f"{result['confidence']}%"],['Finding', result['short']]],
               colWidths=[5*cm,12*cm])
    t1.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#f0f4f8')),
                              ('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),10),
                              ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
                              ('LEFTPADDING',(0,0),(-1,-1),10),
                              ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#dddddd')),
                              ('BACKGROUND',(1,1),(1,1),colors.HexColor('#fdecea') if result['status']=='ADULTERATED' else colors.HexColor('#eafaf1') if result['status']=='PURE' else colors.HexColor('#fef9e7')),
                              ('TEXTCOLOR',(1,1),(1,1),sc),('FONTNAME',(1,1),(1,1),'Helvetica-Bold'),('FONTSIZE',(1,1),(1,1),11)]))
    story += [t1, Spacer(1,12)]

    story.append(Paragraph('Detailed Findings', h2))
    story.append(Paragraph(result['desc'], body))
    story += [Spacer(1,10)]

    story.append(Paragraph('Pixel-Level Analysis Metrics', h2))
    m = result['metrics']
    t2 = Table([['Metric','Value','Interpretation'],
                ['Mean Red Channel', str(m['mean_r']), 'Higher = more red pigment'],
                ['Mean Green Channel', str(m['mean_g']), 'Elevated = possible chalk'],
                ['Mean Blue Channel', str(m['mean_b']), 'Elevated = water dilution indicator'],
                ['White Pixel %', f"{m['white_pct']}%", '> 10% may indicate chalk powder'],
                ['Texture Gradient', str(m['texture_grad']), 'Lower = smoother / adulterated'],
                ['Brightness', str(m['brightness']), 'Reference: turmeric ~160, milk ~245']],
               colWidths=[5*cm,3*cm,9*cm])
    t2.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#2c3e50')),
                              ('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
                              ('FONTSIZE',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),6),
                              ('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),8),
                              ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#f8f9fa')]),
                              ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#cccccc'))]))
    story += [t2, Spacer(1,12)]

    story.append(Paragraph('Recommendations', h2))
    tip_style = ParagraphStyle('tip', parent=body, textColor=colors.HexColor('#e74c3c') if result['status']=='ADULTERATED' else colors.HexColor('#27ae60'))
    story.append(Paragraph(f"• {result['tips']}", tip_style))
    if result['status'] == 'ADULTERATED':
        story.append(Paragraph("• FSSAI Toll-Free: 1800-112-100", tip_style))
        story.append(Paragraph("• Preserve sample as evidence before discarding.", tip_style))

    story += [Spacer(1,20), HRFlowable(width='100%',thickness=0.5,color=colors.HexColor('#cccccc')), Spacer(1,6)]
    story.append(Paragraph('<font size="8" color="#999999">Generated by FoodPure AI Detection System. For informational purposes only. Consult FSSAI-certified labs for legal proceedings.</font>',
                            ParagraphStyle('foot', parent=body, alignment=TA_CENTER)))
    doc.build(story)
    buf.seek(0)
    return buf

# ── Routes ──────────────────────────────────

@app.route('/')
def index():    return send_from_directory('static', 'index.html')

@app.route('/static/<path:path>')
def static_files(path): return send_from_directory('static', path)

@app.route('/api/signup', methods=['POST'])
def signup():
    d = request.get_json()
    u,e,p = (d.get('username') or '').strip(),(d.get('email') or '').strip(),(d.get('password') or '')
    if not u or not e or not p: return jsonify(success=False,msg="All fields required"),400
    if len(p)<6: return jsonify(success=False,msg="Password min 6 chars"),400
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$',e): return jsonify(success=False,msg="Invalid email"),400
    try:
        with get_db() as conn: conn.execute("INSERT INTO users (username,email,password) VALUES (?,?,?)",(u,e,hash_pw(p)))
        return jsonify(success=True,msg="Account created!")
    except sqlite3.IntegrityError: return jsonify(success=False,msg="Username or email already exists"),409

@app.route('/api/login', methods=['POST'])
def login():
    d = request.get_json()
    u,p = (d.get('username') or '').strip(),(d.get('password') or '')
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?",(u,hash_pw(p))).fetchone()
    if not user: return jsonify(success=False,msg="Invalid username or password"),401
    session['user_id']=user['id']; session['username']=user['username']; session['role']=user['role']
    return jsonify(success=True,username=user['username'],role=user['role'])

@app.route('/api/logout', methods=['POST'])
def logout(): session.clear(); return jsonify(success=True)

@app.route('/api/me')
def me():
    if 'user_id' not in session: return jsonify(logged_in=False)
    return jsonify(logged_in=True, username=session['username'], role=session.get('role','user'))

@app.route('/api/profile', methods=['GET'])
def get_profile():
    if 'user_id' not in session: return jsonify(success=False,msg="Not authenticated"),401
    with get_db() as conn:
        user  = conn.execute("SELECT id,username,email,created FROM users WHERE id=?",(session['user_id'],)).fetchone()
        stats = conn.execute("SELECT COUNT(*) as t, SUM(CASE WHEN status='PURE' THEN 1 ELSE 0 END) as p, SUM(CASE WHEN status='ADULTERATED' THEN 1 ELSE 0 END) as a FROM history WHERE user_id=?",(session['user_id'],)).fetchone()
    return jsonify(success=True,username=user['username'],email=user['email'],created=user['created'],
                   total=stats['t'] or 0,pure=stats['p'] or 0,adulterated=stats['a'] or 0)

@app.route('/api/profile', methods=['PUT'])
def update_profile():
    if 'user_id' not in session: return jsonify(success=False),401
    d = request.get_json()
    new_email=(d.get('email') or '').strip(); old_pw=d.get('old_password') or ''; new_pw=d.get('new_password') or ''
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
        if new_email and new_email!=user['email']:
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$',new_email): return jsonify(success=False,msg="Invalid email"),400
            try: conn.execute("UPDATE users SET email=? WHERE id=?",(new_email,session['user_id']))
            except sqlite3.IntegrityError: return jsonify(success=False,msg="Email already in use"),409
        if new_pw:
            if user['password']!=hash_pw(old_pw): return jsonify(success=False,msg="Current password incorrect"),403
            if len(new_pw)<6: return jsonify(success=False,msg="New password min 6 chars"),400
            conn.execute("UPDATE users SET password=? WHERE id=?",(hash_pw(new_pw),session['user_id']))
    return jsonify(success=True,msg="Profile updated!")

@app.route('/api/predict', methods=['POST'])
def api_predict():
    if 'user_id' not in session: return jsonify(success=False,msg="Authentication required"),401
    if not check_rate(session['user_id']): return jsonify(success=False,msg="Rate limit (30/hr). Try later."),429
    if request.content_type and 'application/json' in request.content_type:
        d=request.get_json(); b64=d.get('image','')
        if ',' in b64: b64=b64.split(',')[1]
        img_bytes=base64.b64decode(b64); filename=f"cam_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}.jpg"
    else:
        f=request.files.get('image')
        if not f: return jsonify(success=False,msg="No image provided"),400
        img_bytes=f.read(); filename=f.filename or 'upload.jpg'; b64=base64.b64encode(img_bytes).decode()
    try: pil_img=Image.open(BytesIO(img_bytes))
    except Exception: return jsonify(success=False,msg="Invalid image file"),400
    result=predict(pil_img)
    ts=datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        cur=conn.execute("INSERT INTO history (user_id,food_type,result,status,confidence,image_name,image_b64,created) VALUES (?,?,?,?,?,?,?,?)",
                         (session['user_id'],result['display'],result['label'],result['status'],result['confidence'],filename,b64[:3000],ts))
        result['history_id']=cur.lastrowid; result['timestamp']=ts
    return jsonify(success=True,**result)

@app.route('/api/history')
def history():
    if 'user_id' not in session: return jsonify(success=False,msg="Not authenticated"),401
    page=int(request.args.get('page',1)); limit=int(request.args.get('limit',20)); offset=(page-1)*limit
    with get_db() as conn:
        total=conn.execute("SELECT COUNT(*) FROM history WHERE user_id=?",(session['user_id'],)).fetchone()[0]
        rows=conn.execute("SELECT * FROM history WHERE user_id=? ORDER BY created DESC LIMIT ? OFFSET ?",(session['user_id'],limit,offset)).fetchall()
    records=[]
    for r in rows:
        info=LABEL_INFO.get(r['result'],{})
        records.append({'id':r['id'],'food_type':r['food_type'],'result':r['result'],'status':r['status'],
                        'confidence':r['confidence'],'image_name':r['image_name'],'created':r['created'],
                        'color':info.get('color','#999'),'icon':info.get('icon','?')})
    return jsonify(success=True,history=records,total=total,page=page,pages=(total+limit-1)//limit)

@app.route('/api/history/<int:hid>/delete', methods=['DELETE'])
def delete_history(hid):
    if 'user_id' not in session: return jsonify(success=False),401
    with get_db() as conn: conn.execute("DELETE FROM history WHERE id=? AND user_id=?",(hid,session['user_id']))
    return jsonify(success=True)

@app.route('/api/history/clear', methods=['DELETE'])
def clear_history():
    if 'user_id' not in session: return jsonify(success=False),401
    with get_db() as conn: conn.execute("DELETE FROM history WHERE user_id=?",(session['user_id'],))
    return jsonify(success=True,msg="History cleared")

@app.route('/api/stats')
def user_stats():
    if 'user_id' not in session: return jsonify(success=False),401
    uid=session['user_id']
    with get_db() as conn:
        by_status=conn.execute("SELECT status,COUNT(*) as cnt FROM history WHERE user_id=? GROUP BY status",(uid,)).fetchall()
        by_food=conn.execute("SELECT food_type,COUNT(*) as cnt FROM history WHERE user_id=? GROUP BY food_type",(uid,)).fetchall()
        timeline=conn.execute("SELECT DATE(created) as day,COUNT(*) as cnt FROM history WHERE user_id=? GROUP BY day ORDER BY day DESC LIMIT 14",(uid,)).fetchall()
        avg_conf=conn.execute("SELECT AVG(confidence) FROM history WHERE user_id=?",(uid,)).fetchone()[0]
    return jsonify(success=True,
                   by_status={r['status']:r['cnt'] for r in by_status},
                   by_food=[{'label':r['food_type'],'count':r['cnt']} for r in by_food],
                   timeline=[{'day':r['day'],'count':r['cnt']} for r in timeline],
                   avg_confidence=round(avg_conf or 0,1))

@app.route('/api/export/csv')
def export_csv():
    if 'user_id' not in session: return jsonify(success=False),401
    with get_db() as conn:
        rows=conn.execute("SELECT food_type,result,status,confidence,image_name,created FROM history WHERE user_id=? ORDER BY created DESC",(session['user_id'],)).fetchall()
    out=io.StringIO(); w=csv.writer(out)
    w.writerow(['Food Type','Result','Status','Confidence (%)','Image','Date/Time'])
    for r in rows: w.writerow(list(r))
    resp=make_response(out.getvalue())
    resp.headers['Content-Type']='text/csv'; resp.headers['Content-Disposition']=f'attachment; filename=history_{session["username"]}.csv'
    return resp

@app.route('/api/export/pdf/<int:hid>')
def export_pdf(hid):
    if 'user_id' not in session: return jsonify(success=False),401
    with get_db() as conn:
        row=conn.execute("SELECT * FROM history WHERE id=? AND user_id=?",(hid,session['user_id'])).fetchone()
    if not row: return jsonify(success=False,msg="Not found"),404
    info=LABEL_INFO.get(row['result'],{})
    result={'display':row['food_type'],'status':row['status'],'confidence':row['confidence'],
            'short':info.get('short',''),'desc':info.get('desc',''),'tips':info.get('tips',''),
            'top3':[(row['result'],row['confidence'])],
            'metrics':{'mean_r':0,'mean_g':0,'mean_b':0,'white_pct':0,'texture_grad':0,'brightness':0}}
    buf=generate_pdf_report(result,session['username'],row['created'])
    return send_file(buf,mimetype='application/pdf',as_attachment=True,download_name=f'report_{hid}.pdf')

@app.route('/api/contact', methods=['POST'])
def contact():
    d=request.get_json()
    n,e,m=(d.get('name') or '').strip(),(d.get('email') or '').strip(),(d.get('message') or '').strip()
    if not n or not e or not m: return jsonify(success=False,msg="All fields required"),400
    with get_db() as conn: conn.execute("INSERT INTO contacts (name,email,message) VALUES (?,?,?)",(n,e,m))
    return jsonify(success=True,msg="Message received! We'll respond within 24 hours.")

def admin_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args,**kwargs):
        if session.get('role')!='admin': return jsonify(success=False,msg="Admin only"),403
        return fn(*args,**kwargs)
    return wrapper

@app.route('/api/admin/stats')
@admin_required
def admin_stats():
    with get_db() as conn:
        ut=conn.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0]
        st=conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        ad=conn.execute("SELECT COUNT(*) FROM history WHERE status='ADULTERATED'").fetchone()[0]
        pu=conn.execute("SELECT COUNT(*) FROM history WHERE status='PURE'").fetchone()[0]
        co=conn.execute("SELECT COUNT(*) FROM contacts WHERE resolved=0").fetchone()[0]
        ru=conn.execute("SELECT id,username,email,created FROM users WHERE role='user' ORDER BY created DESC LIMIT 10").fetchall()
        rs=conn.execute("SELECT h.id,u.username,h.food_type,h.status,h.confidence,h.created FROM history h JOIN users u ON h.user_id=u.id ORDER BY h.created DESC LIMIT 15").fetchall()
        bf=conn.execute("SELECT food_type,COUNT(*) as cnt FROM history GROUP BY food_type ORDER BY cnt DESC").fetchall()
        dl=conn.execute("SELECT DATE(created) as day,COUNT(*) as cnt FROM history GROUP BY day ORDER BY day DESC LIMIT 14").fetchall()
    return jsonify(success=True,users_total=ut,scans_total=st,adulterated=ad,pure=pu,contacts_open=co,
                   recent_users=[dict(r) for r in ru],recent_scans=[dict(r) for r in rs],
                   by_food=[{'label':r['food_type'],'count':r['cnt']} for r in bf],
                   daily=[{'day':r['day'],'count':r['cnt']} for r in dl])

@app.route('/api/admin/users')
@admin_required
def admin_users():
    with get_db() as conn:
        users=conn.execute("SELECT u.id,u.username,u.email,u.role,u.created,COUNT(h.id) as scans FROM users u LEFT JOIN history h ON h.user_id=u.id WHERE u.role='user' GROUP BY u.id ORDER BY u.created DESC").fetchall()
    return jsonify(success=True,users=[dict(u) for u in users])

@app.route('/api/admin/users/<int:uid>/delete', methods=['DELETE'])
@admin_required
def admin_delete_user(uid):
    with get_db() as conn:
        conn.execute("DELETE FROM history WHERE user_id=?",(uid,))
        conn.execute("DELETE FROM users WHERE id=? AND role='user'",(uid,))
    return jsonify(success=True)

@app.route('/api/admin/contacts')
@admin_required
def admin_contacts():
    with get_db() as conn:
        rows=conn.execute("SELECT * FROM contacts ORDER BY created DESC LIMIT 50").fetchall()
    return jsonify(success=True,contacts=[dict(r) for r in rows])

@app.route('/api/admin/contacts/<int:cid>/resolve', methods=['POST'])
@admin_required
def resolve_contact(cid):
    with get_db() as conn: conn.execute("UPDATE contacts SET resolved=1 WHERE id=?",(cid,))
    return jsonify(success=True)

@app.route('/api/admin/export/csv')
@admin_required
def admin_export_csv():
    with get_db() as conn:
        rows=conn.execute("SELECT u.username,h.food_type,h.result,h.status,h.confidence,h.image_name,h.created FROM history h JOIN users u ON h.user_id=u.id ORDER BY h.created DESC").fetchall()
    out=io.StringIO(); w=csv.writer(out)
    w.writerow(['Username','Food Type','Result','Status','Confidence (%)','Image','Date/Time'])
    for r in rows: w.writerow(list(r))
    resp=make_response(out.getvalue())
    resp.headers['Content-Type']='text/csv'; resp.headers['Content-Disposition']='attachment; filename=all_detections.csv'
    return resp

if __name__ == '__main__':
    init_db()
    print("\n🌿 FoodPure v2 — http://localhost:5000")
    print("   Admin login: admin / admin123\n")
    app.run(debug=True, host='0.0.0.0', port=5000)