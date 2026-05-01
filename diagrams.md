# TarmRoy — Diagrams (รูปที่ 3.1–3.4)

## วิธีดู
- **UseCase / Activity / Sequence / ER (Mermaid):** วางโค้ดใน [mermaid.live](https://mermaid.live) → กด **Actions → PNG** เพื่อ download
- **UseCase ทางเลือก (PlantUML):** ถ้าต้องการสไตล์ UML แบบมาตรฐาน ใช้ [plantuml.com/plantuml](https://www.plantuml.com/plantuml/uml/)

ตั้งความละเอียดที่ Mermaid Live ให้ใหญ่ขึ้น: **Actions → Configure → maxWidth: 2000** ก่อน export PNG

---

## รูปที่ 3.1  Use Case Diagram ของระบบ TarmRoy

### ตัวเลือก A — Mermaid (แนะนำสำหรับเลย์เอาต์เดียวกับเอกสาร)

```mermaid
flowchart LR
    Guest((👤 Guest))
    Member((👥 Member))
    Admin((🔧 Administrator))
    AI[/🤖 ResNet50 + Supabase\nExternal Services/]

    subgraph SYSTEM["🐾 TarmRoy System"]
      direction TB

      subgraph PUBLIC["📂 Public (Guest)"]
        UC_View["ดูรายการประกาศ"]
        UC_SearchTxt["ค้นหาด้วยข้อความ"]
        UC_SearchImg["ค้นหาด้วยรูปภาพ"]
        UC_Map["ดูประกาศบนแผนที่ + Heatmap"]
        UC_Detail["ดูรายละเอียดประกาศ"]
        UC_Blog["อ่านบทความ/เคล็ดลับ"]
        UC_Product["ดูสินค้าโปรโมท"]
      end

      subgraph AUTH["🔐 Authentication"]
        UC_Signup["สมัครสมาชิก (Email)"]
        UC_Login["เข้าสู่ระบบ (JWT)"]
        UC_Logout["ออกจากระบบ"]
        UC_Reset["รีเซตรหัสผ่าน"]
      end

      subgraph POST["📝 Post Management"]
        UC_Lost["ลงประกาศสัตว์หาย"]
        UC_Found["ลงประกาศพบสัตว์"]
        UC_Edit["แก้ไขประกาศของฉัน"]
        UC_Resolved["ปิดประกาศ (เจอแล้ว)"]
        UC_Delete["ลบประกาศของฉัน"]
        UC_Comment["แสดงความคิดเห็น/รีแอ็กชัน"]
        UC_MyPosts["ดูประกาศของฉัน"]
        UC_Profile["จัดการโปรไฟล์"]
      end

      subgraph ADMIN_GRP["⚙️ Admin Management"]
        UC_AdmPosts["จัดการประกาศทั้งหมด"]
        UC_AdmUsers["จัดการผู้ใช้งาน"]
        UC_AdmBlog["จัดการบทความ"]
        UC_AdmProduct["จัดการสินค้าโปรโมท + Sync ราคา"]
        UC_AdmStats["ดูสถิติของระบบ"]
      end
    end

    %% Guest flows
    Guest --> UC_View
    Guest --> UC_SearchTxt
    Guest --> UC_SearchImg
    Guest --> UC_Map
    Guest --> UC_Detail
    Guest --> UC_Blog
    Guest --> UC_Product

    %% Member inherits Guest
    Member --> UC_Signup
    Member --> UC_Login
    Member --> UC_Logout
    Member --> UC_Reset
    Member --> UC_Lost
    Member --> UC_Found
    Member --> UC_Edit
    Member --> UC_Resolved
    Member --> UC_Delete
    Member --> UC_Comment
    Member --> UC_MyPosts
    Member --> UC_Profile
    Member -.->|inherits| Guest

    %% Admin inherits Member
    Admin --> UC_AdmPosts
    Admin --> UC_AdmUsers
    Admin --> UC_AdmBlog
    Admin --> UC_AdmProduct
    Admin --> UC_AdmStats
    Admin -.->|inherits| Member

    %% External integrations
    UC_SearchImg -.->|extract vector| AI
    UC_Lost -.->|store image| AI
    UC_Found -.->|store image| AI
    UC_Login -.->|JWT verify| AI

    %% Includes
    UC_Lost -.->|<<include>>| UC_Login
    UC_Found -.->|<<include>>| UC_Login
    UC_Edit -.->|<<include>>| UC_Login
    UC_Comment -.->|<<include>>| UC_Login

    classDef actor fill:#FEF3C7,stroke:#F59E0B,stroke-width:2px
    classDef ext fill:#F0FDF4,stroke:#22C55E,stroke-width:2px,stroke-dasharray:5 5
    class Guest,Member,Admin actor
    class AI ext
```

### ตัวเลือก B — PlantUML (สไตล์ UML มาตรฐาน)

```plantuml
@startuml TarmRoy_UseCase
skinparam actorStyle awesome
skinparam usecase {
  BackgroundColor #FFF8F1
  BorderColor #F59E0B
  ArrowColor #374151
}
left to right direction

actor "👤 Guest" as Guest
actor "👥 Member" as Member
actor "🔧 Administrator" as Admin
actor "🤖 ResNet50 + Supabase" as AI <<external>>

rectangle "🐾 TarmRoy System" {

  package "Public (Guest)" {
    usecase "ดูรายการประกาศ" as UC_View
    usecase "ค้นหาด้วยข้อความ" as UC_SearchTxt
    usecase "ค้นหาด้วยรูปภาพ" as UC_SearchImg
    usecase "ดูประกาศบนแผนที่" as UC_Map
    usecase "ดูรายละเอียดประกาศ" as UC_Detail
    usecase "อ่านบทความ/เคล็ดลับ" as UC_Blog
    usecase "ดูสินค้าโปรโมท" as UC_Product
  }

  package "Authentication" {
    usecase "สมัครสมาชิก" as UC_Signup
    usecase "เข้าสู่ระบบ (JWT)" as UC_Login
    usecase "ออกจากระบบ" as UC_Logout
  }

  package "Post Management" {
    usecase "ลงประกาศสัตว์หาย" as UC_Lost
    usecase "ลงประกาศพบสัตว์" as UC_Found
    usecase "แก้ไข/ลบประกาศ" as UC_Edit
    usecase "ปิดประกาศ (เจอแล้ว)" as UC_Resolved
    usecase "แสดงความคิดเห็น" as UC_Comment
    usecase "ดูประกาศของฉัน" as UC_MyPosts
    usecase "จัดการโปรไฟล์" as UC_Profile
  }

  package "Admin Management" {
    usecase "จัดการประกาศทั้งหมด" as UC_AdmPosts
    usecase "จัดการผู้ใช้งาน" as UC_AdmUsers
    usecase "จัดการบทความ" as UC_AdmBlog
    usecase "จัดการสินค้าโปรโมท" as UC_AdmProduct
    usecase "ดูสถิติของระบบ" as UC_AdmStats
  }
}

Guest --> UC_View
Guest --> UC_SearchTxt
Guest --> UC_SearchImg
Guest --> UC_Map
Guest --> UC_Detail
Guest --> UC_Blog
Guest --> UC_Product

Member --|> Guest
Member --> UC_Signup
Member --> UC_Login
Member --> UC_Logout
Member --> UC_Lost
Member --> UC_Found
Member --> UC_Edit
Member --> UC_Resolved
Member --> UC_Comment
Member --> UC_MyPosts
Member --> UC_Profile

Admin --|> Member
Admin --> UC_AdmPosts
Admin --> UC_AdmUsers
Admin --> UC_AdmBlog
Admin --> UC_AdmProduct
Admin --> UC_AdmStats

UC_SearchImg ..> AI : <<uses>>
UC_Lost ..> AI : <<stores image>>
UC_Login ..> AI : <<verify JWT>>
UC_Lost ..> UC_Login : <<include>>
UC_Found ..> UC_Login : <<include>>
UC_Comment ..> UC_Login : <<include>>

@enduml
```

---

## รูปที่ 3.2  Activity Diagram การลงประกาศสัตว์หาย

```mermaid
flowchart TD
    Start([● เริ่มต้น]) --> Login{เข้าสู่ระบบ\nแล้วหรือยัง?}
    Login -->|ยัง| GoLogin[เข้าหน้า Login\n→ กรอก Email/Password\n→ Supabase Auth ออก JWT]
    GoLogin --> Login
    Login -->|แล้ว| Menu[คลิกเมนู\n'ลงประกาศสัตว์หาย']
    Menu --> Form[กรอกข้อมูลในฟอร์ม\n• ชื่อ ประเภท สายพันธุ์\n• อายุ เพศ สี\n• รายละเอียดเพิ่มเติม]
    Form --> Upload[อัปโหลดรูปภาพ\nสูงสุด 5 รูป]
    Upload --> Map[ระบุพิกัดบนแผนที่\nLeaflet + OpenStreetMap]
    Map --> DateTime[ระบุวันที่/เวลาที่หาย]
    Map --> Contact[กรอกข้อมูลติดต่อ\n• ชื่อ • อีเมล • โทร]
    DateTime --> Submit[คลิกปุ่ม 'ลงประกาศ']
    Contact --> Submit
    Submit --> Validate{ตรวจสอบ\nข้อมูลครบ?}
    Validate -->|ไม่ครบ| ShowError[แสดงข้อความ Error\n→ ย้อนกลับไปแก้]
    ShowError --> Form
    Validate -->|ครบ| Compress[บีบอัดรูปด้วย Pillow\nmax_dim=1600, q=82]
    Compress --> AI[ส่งรูปเข้า ResNet50\n→ extract feature vector\n→ classify pet_type]
    AI --> Storage[อัปโหลดรูปลง\nSupabase Storage]
    AI --> DB[บันทึก PetPost + PetImage\nลง PostgreSQL+pgvector\nพร้อม vector 2,048 มิติ]
    Storage --> Cache[ล้าง cache:\nlist_lost_v1, home_data_v2,\nmap_data_v1]
    DB --> Cache
    Cache --> Detail[Redirect ไปยัง\nหน้ารายละเอียดประกาศ\n/pet/<id>/]
    Detail --> Confirm[เจ้าของยืนยัน\nความถูกต้อง]
    Confirm --> End([◉ จบ])

    classDef startEnd fill:#FEC356,stroke:#003459,stroke-width:3px,color:#fff
    classDef decision fill:#FCEED5,stroke:#003459,stroke-width:2px
    classDef action fill:#FFF,stroke:#003459,stroke-width:1.5px
    classDef ai fill:#EDE9FE,stroke:#7C3AED,stroke-width:2px
    class Start,End startEnd
    class Login,Validate decision
    class AI,Compress ai
```

---

## รูปที่ 3.3  E-R Diagram ของระบบฐานข้อมูล TarmRoy

```mermaid
erDiagram
    USER ||--o{ PETPOST : "owns"
    USER ||--o{ COMMENT : "writes"
    PETPOST ||--o{ PETIMAGE : "has"
    PETPOST ||--o{ COMMENT : "receives"

    USER {
        int id PK
        string username
        string email
        string password
        string supabase_uuid "Supabase Auth UUID"
        bool is_staff
        bool is_active
        datetime date_joined
    }

    PETPOST {
        bigint id PK
        int owner_id FK "→ USER.id"
        string supabase_user_id "Supabase UUID"
        string post_type "lost / found"
        string status "active / resolved"
        string name "ชื่อสัตว์"
        string pet_type "สุนัข/แมว/อื่น"
        string breed
        string age
        string gender "M/F/U"
        string color
        string microchip
        text description
        image image "main image"
        decimal latitude
        decimal longitude
        string location_name
        date lost_date
        time lost_time
        date found_date
        time found_time
        decimal reward
        string contact_name
        string contact_email
        string contact_phone
        url social_link
        datetime resolved_at
        text resolved_note
        datetime created_at
        datetime updated_at
    }

    PETIMAGE {
        bigint id PK
        int pet_post_id FK "→ PETPOST.id"
        image image
        vector feature_vector "2048-dim ResNet50"
    }

    COMMENT {
        bigint id PK
        int pet_post_id FK "→ PETPOST.id"
        int user_id FK "→ USER.id"
        string author_name
        text text
        string reaction "👍 ❤ 🙏"
        datetime created_at
    }

    BLOGPOST {
        bigint id PK
        string title
        string summary
        image cover_image
        text body "HTML"
        string author_name
        date published_at
        bool is_published
        datetime created_at
        datetime updated_at
    }

    PRODUCT {
        bigint id PK
        string name
        text description
        decimal price
        decimal scraped_price "from external_link"
        datetime last_scraped_at
        string category
        image image
        url external_link
        string promoter_name
        string promoter_contact
        decimal amount_paid
        int promotion_days
        date promotion_start
        date promotion_end
        bool is_active
        int sort_order
        datetime created_at
        datetime updated_at
    }
```

> **หมายเหตุ:** `PETIMAGE.feature_vector` เป็นชนิดข้อมูล `vector(2048)` ของส่วนขยาย pgvector — รองรับการค้นหาแบบ Cosine Distance ผ่านตัวดำเนินการ `<=>` ส่วน BLOGPOST และ PRODUCT เป็น entity แยก ไม่มี FK เชื่อมกับ PETPOST/USER โดยตรง

---

## รูปที่ 3.4  Sequence Diagram การค้นหาด้วยรูปภาพ

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 User
    participant Browser as 🌐 Browser
    participant Django as ⚡ Django<br/>(views.search_pet)
    participant Pillow as 🖼️ Pillow<br/>(compress_image)
    participant ResNet as 🧠 ResNet50<br/>(analyze_image)
    participant pgv as 🗄️ PostgreSQL<br/>+ pgvector
    participant Storage as ☁️ Supabase<br/>Storage

    User->>Browser: คลิก "ค้นหาด้วย AI"
    Browser->>User: แสดงหน้า /search/
    User->>Browser: เลือกไฟล์รูปภาพ + Submit
    Browser->>Django: POST /search/<br/>(multipart/form-data)

    activate Django
    Django->>Pillow: compress_image(file)<br/>max_dim=1600, q=82
    Pillow-->>Django: bytes (JPEG)

    Django->>ResNet: analyze_image(bytes)
    activate ResNet
    Note over ResNet: 1. Resize 232 + CenterCrop 224<br/>2. Normalize ImageNet<br/>3. TTA (original + h-flip)<br/>4. Average + L2 Normalize
    ResNet-->>Django: { feature_vector[2048],<br/>pet_type, top5_labels }
    deactivate ResNet

    Django->>pgv: SELECT * FROM pet_core_petimage<br/>ORDER BY feature_vector <=> :query_vec<br/>LIMIT 24
    activate pgv
    Note over pgv: pgvector คำนวณ<br/>Cosine Distance ระหว่าง<br/>query_vec และทุก<br/>vector ในตาราง
    pgv-->>Django: 24 PetImage rows<br/>เรียงตาม distance น้อย→มาก
    deactivate pgv

    Django->>pgv: JOIN PetPost<br/>เพื่อดึง metadata
    pgv-->>Django: PetPost data

    loop สำหรับแต่ละผลลัพธ์
        Django->>Storage: GET thumbnail URL<br/>(Image Transform)
        Storage-->>Django: signed URL
    end

    Django->>Django: คำนวณ similarity_score<br/>= 1 − cosine_distance
    Django->>Django: Smart Re-ranking<br/>(จำนวนรูปตรง + pet_type match)
    Django-->>Browser: HTML + รายการ 24<br/>เรียงตาม score
    deactivate Django

    Browser->>User: แสดงการ์ดผลลัพธ์<br/>พร้อม % ความใกล้เคียง
    User->>Browser: คลิกประกาศที่ใช่
    Browser->>Django: GET /pet/<id>/
    Django-->>Browser: หน้ารายละเอียดประกาศ
```

---

## วิธีนำไปใช้

### Mermaid → PNG
1. ไปที่ https://mermaid.live
2. ลบโค้ดตัวอย่าง แล้ววาง code block ของ diagram ที่ต้องการ (เริ่มจากบรรทัดถัดจาก ` ```mermaid ` ถึงก่อน ` ``` `)
3. รอจน preview ขึ้นทางขวา
4. กด **Actions** ที่มุมขวาบน → **PNG** หรือ **SVG**
5. ตั้งชื่อไฟล์ตามรูปในรายงาน เช่น `figure_3_1_usecase.png`

### PlantUML → PNG
1. ไปที่ https://www.plantuml.com/plantuml/
2. วาง code block ของ PlantUML
3. กด **Submit** จะได้ภาพ PNG ทันที — กด save image as

### นำไปใส่ Word
1. เปิดไฟล์ `TarmRoy_รายงานโครงงาน2_ฉบับสมบูรณ์.docx` ใน MS Word
2. กด `Ctrl+F` หา Caption เช่น "**รูปที่ 3.1 Use Case Diagram ของระบบ TarmRoy**"
3. คลิกที่บรรทัดเหนือ Caption → **Insert → Pictures → This Device** → เลือก PNG
4. คลิกขวา → **Wrap Text → In Line with Text**
5. ปรับขนาดให้กว้างไม่เกิน 6 นิ้ว
6. จัดกึ่งกลาง (Ctrl+E)

---

## เทคนิคปรับสีให้เข้ากับเอกสาร TarmRoy

ถ้าต้องการสีตามแบรนด์ TarmRoy (Navy + Cream + Gold) เพิ่ม `%%{init: ...}%%` ที่บรรทัดแรกของ Mermaid:

```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor': '#FCEED5',
  'primaryTextColor': '#003459',
  'primaryBorderColor': '#FEC356',
  'lineColor': '#003459',
  'secondaryColor': '#FFE7BA',
  'tertiaryColor': '#FFFFFF'
}}}%%
flowchart TD
  ...
```

วางบรรทัดนี้ก่อน `flowchart`/`erDiagram`/`sequenceDiagram` จะได้สีน้ำเงินกรมท่า + ครีม + เหลือง ตามแบรนด์ระบบ

---

ทุก diagram ออกแบบให้สอดคล้องกับเนื้อหาในรายงาน:
- **3.1 Use Case** — Actor 3 ระดับ (Guest → Member → Administrator) มี inheritance พร้อม external service (ResNet50 + Supabase)
- **3.2 Activity** — flow การลงประกาศสัตว์หายตั้งแต่ login → upload → ResNet50 → pgvector → cache invalidation → redirect
- **3.3 ER** — 6 entity ตรงกับ models.py (User, PetPost, PetImage, Comment, BlogPost, Product) ครบทุก field พร้อม FK และ cardinality
- **3.4 Sequence** — 6 lifeline (User, Browser, Django, Pillow, ResNet50, pgvector, Storage) แสดงทั้ง TTA, L2 normalize, cosine distance, smart re-ranking
