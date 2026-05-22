from flask import Blueprint, jsonify, request, session
from models.database import get_db
from analytics.data_analysis import get_stats_overview
import json

api_bp = Blueprint('api', __name__)

@api_bp.route('/trips')
def get_trips():
    conn = get_db()
    trips = conn.execute('''
        SELECT t.*, u.name as driver_name FROM trips t
        JOIN users u ON t.driver_id=u.id WHERE t.status='active'
        AND t.departure_lat != 0 AND t.destination_lat != 0
    ''').fetchall()
    conn.close()
    return jsonify([dict(t) for t in trips])

@api_bp.route('/stats')
def stats():
    return jsonify(get_stats_overview())

@api_bp.route('/search')
def search():
    dep = request.args.get('departure','')
    dest = request.args.get('destination','')
    conn = get_db()
    trips = conn.execute('''
        SELECT t.*, u.name as driver_name FROM trips t
        JOIN users u ON t.driver_id=u.id
        WHERE t.status='active' AND t.departure LIKE ? AND t.destination LIKE ?
    ''', (f'%{dep}%', f'%{dest}%')).fetchall()
    conn.close()
    return jsonify([dict(t) for t in trips])

@api_bp.route('/notifications/read/<int:notif_id>', methods=['POST'])
def mark_read(notif_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?",
                 (notif_id, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@api_bp.route('/ai-chat', methods=['POST'])
def ai_chat():
    from flask import jsonify, request as req
    data = req.get_json()
    user_message = data.get('message', '')
    history = data.get('history', [])

    system_prompt = """Sen YolPayı'nın akıllı asistanısın. YolPayı, Gümüşhane merkezli bir paylaşımlı ulaşım (carpooling) platformudur.

Platform hakkında bilmen gerekenler:
- Kullanıcılar sürücü veya yolcu olarak kayıt olabilir
- Sürücüler yolculuk oluşturur, yolcular rezervasyon yapar
- Harita üzerinde yolculuklar görüntülenebilir
- Sistem CO₂ tasarrufu hesaplar
- Dijkstra algoritması ile rota optimizasyonu yapılır
- Admin, Sürücü, Yolcu ve Kent Yöneticisi rolleri vardır
- Kayıt: /auth/register, Giriş: /auth/login, Arama: /search

Türkçe yanıt ver. Kısa, net ve yardımcı ol. Emoji kullanabilirsin."""

    messages = []
    for h in history[:-1]:  # exclude last (current) message
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        import urllib.request
        import json as json_lib

        payload = json_lib.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 400,
            "system": system_prompt,
            "messages": messages
        }).encode('utf-8')

        req_obj = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'anthropic-version': '2023-06-01',
                'x-api-key': 'YOUR_API_KEY_HERE'
            },
            method='POST'
        )

        with urllib.request.urlopen(req_obj, timeout=15) as response:
            result = json_lib.loads(response.read())
            reply = result['content'][0]['text']

    except Exception as e:
        # Fallback: rule-based responses without API
        reply = get_rule_based_reply(user_message)

    return jsonify({'reply': reply})


def get_rule_based_reply(msg):
    msg = msg.lower()
    if any(w in msg for w in ['yolculuk', 'nasıl bul', 'ara', 'search']):
        return "🔍 Yolculuk bulmak için Ana Sayfa'daki arama kutusunu kullanabilirsin! Kalkış noktası, varış noktası ve tarihi girerek uygun yolculukları görebilirsin."
    elif any(w in msg for w in ['rezervasyon', 'rezerve', 'iptal']):
        return "📋 Rezervasyonlarını Dashboard > Mes Réservations bölümünden görebilirsin. İptal etmek için 'İptal' butonuna tıkla. Sürücü henüz onaylamamışsa iptal edebilirsin."
    elif any(w in msg for w in ['fiyat', 'ücret', 'para', 'kaç']):
        return "💰 Fiyatlar sürücü tarafından belirlenir. Yolculuk kartında kişi başı ücret gösterilir. Paylaşımlı yolculukla hem sen hem sürücü tasarruf eder!"
    elif any(w in msg for w in ['co2', 'karbon', 'çevre', 'ekoloji']):
        return "🌱 Her paylaşımlı yolculukta yaklaşık 2.3 kg CO₂ tasarrufu sağlanır. Dashboard'unda toplam katkını görebilirsin!"
    elif any(w in msg for w in ['kayıt', 'üye', 'hesap', 'register']):
        return "👤 Kayıt olmak için sağ üstteki 'Kayıt Ol' butonuna tıkla! Sürücü veya Yolcu olarak kaydolabilirsin. Tamamen ücretsiz!"
    elif any(w in msg for w in ['harita', 'map', 'nerede']):
        return "🗺️ Canlı haritayı üst menüden 'Carte' seçeneğiyle açabilirsin. Tüm aktif yolculuklar harita üzerinde görüntülenir!"
    elif any(w in msg for w in ['sürücü', 'yolculuk ekle', 'oluştur']):
        return "🚗 Sürücü olarak yolculuk eklemek için önce Sürücü rolüyle kayıt ol, ardından Dashboard > 'Yolculuk Ekle' seçeneğini kullan."
    elif any(w in msg for w in ['merhaba', 'selam', 'hello', 'hi', 'bonjour']):
        return "👋 Merhaba! YolPayı asistanına hoş geldin! Yolculuk bulmak, rezervasyon veya platform hakkında her konuda yardımcı olabilirim. Ne öğrenmek istersin?"
    elif any(w in msg for w in ['teşekkür', 'sağol', 'merci', 'thanks']):
        return "😊 Rica ederim! Başka bir sorun olursa buradayım. İyi yolculuklar! 🚗"
    else:
        return "🤔 Bu konuda sana şunu söyleyebilirim: YolPayı'da yolculuk aramak, rezervasyon yapmak veya sürücü olarak yolculuk eklemek için üst menüyü kullanabilirsin. Daha spesifik bir soru sormak ister misin?"
