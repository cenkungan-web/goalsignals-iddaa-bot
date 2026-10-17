# GoalSignals.com.tr Entegrasyon ve 7/24 Bulut Kurulum Kılavuzu

Bu doküman, Bilyoner Çoklu Oran Botu'nun bilgisayarınız kapalıyken bile **7/24 kesintisiz çalışması** ve **GoalSignals.com.tr** platformuna entegre edilmesi için hazırlanmıştır.

---

## 1. 2-3 Seçenekli (Çoklu Kriter) Arama Nasıl Çalışır?

Arayüzde **"+ Yeni Oran Kriteri Ekle"** butonuna basarak dilediğiniz kadar (2, 3 veya daha fazla) oran kriteri belirleyebilirsiniz:

### 🔗 "VE (Aynı Maçta Tümü)" Modu:
- **Ne yapar?** Belirlediğiniz 2-3 kriterin **AYNI MAÇ İÇİNDE** birlikte gerçekleşmesini arar.
- **Örnek:** 
  - Kriter 1: `İlk Yarı Skoru: 0:0` @ `2.20`
  - Kriter 2: `Maç Sonucu: MS 1` @ `1.80`
- **Sonuç:** Sadece ilk yarısı 0-0 oranı ~2.20 olan VE maç sonu 1 oranı ~1.80 olan özel maçları getirir. Ayrıca kart üzerinde **Kombine Çarpan Oranını (örn. 3.96)** hesaplar.

### 🔀 "VEYA (Herhangi Biri)" Modu:
- **Ne yapar?** Belirlediğiniz kriterlerden **herhangi birine** uyan tüm maçları tek bir havuzda toplar.

---

## 2. PC'den Bağımsız 7/24 Çalıştırma (Sunucu / VPS)

Botun bilgisayarınız kapalıyken de sürekli çalışması için bir Linux VPS sunucusunda (DigitalOcean, Hetzner, AWS, Contabo vb.) 2 farklı yöntemle çalıştırabilirsiniz:

### Yöntem A: Docker ile 1 Dakikada Başlatma (Tavsiye Edilen)

Sunucunuza dosyaları yükledikten sonra:
```bash
# Klasöre gidin
cd bilyoner_bot

# Arka planda 7/24 çalışacak şekilde başlatın
docker compose up -d --build
```
> Bot otomatik olarak `http://SUNUCU_IP:8000` portunda çalışacak ve her 15 dakikada bir Bilyoner bültenini arka planda otomatik yenileyecektir.

### Yöntem B: Linux Systemd Servisi ile Başlatma

```bash
# Bağımlılıkları kurun
pip install -r requirements.txt

# Servis dosyasını kopyalayın
sudo cp bilyoner-bot.service /etc/systemd/system/

# Servisi etkinleştirip başlatın
sudo systemctl daemon-reload
sudo systemctl enable bilyoner-bot
sudo systemctl start bilyoner-bot

# Durumu kontrol edin
sudo systemctl status bilyoner-bot
```

---

## 3. GoalSignals.com.tr Entegrasyon Yöntemleri

### Seçenek 1: Subdomain ile Yayınlama (En Hızlı ve Profesyonel)
Botu `bilyoner.goalsignals.com.tr` veya `bot.goalsignals.com.tr` üzerinde çalıştırabilirsiniz.
1. DNS yönetiminizden `bilyoner.goalsignals.com.tr` A kaydını sunucu IP'nize yönlendirin.
2. Klasördeki `nginx.conf` dosyasını `/etc/nginx/sites-available/bilyoner` olarak kaydedin.
3. Ücretsiz SSL sertifikası alın:
   ```bash
   sudo certbot --nginx -d bilyoner.goalsignals.com.tr
   ```

### Seçenek 2: GoalSignals.com.tr İçine Sayfa / Iframe Olarak Gömme
GoalSignals panelinde yeni bir menü / sekme açıp:
```html
<iframe 
  src="https://bilyoner.goalsignals.com.tr" 
  width="100%" 
  height="900px" 
  frameborder="0" 
  style="border-radius: 16px; border: 1px solid #1e293b;">
</iframe>
```

### Seçenek 3: Doğrudan GoalSignals Backend/Frontend REST API Entegrasyonu
Bot üzerinde **CORS desteği aktiftir**. GoalSignals arayüzünüzden doğrudan JSON isteği atabilirsiniz:

**API İsteği Örneği (JavaScript fetch):**
```javascript
const response = await fetch("https://bilyoner.goalsignals.com.tr/api/search", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    match_mode: "AND", // "AND" veya "OR"
    criteria: [
      {
        market: "İlk Yarı Skoru",
        selection: "0:0",
        target_odd: 2.20,
        tolerance: 0.05
      },
      {
        market: "Maç Sonucu",
        selection: "MS 1",
        target_odd: 1.80,
        tolerance: 0.10
      }
    ]
  })
});

const data = await response.json();
console.log(`Bulunan maç sayısı: ${data.count}`);
console.log(data.results);
```
