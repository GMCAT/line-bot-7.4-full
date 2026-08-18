# Service Architecture v1

โปรเจกต์รุ่นนี้เริ่มใช้ interface กลาง เพื่อทยอยแยกระบบเดิมโดยไม่ทำให้คำสั่งเก่าหยุดทำงาน

## Contract กลาง

- `ServiceRequest`: ข้อมูลมาตรฐานที่ Gateway ส่งให้ทุก Service
- `ServiceResponse`: ผลลัพธ์มาตรฐาน รวมสถานะ retry และ error code
- `BotService`: interface ที่ Service ทุกตัวต้องทำตาม
- `ServiceRegistry`: ลงทะเบียน เลือก และแยกข้อผิดพลาดของ Service

## Service ที่ย้ายแล้ว

1. `news` — ดึงและแสดงข่าวแบบ plain โดยไม่พึ่ง AI
2. `stocks` — ราคาหุ้น
3. `ai_chat` — AI ถามตอบทั่วไปผ่านคำสั่ง `ถาม ...` หรือ `ai ...`
4. `contacts` — ค้นหาผู้ติดต่อและรายชื่อฉุกเฉิน แยกจากคำสั่ง Admin
5. `subscriptions` — จัดการหัวข้อติดตามและสถานะข่าวประจำวันแยกตาม chat ID
6. `admin` — เพิ่ม/ตรวจ/แสดงข้อมูลฐานหลัก พร้อมตรวจสิทธิ์ผู้ใช้
7. `settings` — ดูและเปลี่ยน AI สำหรับคำสั่ง `ถาม` (`none/local/gemini/anthropic`)

ระบบข่าวแสดงผลแบบ plain เท่านั้น และไม่เรียก AI ทั้งข่าวปกติ ข่าวจากคำค้น และข่าวประจำวัน

Contacts ใช้ `DATABASE_URL` เพียงฐานเดียว และรองรับ primary key แบบ Int autoincrement ตาม Prisma schema
แบบฟอร์มเพิ่มผู้ติดต่อรองรับ `ตัวย่อหน่วยงาน` และบันทึกลง `organizations.code`

คำสั่งเดิมที่ยังผ่าน legacy adapter คือเมนูช่วยเหลือและข้อความ fallback ที่ยังไม่ได้แยกเป็น Service

## การกำหนดหน้าที่ต่อบอท

```env
BOT_SERVICES=news,stocks,ai_chat,contacts,subscriptions,admin,settings
```

ตัวอย่าง Bot ข่าวอย่างเดียว:

```env
BOT_SERVICES=news
```

ตัวอย่าง Bot AI อย่างเดียว:

```env
BOT_SERVICES=ai_chat
```

หากมีหลาย Bot สามารถใช้ตัวแปรเฉพาะ bot id เช่น `BOT_SERVICES_NEWS_BOT=news`

## หลักการแยกความเสียหาย

Registry จับ exception ภายใน Service และตอบว่าระบบนั้นไม่พร้อม โดยไม่ปล่อย exception ไปทำให้
webhook ล้มทั้งตัว อย่างไรก็ตามรุ่นนี้ยังเป็น process เดียว การแยกการล่มระดับ process ต้องย้าย Service
ออกเป็น deployment/worker อิสระในระยะถัดไป
