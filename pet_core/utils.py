"""
AI Utilities for PetFinder
- ResNet50 ImageNet เพื่อสกัด feature vector (2048 มิติ) สำหรับ similarity search
- Pet-type auto classification จาก ImageNet 1000 class → Thai pet type
- Image compression (Pillow) เพื่อลดขนาดไฟล์ก่อนอัปโหลด

หมายเหตุ: model โหลดครั้งเดียวตอน import แล้ว reuse ทุก request
"""
import io
import torch
import torch.nn as nn
import torchvision.models as tv_models
import torchvision.transforms as transforms
from PIL import Image, ImageOps

# ─────────────────────────────────────────────
# 1) Load ResNet50 ครั้งเดียว (ทั้ง classifier และ feature extractor)
# ─────────────────────────────────────────────
_weights = tv_models.ResNet50_Weights.IMAGENET1K_V2
_resnet50_full = tv_models.resnet50(weights=_weights)
_resnet50_full.eval()

# Feature extractor (ตัด layer สุดท้าย → vector 2048 มิติ)
_feature_model = nn.Sequential(*list(_resnet50_full.children())[:-1])
_feature_model.eval()

_preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Class labels จาก ImageNet (1000 classes)
_imagenet_categories = _weights.meta.get("categories", [])

# ─────────────────────────────────────────────
# 2) ImageNet class index → Thai pet type
#    อิง ImageNet-1K class taxonomy (https://gist.github.com/yrevar/942d3a0ac09ec9e5eb3a)
# ─────────────────────────────────────────────
# Range ของ class index ใน ImageNet ที่เป็นสัตว์เลี้ยงประเภทต่างๆ
_PET_TYPE_RANGES = [
    # (start_idx, end_idx_inclusive, thai_label)
    (7,   24,  'นก'),         # birds (cock, hen, ostrich, finches, ...)
    (80,  100, 'นก'),          # more birds (peacock, hornbill, ...)
    (33,  37,  'เต่า'),        # turtles
    (38,  68,  'สัตว์เลื้อยคลาน'),  # lizards, snakes (อาจไม่ใช่ pet ที่นิยม แต่กันไว้)
    (151, 268, 'สุนัข'),        # all dog breeds (Chihuahua, Maltese, Poodle, ...)
    (269, 275, 'หมาป่า'),       # wolves (rare)
    (281, 285, 'แมว'),          # cats (Egyptian, Persian, Siamese, tabby, ...)
    (286, 293, 'แมว'),          # big cats (cougar, lynx, ...)
    (330, 335, 'กระรอก/หนู'),   # squirrels, rodents
    (337, 339, 'กระต่าย'),      # rabbits/hares
]

# สี backup keyword ใน label (กรณี class index ไม่ตรง pattern)
_LABEL_KEYWORDS = [
    ('สุนัข',   ['dog', 'terrier', 'spaniel', 'retriever', 'hound', 'poodle', 'corgi',
               'shepherd', 'bulldog', 'beagle', 'husky', 'collie', 'mastiff', 'pug',
               'rottweiler', 'pinscher', 'doberman']),
    ('แมว',    ['cat', 'kitten', 'tabby', 'persian', 'siamese']),
    ('นก',     ['bird', 'parrot', 'cockatoo', 'macaw', 'finch', 'sparrow', 'owl',
               'hawk', 'eagle', 'pigeon', 'duck', 'goose', 'chicken', 'rooster']),
    ('กระต่าย', ['rabbit', 'hare', 'bunny']),
    ('เต่า',   ['turtle', 'tortoise']),
    ('ปลา',    ['fish', 'goldfish']),
    ('หนู',    ['hamster', 'mouse', 'rat', 'guinea pig']),
]


def _idx_to_pet_type(idx: int, label: str | None = None) -> str | None:
    """แปลง ImageNet class idx → Thai pet type"""
    for start, end, thai in _PET_TYPE_RANGES:
        if start <= idx <= end:
            return thai
    if label:
        low = label.lower()
        for thai, kws in _LABEL_KEYWORDS:
            if any(k in low for k in kws):
                return thai
    return None


# ─────────────────────────────────────────────
# 3) Public API
# ─────────────────────────────────────────────
def _open_image(img_or_path):
    """รับ path หรือ PIL.Image หรือ bytes → คืน PIL.Image RGB"""
    if isinstance(img_or_path, Image.Image):
        return img_or_path.convert('RGB')
    if isinstance(img_or_path, (bytes, bytearray)):
        return Image.open(io.BytesIO(img_or_path)).convert('RGB')
    return Image.open(img_or_path).convert('RGB')


def extract_feature_vector(img_or_path):
    """สกัด vector 2048 มิติ"""
    try:
        img = _open_image(img_or_path)
        # auto-rotate ตาม EXIF (มือถือ iOS/Android หมุนรูปบ่อย)
        img = ImageOps.exif_transpose(img)
        tensor = _preprocess(img).unsqueeze(0)
        with torch.no_grad():
            out = _feature_model(tensor)
        return out.flatten().numpy().tolist()
    except Exception as e:
        print(f"[AI] extract_feature_vector failed: {e}")
        return None


def classify_pet_type(img_or_path, top_k: int = 3) -> dict:
    """
    วิเคราะห์รูปภาพ → คืน {'pet_type': 'สุนัข', 'confidence': 0.83, 'top_labels': [...]}
    หากไม่สามารถจัดประเภทได้ → pet_type = None
    """
    try:
        img = _open_image(img_or_path)
        img = ImageOps.exif_transpose(img)
        tensor = _preprocess(img).unsqueeze(0)
        with torch.no_grad():
            logits = _resnet50_full(tensor)
            probs = torch.nn.functional.softmax(logits, dim=1)[0]
            top_p, top_i = torch.topk(probs, top_k)

        top_labels = []
        best_pet = None
        best_conf = 0.0

        for p, i in zip(top_p.tolist(), top_i.tolist()):
            label = _imagenet_categories[i] if i < len(_imagenet_categories) else f"class_{i}"
            top_labels.append({'label': label, 'prob': round(p, 4)})
            pt = _idx_to_pet_type(i, label)
            if pt and p > best_conf:
                best_pet = pt
                best_conf = p

        return {
            'pet_type': best_pet,
            'confidence': round(best_conf, 4),
            'top_labels': top_labels,
        }
    except Exception as e:
        print(f"[AI] classify_pet_type failed: {e}")
        return {'pet_type': None, 'confidence': 0.0, 'top_labels': []}


def analyze_image(img_or_path) -> dict:
    """
    วิเคราะห์รูปภาพแบบครบ — ทั้ง vector + classification (single forward pass จะดีกว่า
    แต่ในเวอร์ชันนี้แยกเรียก 2 รอบเพื่อความตรงไปตรงมา)
    """
    img = _open_image(img_or_path)
    img = ImageOps.exif_transpose(img)
    vec = extract_feature_vector(img)
    cls = classify_pet_type(img)
    return {
        'feature_vector': vec,
        **cls,
    }


# ─────────────────────────────────────────────
# 4) Image compression (ลดขนาดก่อนอัปโหลดเข้า Supabase)
# ─────────────────────────────────────────────
def compress_image(file_obj, max_dim: int = 1600, quality: int = 82) -> io.BytesIO:
    """
    รับ Django UploadedFile → คืน BytesIO ของ JPEG ที่ resize + compress แล้ว
    - ลด long-edge ลง max_dim px
    - แปลงเป็น JPEG quality 82 (ไฟล์เล็กกว่า PNG/HEIC มาก)
    - auto-rotate ตาม EXIF
    """
    try:
        file_obj.seek(0)
    except Exception:
        pass
    img = Image.open(file_obj)
    img = ImageOps.exif_transpose(img)
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')

    w, h = img.size
    if max(w, h) > max_dim:
        if w >= h:
            new_w = max_dim
            new_h = int(h * max_dim / w)
        else:
            new_h = max_dim
            new_w = int(w * max_dim / h)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=quality, optimize=True, progressive=True)
    buf.seek(0)
    return buf
