const STORAGE_BASE_URL = 'https://vrdhnddomhhhooquxlrr.supabase.co/storage/v1/object/public/pet-images/';

function mapPost(p) {
    let finalImageUrl = null;

    if (p.image) {
        let tempImage = p.image;

        // 🚨 ดักจับตัวการสำคัญ: ถ้า Django ส่ง http://127.0.0.1 หรือ localhost มา ให้หั่นทิ้งให้หมด!
        if (tempImage.includes('127.0.0.1') || tempImage.includes('localhost')) {
            // ตัดเอาเฉพาะส่วนที่อยู่หลังคำว่า /media/ มาใช้ (เช่น เอาแค่ pets/images_20.jpg)
            if (tempImage.includes('/media/')) {
                tempImage = tempImage.split('/media/')[1];
            }
        }

        // หลังจากกำจัด 127.0.0.1 ทิ้งไปแล้ว ค่อยมาเช็คต่อ
        if (tempImage.startsWith('http')) {
            // ถ้าเป็นลิงก์ Supabase ที่ถูกต้องอยู่แล้ว ให้ใช้เลย
            finalImageUrl = tempImage;
        } 
        else {
            // ลบคำว่า 'media/' ที่อาจหลงเหลืออยู่ออก
            let cleanPath = tempImage.replace('media/', '').replace('/media/', '');
            
            // ถ้ามีเครื่องหมาย / นำหน้าสุด ให้ตัดทิ้ง
            if (cleanPath.startsWith('/')) {
                cleanPath = cleanPath.substring(1);
            }
            
            // นำ URL ของคลาวด์มาประกอบร่างกับชื่อไฟล์
            finalImageUrl = STORAGE_BASE_URL + cleanPath;
        }
    }

    // แมพข้อมูลเพื่อส่งไปแสดงผลที่หน้า HTML
    return {
        id:            p.id,
        type:          p.post_type,
        title:         p.name           || 'ไม่ทราบชื่อ',
        species:       p.pet_type, 
        breed:         p.breed          || null,
        gender:        p.gender         || 'unknown',
        age_months:    p.age            ?? null,
        color:         p.color          || null,
        description:   p.description    || null,
        location:      p.location_name  || null,
        image_url:     finalImageUrl,   // <--- รูปภาพจะต้องมาแล้ว!
        contact_name:  p.contact_name   || null,
        contact_phone: p.contact_phone  || null,
        contact_line:  p.social_link    || null,
        is_resolved:   p.status === 'resolved',
        created_at:    p.created_at,
    };
}