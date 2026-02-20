# 🕌 VakitHub - Home Assistant Entegrasyonu

<p align="center">
  <img src="custom_components/ramazan/icon.png" alt="VakitHub Logo" width="128" height="128">
</p>

Diyanet İşleri Başkanlığı'nın API'sini kullanarak namaz vakitlerini, iftar/sahur saatlerini ve geri sayım sayaçlarını Home Assistant'a getiren özel entegrasyon.

## ✨ Özellikler

### Namaz Vakitleri Sensörleri
| Sensör | Açıklama |
|--------|----------|
| 🌅 İmsak | İmsak vakti |
| ☀️ Güneş | Güneş doğuşu |
| 🕐 Öğle | Öğle namazı |
| 🕑 İkindi | İkindi namazı |
| 🌇 Akşam | Akşam namazı |
| 🌙 Yatsı | Yatsı namazı |

### İftar & Sahur
| Sensör | Açıklama |
|--------|----------|
| 🍽️ İftar | İftar vakti (Akşam namazı) |
| 🍽️ Sahur | Sahur vakti (İmsak) |
| ⏳ İftara Kalan Süre | Geri sayım (saat/dakika/saniye) |
| ⏳ Sahura Kalan Süre | Geri sayım (saat/dakika/saniye) |

### Ek Bilgiler
| Sensör | Açıklama |
|--------|----------|
| 🧭 Kıble Saati | Güneşin kıble yönünde olduğu saat |
| 📅 Hicri Tarih | Hicri takvim tarihi |
| 📅 Miladi Tarih | Miladi takvim tarihi |
| 🌅 Astronomik Gün Doğumu | Astronomik gün doğumu |
| 🌇 Astronomik Gün Batımı | Astronomik gün batımı |
| 🌙 Ay Evresi | Ay'ın mevcut evresi |
| 🕰️ İftar Zamanı | Otomasyon için zaman damgası |
| 🕰️ Sahur Zamanı | Otomasyon için zaman damgası |

## 📦 Kurulum

### HACS ile (Önerilen)
1. HACS'ı açın
2. **Entegrasyonlar** bölümüne gidin
3. Sağ üst köşeden **⋮** menüsüne tıklayın → **Özel depolar**
4. URL: `https://github.com/ahamitd/ramazan` ekleyin
5. Kategori: **Entegrasyon** seçin
6. **VakitHub** entegrasyonunu bulun ve yükleyin
7. Home Assistant'ı yeniden başlatın

### Manuel Kurulum
1. Bu depoyu indirin
2. `custom_components/ramazan` klasörünü Home Assistant'ınızın `custom_components` dizinine kopyalayın
3. Home Assistant'ı yeniden başlatın

## ⚙️ Yapılandırma

1. **Ayarlar** → **Cihazlar ve Hizmetler** → **Entegrasyon Ekle**
2. **VakitHub** arayın
3. **Ülke** seçin (örn: Türkiye)
4. **İl** seçin (örn: İstanbul)
5. **İlçe** seçin (örn: Kadıköy)

## 🛡️ Dayanıklılık

VakitHub, Diyanet API'si geçici olarak erişilemez olduğunda da çalışmaya devam eder:

- **Otomatik yeniden deneme:** API bağlantı hatası entegrasyonu durdurmaz; arka planda her 6 saatte bir yeniden denenir.
- **Önbellek:** Son başarılı API yanıtı saklanır; API erişilemez olduğunda sensörler bu verilerle çalışmaya devam eder.
- **Zaman aşımı:** HTTP istekleri 15 saniye sonra otomatik olarak zaman aşımına uğrar, Home Assistant'ın donmasını önler.

## 🤖 Otomasyon Örneği

Namaz vakitlerinde (İftar/Sahur vb.) otomasyon çalıştırmak için sensörlerin `vakit_timestamp` özelliğini kullanın:

```yaml
alias: "İftar Bildirimi"
trigger:
  - platform: time
    at: sensor.ramazan_iftar_time
```

*Not: `vakit_timestamp` özelliği tam bir zaman damgası içerir ve otomasyon tetikleyicileri ile uyumludur.*

## 📡 Veri Kaynağı

Veriler [T.C. Diyanet İşleri Başkanlığı](https://www.diyanet.gov.tr/) tarafından sağlanmaktadır.

## 📝 Lisans

MIT License
