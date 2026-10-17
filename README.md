# Goal Signals Iddaa Bot
### İddaa Oran Eşleştirme & Bülten Botu (GoalSignals.com.tr)

Canlı İddaa bültenindeki tüm maçları ve derin market oranlarını (İlk Yarı Skoru, Maç Skoru, Maç Sonucu, Alt/Üst, Karşılıklı Gol vb.) anlık olarak tarayan, 1, 2, 3 veya daha fazla seçeneği aynı maçta ya da bültende saniyeler içinde bulan yüksek hızlı analiz botu.

---

## 🚀 Öne Çıkan Özellikler

1. **2-3 ve Çoklu Seçenekli Arama Desteği:**
   - **🔗 "VE (Aynı Maçta Tümü)" Modu:** Belirlediğiniz 2 veya 3 farklı kriterin **AYNI MAÇTA** gerçekleşmesini arar (Örn: *İlk Yarı Skoru 0:0 @ 2.20* **VE** *Maç Sonucu 1 @ 1.80*). Kombine çarpan oranını da hesaplar.
   - **🔀 "VEYA (Herhangi Biri)" Modu:** Belirlediğiniz kriterlerden herhangi birine uyan tüm maçları tek listede getirir.

2. **Dış Bağlantılardan Arındırılmış Temiz Arayüz:**
   - Harici bahis sitelerine giden bağlantılar kaldırılmıştır; kendi platformunuza veya GoalSignals.com.tr'ye özel bağımsız bir analiz aracıdır.
   - Tek tıkla maç ve oran detaylarını kopyalama özelliği bulunur.

3. **PC'den Bağımsız 7/24 Bulut / Sunucu Çalışma Desteği:**
   - Dahili otomatik arka plan tarayıcısı (Auto-Refresh Daemon) her 15 dakikada bir bülteni otomatik olarak günceller.
   - Docker (`docker compose up -d`) ve Linux Systemd servis desteği hazırdır.

4. **GoalSignals.com.tr Tam Entegrasyonu:**
   - **CORS Destekli REST API:** GoalSignals web siteniz doğrudan `/api/search` uç noktasını çağırarak verileri JSON olarak alabilir.
   - **Subdomain veya Iframe:** `bilyoner.goalsignals.com.tr` olarak yayına alabilir veya panel içine kolayca gömebilirsiniz.

---

## 💻 Yerel Olarak Nasıl Çalıştırılır?

Klasör içindeki **`GoalSignals_Iddaa_Bot.bat`** dosyasına çift tıklayın veya terminalden:
```bash
python start.py
```
Tarayıcınızda otomatik olarak **`http://127.0.0.1:8000`** adresinde açılır.

---

## 🌐 7/24 Sunucu & GoalSignals.com.tr Kurulumu
Detaylı bulut kurulumu, Docker ve Nginx yönergeleri için [GOALSIGNALS_INTEGRATION.md](file:///C:/Users/Win10/.gemini/antigravity/scratch/bilyoner_bot/GOALSIGNALS_INTEGRATION.md) dosyasını inceleyebilirsiniz.
