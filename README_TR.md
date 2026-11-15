# JobRadar v2.0 — macOS ve tamamen yerel LLM

Saatlik servis kaldırıldı. Uygulama yalnızca çağırdığınızda freehire, Himalayas, Jobicy ve etkinleştirilmiş resmi ATS panolarını sorgular. İlgi alanı dışındaki başlıkları ve lokasyonları elemek için ikinci bir filtre kullanır. Pano, kolon başına sıralama ve çoklu değer filtresi, şehir/ülke, kaynak tarihi ve kaynak tarihine göre yaş, isteğe bağlı local-seen ve CSV dışa aktarma içerir. LLM değerlendirmesi yalnızca **yerel Ollama** üzerinden yapılır. Kurulumdan sonra otomatik başvuru yapılmaz.

## 1. Eski sürümü önce kaldırın

Yeni ZIP dosyasını `Downloads` klasörüne kaydedin. Terminal:

```bash
cd ~/Downloads
unzip JobRadar_v2.0_macOS.zip
cd JobRadar_v2.0
./remove_v1.sh
```

Betik yalnızca `~/Downloads/JobRadar_v1.0` ve `~/Library/LaunchAgents/com.alihan.jobradar.hourly.plist` yollarını hedefler. `DELETE V1` onayı olmadan eski sürümü silmez. Eski SQLite veritabanı ve paketler de kaybolacaktır. İhtiyaç duyduğunuz geçmiş kayıtlarını **önceden ayrı yere yedekleyin**. v1 ZIP dosyasını da ayrıca silmeyi sorar. Bu sohbet Mac'inizdeki dosyaları doğrudan silemez.

## 2. v2'yi kurun

```bash
./installer.sh
```

Python 3.10+ gerekir; Python `venv` içine ücretsiz PDF/DOCX kütüphaneleri kurulur. Saatlik `launchd` görevi oluşturulmaz. Tam **v4.1 Full Edition** dosyası `prompts/ACTIVE.md` içinde yer alır. Yalnızca 6 kısmi başvuru geçmişi olayı başlangıçta yüklenir; tüm eski başvurularınızı kapsadığı anlamına gelmez.

## 3. Ücretsiz, yerel model

Ollama macOS uygulamasını `https://ollama.com/download` adresinden indirip açın. Sonra:

```bash
ollama pull qwen3:8b
./jr doctor
```

Model varsayılanı `qwen3:8b`. Ollama yerel API adresi `http://127.0.0.1:11434/api/chat`, bulut kullanımı `false` olarak yapılandırılmıştır. `./jr doctor` modelin varlığını ve Mac RAM'ini kontrol eder. **8 GB RAM, 8B + 32K bağlam için yetersiz kalabilir**; 16 GB üzerinde de kalite/hız garantisi yoktur. Tam prompt 63 KB olduğundan küçük modellerde bağlamın kesilmesi, düşük kalite, JSON hatası ve bellek sorunu olabilir. Gerçek bir ilanda doğrulayın. Dilerseniz `config.json` içindeki `llm.model` ve `num_ctx` değerlerini değiştirin. Ücretli LLM API anahtarı gerekli değildir.

## 4. Tek komutla manuel tarama

```bash
./jr run
./jr list
./jr report --open
```

`run`: çevrimiçi kaynakları bir kez tarar, SQLite kayıtlarını günceller, `output/dashboard.html` panosunu tarayıcıda açar. `report --open` yeniden ağ taraması yapmadan pano üretir.

**Pano:** Her kolon başlığından sıralama, `▾` ile Excel benzeri çoklu değer seçimi, genel arama, “yalnızca yeni tespit” anahtarı, teknik kolonlar (ID ve local first seen) ve seçilen kayıtları CSV dışa aktarma. Şehir ve ülke ayrıdır. `BASELINE` = ilk taramada bulundu; `DISCOVERED` = sonraki taramada ilk kez görüldü. Bunlar başvuru statüsü değildir. Yaş hesabı gerçek açık kaldığı süre değil, *kaynak tarihine göre takvim günü* farkıdır.

**Hedef roller:** Türkiye, KSA, UAE, Katar ve remote eligibility doğrulanması gereken uluslararası ilanlar. `config.json` içindeki `interest.include_any/exclude_any` ve `searches` değiştirilebilir. İngilizce ve Türkçe yönetici başlıklarıyla arama yapılır. ABD ile sınırlı remote ilanlar elenir; eligibility belirsiz remote ilanlar teyit gerektirir.

```bash
./jr watch-add 'VP Strategic Partnerships'
./jr watch-list
./jr watch-remove 'VP Strategic Partnerships'
```

## 5. İlan değerlendirme ve başvuru taslağı

```bash
./jr evaluate 'freehire:ILANIN-TAM-ID'
```

Tam ID'yi panoda “Teknik kolonlar” seçeneğinden veya `./jr list` komutundan alın. Önce asıl işveren ilanını açıp hâlâ açık ve konum olarak uygun olduğunu doğrulayın. `SKIP/CLARIFY` için paket üretilmez; `APPLY/APPLY TACTICAL` için *taslak* cover letter, CV, PDF, DOCX ve birleşik PDF üretilir. v4.1 master promptu aktif dosyadan bütün olarak okunur. Sonuç kalite kontrolü ve başvuru kararı kullanıcıya aittir; otomatik başvuru ve otomatik e-posta yoktur.

Eksik ilan açıklaması:

```bash
./jr jd 'freehire:ILANIN-TAM-ID' ~/Downloads/ilan.txt
```

LinkedIn dahil başka bir kaynaktan ilanın **URL ve metnini elle ekleme** (scraping yok):

```bash
./jr add-job --url 'https://firma.example/jobs/123' \
  --title 'Head of AI Transformation' --company 'Firma' \
  --location 'Istanbul, Türkiye' --jd-file ~/Downloads/ilan.txt
```

Gelecek prompt sürümünü kullanma:

```bash
./jr prompt-set ~/Downloads/Job_Application_Master_v4.2.md
./jr prompt
```

Eski aktif prompt SHA256 etiketiyle `prompts/archive` altına alınır. Başvuru geçmişi CSV: `./jr history-import /path/history.csv`. CSV kolonları: `company,title,location,requisition,url,status,date,notes`.

## Sınırlar

- Üçüncü taraf API'lerin tümü Mac üzerinde uçtan uca doğrulanmadı; bazıları kota veya bölgesel engelle yanıt verebilir. Bir kaynak hata verse bile diğerlerinin sonuçları korunur.
- macOS/Safari panosunun son görüntüsü, bu ortamda Chromium ekran görüntüsü denemesi zaman aşımına uğradığı için görsel olarak doğrulanamadı; üretilen HTML'nin JavaScript sözdizimi ve XSS güvenliği kontrol edildi.
- Yerel modelin v4.1 içindeki karar kalitesi güçlü bulut modelleriyle eşdeğer varsayılamaz. Factual claim audit, CV gerçekliği ve taslağın son görsel kontrolü zorunludur.
- Local-first, *offline job search* demek değildir: iş ilanı kaynaklarına internet bağlantısı gerekir. CV/prompt verisi sadece localhost Ollama'ya gönderilir.
- `FileVault` önerilir. SQLite ve taslak dosyalar Mac'te tutulur; başvuru geçmişi başka bir konuşmadan otomatik eşitlenmez.

## Test

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

Kaynak araştırması: `SOURCES_RESEARCH_TR.md`.
