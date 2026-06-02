# YolPayı  — Akıllı Paylaşımlı Ulaşım Platformu

**Gümüşhane merkezli modern carpooling platformu**

## Kurulum

```bash
# 1. Sanal ortam oluştur
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Bağımlılıkları yükle
pip install -r requirements.txt

# 3. Uygulamayı başlat
python app.py
```

Tarayıcıda aç: **http://localhost:5000**

## Demo Hesaplar

| Rol | E-posta | Şifre |
| Admin | admin@yolpayi.com | admin123 |
| Sürücü | driver@yolpayi.com | driver123 |
| Kent Yöneticisi | urban@yolpayi.com | urban123 |

## Teknolojiler

- **Backend**: Python 3 + Flask + SQLite3
- **Frontend**: HTML5 + CSS3 + Vanilla JS
- **Harita**: Leaflet.js + OpenStreetMap (CartoDB Dark)
- **Analitik**: Pandas + NetworkX (Dijkstra)
- **Güvenlik**: hashlib SHA-256

## Proje Yapısı

```
YolPayi/
├── app.py              # Flask uygulaması
├── models/database.py  # SQLite veritabanı
├── routes/             # Blueprint rotaları
├── analytics/          # Veri analizi
├── ai/                 # Öneri sistemi
├── templates/          # HTML şablonları
└── static/             # CSS + JS
```

## Roller

- **Admin** — Tam yönetim yetkisi
- **Sürücü** — Yolculuk oluştur ve yönet
- **Yolcu** — Yolculuk bul ve rezerve et
- **Kent Yöneticisi** — Mobilite analizi

