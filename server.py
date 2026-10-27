#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gate Academy - Web Sunucusu ve Otomatik Kayıt Mail Botu
Çalıştırmak için: python3 server.py
Varsayılan adres: http://localhost:3000
"""

import csv
import datetime
import json
import os
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REG_JSON_PATH = os.path.join(BASE_DIR, "registrations.json")
REG_CSV_PATH = os.path.join(BASE_DIR, "registrations.csv")
SENT_EMAILS_DIR = os.path.join(BASE_DIR, "sent_emails")
ENV_PATH = os.path.join(BASE_DIR, ".env")

os.makedirs(SENT_EMAILS_DIR, exist_ok=True)


def load_env():
    """Her istekte .env dosyasını okur (sunucuyu yeniden başlatmadan ayar değişimi sağlar)."""
    config = {
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "",
        "SMTP_PASS": "",
        "SENDER_NAME": "Gate Academy",
        "ADMIN_EMAIL": "contact.gateacademy@gmail.com",
        "PORT": "3000",
    }
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip().strip('"').strip("'")
    return config


COURSE_META = {
    "qrafik": {
        "az": {
            "name": "Qrafik Dizayn",
            "duration": "32 dərs • 4 ay (Həftədə 2 dəfə, 2 saat)",
            "tools": "Adobe Photoshop, Illustrator, Higgsfield AI",
        },
        "tr": {
            "name": "Grafik Tasarım",
            "duration": "32 ders • 4 ay (Haftada 2 gün, 2 saat)",
            "tools": "Adobe Photoshop, Illustrator, Higgsfield AI",
        },
        "en": {
            "name": "Graphic Design",
            "duration": "32 lessons • 4 months (2x/week, 2 hours)",
            "tools": "Adobe Photoshop, Illustrator, Higgsfield AI",
        },
    },
    "motion": {
        "az": {
            "name": "Motion Dizayn",
            "duration": "48 dərs • 4 ay (Həftədə 3 dəfə, 2 saat)",
            "tools": "Adobe After Effects, Premiere Pro, Higgsfield AI",
        },
        "tr": {
            "name": "Motion Tasarım",
            "duration": "48 ders • 4 ay (Haftada 3 gün, 2 saat)",
            "tools": "Adobe After Effects, Premiere Pro, Higgsfield AI",
        },
        "en": {
            "name": "Motion Design",
            "duration": "48 lessons • 4 months (3x/week, 2 hours)",
            "tools": "Adobe After Effects, Premiere Pro, Higgsfield AI",
        },
    },
    "uiux": {
        "az": {
            "name": "UI/UX Dizayn",
            "duration": "48 dərs • 4 ay (Həftədə 3 dəfə, 2 saat)",
            "tools": "Figma, UX Research, Design System",
        },
        "tr": {
            "name": "UI/UX Tasarım",
            "duration": "48 ders • 4 ay (Haftada 3 gün, 2 saat)",
            "tools": "Figma, UX Research, Design System",
        },
        "en": {
            "name": "UI/UX Design",
            "duration": "48 lessons • 4 months (3x/week, 2 hours)",
            "tools": "Figma, UX Research, Design System",
        },
    },
}


EMAIL_I18N = {
    "az": {
        "subject": "Gate Academy | Qeydiyyatınız Təsdiqləndi! 🎨",
        "badge": "QEYDİYYAT TƏSDİQİ",
        "greeting": "Salam, {name}!",
        "intro": "Gate Academy-yə müraciətiniz uğurla qeydə alındı. Yaradıcılığa qapı açmaq üçün ilk addımı atdınız! Tədris koordinatorumuz ən qısa zamanda sizinlə əlaqə saxlayaraq ödənişsiz sınaq dərsi vaxtını təyin edəcək.",
        "summary_title": "QEYDİYYAT MƏLUMATLARINIZ",
        "lbl_name": "Ad və Soyad",
        "lbl_phone": "Əlaqə Nömrəsi",
        "lbl_email": "E-poçt",
        "lbl_course": "Seçilən Tədris İstiqaməti",
        "lbl_duration": "Tədris Müddəti",
        "lbl_tools": "Öyrədiləcək Proqramlar",
        "lbl_reg_id": "Müraciət Kodu",
        "cta_text": "Gözləmədən dərhal sınaq dərsi vaxtını seçmək istəyirsinizsə, WhatsApp üzərindən bizə yaza bilərsiniz:",
        "cta_btn": "WhatsApp-da Bizə Yazın",
        "footer": "Yaradıcılığa qapı aç. • Gate Academy Bakı, Azərbaycan",
    },
    "tr": {
        "subject": "Gate Academy | Kaydınız Alındı! 🎨",
        "badge": "KAYIT ONAYI",
        "greeting": "Merhaba, {name}!",
        "intro": "Gate Academy başvurunuz başarıyla alındı. Yaratıcılığa kapı açmak için ilk adımı attınız! Eğitim koordinatörümüz en kısa sürede sizinle iletişime geçerek ücretsiz deneme dersi gün ve saatini birlikte planlayacaktır.",
        "summary_title": "KAYIT BİLGİLERİNİZ",
        "lbl_name": "Ad Soyad",
        "lbl_phone": "Telefon Numarası",
        "lbl_email": "E-posta Adresi",
        "lbl_course": "Seçilen Eğitim Programı",
        "lbl_duration": "Eğitim Süresi",
        "lbl_tools": "Kapsanan Araçlar & AI",
        "lbl_reg_id": "Başvuru Kodu",
        "cta_text": "Beklemeden hemen deneme dersi saatinizi belirlemek isterseniz WhatsApp üzerinden bize ulaşabilirsiniz:",
        "cta_btn": "WhatsApp'tan Bize Yazın",
        "footer": "Yaratıcılığa kapı aç. • Gate Academy",
    },
    "en": {
        "subject": "Gate Academy | Your Registration is Confirmed! 🎨",
        "badge": "REGISTRATION CONFIRMED",
        "greeting": "Hello, {name}!",
        "intro": "Your application to Gate Academy has been successfully received. You have taken the first step toward unlocking your creative potential! Our admissions coordinator will contact you shortly to schedule your free trial class.",
        "summary_title": "YOUR REGISTRATION DETAILS",
        "lbl_name": "Full Name",
        "lbl_phone": "Phone Number",
        "lbl_email": "Email Address",
        "lbl_course": "Selected Program Track",
        "lbl_duration": "Program Schedule",
        "lbl_tools": "Tools & AI Covered",
        "lbl_reg_id": "Reference ID",
        "cta_text": "Want to pick your free trial slot right away? Message our team directly on WhatsApp:",
        "cta_btn": "Chat with Us on WhatsApp",
        "footer": "Unlock creativity. • Gate Academy",
    },
}


def build_email_html(record):
    lang = record.get("lang", "az")
    if lang not in EMAIL_I18N:
        lang = "az"
    t = EMAIL_I18N[lang]

    course_key = record.get("course", "qrafik")
    c_meta = COURSE_META.get(course_key, COURSE_META["qrafik"]).get(lang, COURSE_META["qrafik"]["az"])

    greeting = t["greeting"].format(name=record["name"])

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{t["subject"]}</title>
</head>
<body style="margin:0;padding:0;background-color:#0B1B5E;font-family:'DM Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#0B1B5E;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#0B1B5E;padding:36px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;background-color:#ffffff;border-radius:32px;overflow:hidden;box-shadow:0 24px 60px rgba(0,0,0,0.35);">
          <!-- Top Hero Header -->
          <tr>
            <td style="background-color:#1E45FC;padding:36px 32px;text-align:center;color:#ffffff;">
              <div style="display:inline-block;background-color:#AEFF03;color:#0B1B5E;font-size:11px;font-weight:900;letter-spacing:0.08em;padding:6px 14px;border-radius:99px;text-transform:uppercase;margin-bottom:14px;">
                ✦ {t["badge"]}
              </div>
              <h1 style="margin:0;font-size:32px;font-weight:900;letter-spacing:-0.03em;text-transform:uppercase;color:#ffffff;line-height:1.05;">
                GATE ACADEMY
              </h1>
              <p style="margin:8px 0 0;font-size:14px;color:rgba(255,255,255,0.88);font-weight:500;">
                Adobe Creative Cloud &amp; AI Design Ecosystem
              </p>
            </td>
          </tr>

          <!-- Main Body -->
          <tr>
            <td style="padding:36px 32px 24px;">
              <h2 style="margin:0 0 12px;font-size:24px;font-weight:900;color:#0B1B5E;letter-spacing:-0.02em;">
                {greeting}
              </h2>
              <p style="margin:0 0 26px;font-size:15.5px;line-height:1.6;color:#2E3B70;">
                {t["intro"]}
              </p>

              <!-- Summary Box -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#EEF1F9;border-radius:22px;padding:24px;margin-bottom:26px;">
                <tr>
                  <td>
                    <div style="font-size:12px;font-weight:900;letter-spacing:0.06em;color:#1E45FC;text-transform:uppercase;margin-bottom:14px;">
                      📋 {t["summary_title"]}
                    </div>

                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="font-size:14.5px;color:#0B1B5E;">
                      <tr>
                        <td style="padding:7px 0;color:#52608F;font-weight:600;width:42%;">{t["lbl_reg_id"]}:</td>
                        <td style="padding:7px 0;font-weight:800;font-family:monospace;">#{record["id"]}</td>
                      </tr>
                      <tr>
                        <td style="padding:7px 0;color:#52608F;font-weight:600;">{t["lbl_name"]}:</td>
                        <td style="padding:7px 0;font-weight:800;">{record["name"]}</td>
                      </tr>
                      <tr>
                        <td style="padding:7px 0;color:#52608F;font-weight:600;">{t["lbl_phone"]}:</td>
                        <td style="padding:7px 0;font-weight:800;">{record["phone"]}</td>
                      </tr>
                      <tr>
                        <td style="padding:7px 0;color:#52608F;font-weight:600;">{t["lbl_email"]}:</td>
                        <td style="padding:7px 0;font-weight:800;">{record["email"]}</td>
                      </tr>
                      <tr>
                        <td style="padding:7px 0;color:#52608F;font-weight:600;">{t["lbl_course"]}:</td>
                        <td style="padding:7px 0;">
                          <span style="background-color:#1E45FC;color:#ffffff;font-weight:900;font-size:13px;padding:4px 12px;border-radius:99px;display:inline-block;">
                            {c_meta["name"]}
                          </span>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding:7px 0;color:#52608F;font-weight:600;">{t["lbl_duration"]}:</td>
                        <td style="padding:7px 0;font-weight:700;">{c_meta["duration"]}</td>
                      </tr>
                      <tr>
                        <td style="padding:7px 0;color:#52608F;font-weight:600;">{t["lbl_tools"]}:</td>
                        <td style="padding:7px 0;font-weight:700;color:#1E45FC;">{c_meta["tools"]}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <p style="margin:0 0 20px;font-size:14.5px;line-height:1.55;color:#2E3B70;text-align:center;">
                {t["cta_text"]}
              </p>

              <div style="text-align:center;margin-bottom:12px;">
                <a href="https://wa.link/9mwhgp" style="display:inline-block;background-color:#AEFF03;color:#0B1B5E;font-size:15px;font-weight:900;text-decoration:none;padding:15px 32px;border-radius:99px;letter-spacing:-0.01em;">
                  {t["cta_btn"]} &rarr;
                </a>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#EEF1F9;padding:22px 32px;text-align:center;border-top:1px solid rgba(11,27,94,0.08);">
              <p style="margin:0 0 6px;font-size:13.5px;font-weight:800;color:#0B1B5E;">
                +994 51 448 68 20 &nbsp;&bull;&nbsp; contact.gateacademy@gmail.com
              </p>
              <p style="margin:0;font-size:12px;color:#52608F;font-weight:600;">
                {t["footer"]}
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def save_registration(record):
    """Kaydı hem registrations.json hem registrations.csv dosyasına yazar."""
    records = []
    if os.path.exists(REG_JSON_PATH):
        try:
            with open(REG_JSON_PATH, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            records = []

    records.insert(0, record)
    with open(REG_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    file_exists = os.path.exists(REG_CSV_PATH)
    with open(REG_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["ID", "Tarih", "Ad Soyad", "Telefon", "E-posta", "Kurs", "Dil", "Mail Durumu"])
        writer.writerow([
            record["id"],
            record["created_at"],
            record["name"],
            record["phone"],
            record["email"],
            record["course_title"],
            record["lang"],
            record.get("mail_status", "saved"),
        ])


def send_registration_emails(record):
    """
    1. HTML e-postasını oluşturup sent_emails/ klasörüne kaydeder.
    2. .env içinde SMTP_USER ve SMTP_PASS tanımlıysa gerçek SMTP üzerinden kullanıcıya ve admine mail atar.
    """
    env = load_env()
    lang = record.get("lang", "az")
    if lang not in EMAIL_I18N:
        lang = "az"
    t = EMAIL_I18N[lang]

    html_body = build_email_html(record)
    email_filename = f"email_{record['id']}.html"
    email_filepath = os.path.join(SENT_EMAILS_DIR, email_filename)

    with open(email_filepath, "w", encoding="utf-8") as f:
        f.write(html_body)

    preview_url = f"/sent_emails/{email_filename}"

    smtp_user = env.get("SMTP_USER", "").strip()
    smtp_pass = env.get("SMTP_PASS", "").strip()
    smtp_host = env.get("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(env.get("SMTP_PORT", "587") or 587)
    sender_name = env.get("SENDER_NAME", "Gate Academy")
    admin_email = env.get("ADMIN_EMAIL", "contact.gateacademy@gmail.com").strip()

    if not smtp_user or not smtp_pass:
        return {
            "sent_via_smtp": False,
            "mode": "preview",
            "message": "Mail botu HTML e-postayı oluşturdu ve kaydetti (.env içine SMTP_USER ve SMTP_PASS girildiğinde gerçek e-posta kutusuna da iletilir).",
            "preview_url": preview_url,
        }

    try:
        # 1) Kullanıcıya onay maili
        msg = MIMEMultipart("alternative")
        msg["Subject"] = t["subject"]
        msg["From"] = formataddr((sender_name, smtp_user))
        msg["To"] = record["email"]
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # 2) Admin'e bildirim maili
        admin_msg = MIMEMultipart("alternative")
        admin_msg["Subject"] = f"[Yeni Kayıt #{record['id']}] {record['name']} - {record['course_title']}"
        admin_msg["From"] = formataddr((sender_name, smtp_user))
        admin_msg["To"] = admin_email
        admin_msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [record["email"]], msg.as_string())
            if admin_email:
                server.sendmail(smtp_user, [admin_email], admin_msg.as_string())

        return {
            "sent_via_smtp": True,
            "mode": "smtp",
            "message": f"Onay e-postası {record['email']} adresine başarıyla gönderildi!",
            "preview_url": preview_url,
        }
    except Exception as exc:
        return {
            "sent_via_smtp": False,
            "mode": "smtp_error",
            "error": str(exc),
            "message": f"SMTP hatası ({exc}), ancak e-posta önizlemesi oluşturuldu.",
            "preview_url": preview_url,
        }


class GateAcademyHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/registrations":
            records = []
            if os.path.exists(REG_JSON_PATH):
                try:
                    with open(REG_JSON_PATH, "r", encoding="utf-8") as f:
                        records = json.load(f)
                except Exception:
                    records = []
            payload = json.dumps({"ok": True, "count": len(records), "registrations": records}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/register":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(length).decode("utf-8")
                data = json.loads(raw_body) if raw_body else {}

                name = (data.get("name") or "").strip()
                phone = (data.get("phone") or "").strip()
                email = (data.get("email") or "").strip()
                course = (data.get("course") or "qrafik").strip().lower()
                lang = (data.get("lang") or "az").strip().lower()

                if not name or not phone or not email:
                    self._send_json(400, {"ok": False, "error": "Missing required fields (name, phone, email)."})
                    return

                if course not in COURSE_META:
                    course = "qrafik"
                if lang not in ("az", "tr", "en"):
                    lang = "az"

                reg_id = uuid.uuid4().hex[:8].upper()
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                course_title = COURSE_META[course][lang]["name"]

                record = {
                    "id": reg_id,
                    "created_at": now_str,
                    "name": name,
                    "phone": phone,
                    "email": email,
                    "course": course,
                    "course_title": course_title,
                    "lang": lang,
                }

                mail_result = send_registration_emails(record)
                record["mail_status"] = mail_result.get("mode", "saved")
                record["preview_url"] = mail_result.get("preview_url", "")

                save_registration(record)

                self._send_json(200, {
                    "ok": True,
                    "registration": record,
                    "mail": mail_result,
                })
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        self._send_json(404, {"ok": False, "error": "Not found"})

    def _send_json(self, status_code, obj):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    env = load_env()
    port = int(env.get("PORT", "3000") or 3000)
    server = ThreadingHTTPServer(("0.0.0.0", port), GateAcademyHandler)
    print(f"🚀 Gate Academy Server & Mail Bot running on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
