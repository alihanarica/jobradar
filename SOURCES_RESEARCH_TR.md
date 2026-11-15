# İş ilanı kaynakları — araştırma özeti (18 Ekim 2026)

Tek ücretsiz veri sağlayıcı Türkiye + Suudi Arabistan + BAE + Katar'daki yönetici ilanlarının tam kapsamasını garanti etmiyor. En güvenilir yol: **resmi işveren ATS sayfaları + freehire + ülke eligibility içeren remote API + manuel teyit**.

| Kaynak | Mevcut kullanım | Güçlü yan | Risk / kısıt |
|---|---|---|---|
| [freehire](https://freehire.me/docs/api) | Entegre, açık | 225 kaynak, ATS tabanlı küresel katalog, title ve coğrafya filtreleri | Türkiye/MENA kapsama tam değil; tarih işveren sisteminde değişebilir |
| [Himalayas](https://himalayas.app/api) | Entegre, açık | Anahtarsız remote arama; `locationRestrictions`, `pubDate`, `applicationLink`; günlük güncelleme | Sadece remote, ülke ve saat dilimi uygunluğunu doğrulamak gerekir; ortak kota |
| [Jobicy](https://github.com/Jobicy/remote-jobs-api) | Entegre, açık | Anahtarsız remote feed, son 7 gün, açıklama ve `jobGeo` | Ücretsiz URL genellikle Jobicy ilanına yönlendirir, işveren URL'si eksik olabilir |
| [Greenhouse](https://docs.greenhouse.io/job-board) | Belirli board etkinleştirilirse | Şirketin yayımladığı ilanlar, tam açıklama | Board token gerekir; `updated_at` ilk yayın değildir |
| [Lever](https://github.com/lever/postings-api) | Belirli board etkinleştirilirse | Şirketin yayımladığı pozisyonlar | Board slug gerekir; genel pazar araması sunmaz |
| [Ashby](https://developers.ashbyhq.com/docs/public-job-posting-api) | Belirli board etkinleştirilirse | Kamuya açık ilanlar, bazen ücret | Board tanımlama ve coğrafi yetki kontrolü |
| [JobSpy](https://github.com/speedyapply/JobSpy) | **Varsayılan taramadan kaldırıldı** | LinkedIn, Indeed, Bayt vb. üzerinde geniş keşif | Platform kuralları, bot kısıtları, CAPTCHA, sahte/eskimiş ilan |
| [LinkedIn](https://www.linkedin.com/help/linkedin/answer/a1341387/prohibition-of-scraping-software?lang=en-us) | Manuel URL/JD import | Türkiye ve Körfez kıdemli roller | Scraping/otomasyon LinkedIn şartlarında yasak; resmi ilanın linki esas alınmalı |
| [Adzuna](https://developer.adzuna.com/overview) | İleride opsiyon | Birden çok pazarda arama/ücret | API app_id/key, [kota ve şartlar](https://developer.adzuna.com/docs/terms_of_service) |
| [Remotive](https://remotive.com/remote-jobs/api) | İleride opsiyon | Remote API, RSS | ~24 saat gecikme, atıf ve hız kısıtları |
| Workday / iCIMS / SmartRecruiters | freehire veya şirkete özel | Büyük işletmelerin doğrudan ilanları | Her şirket/tenant için tek standart API olmayabilir |
| Kariyer.net / İŞKUR / SecretCV | Manuel/e-posta alarmı | Türkiye'de yerel yönetici pozisyonları | Genel ücretsiz ve izinli API teyit edilmeden scraping eklenmemeli |
| Bayt / GulfTalent / Naukrigulf | Manuel/e-posta alarmı | Körfez ülke-spesifik roller | Serbest API ve otomatik erişim hakkı doğrulanmalı |

**Öncelik:** Türkiye bankalar/holdingler/telekom; Saudi Riyadh ve Jeddah teknoloji, dijital dönüşüm; UAE Dubai/Abu Dhabi commercial + transformation; Qatar Doha strateji ve general management. Bu şirketleri ATS board listesine güvenilir kaynak URL'siyle eklemek, daha fazla genel scraper eklemekten daha değerli.

**Arama sinyalleri:** Rol başlığı (TR/EN), işveren grubu, lokasyon, gerçekten remote-eligible ülke listesi, kıdem, sponsor gereksinimi, başvuru geçmişi, son resmi teyit, duplicate requisition, kaynak yayım tarihi. `first seen` ile `source posted at` ayrı saklanmalıdır. Kaynakların ilan hacmi, bunların hiçbirini otomatik kanıtlamaz.

**Önerilen sonraki geliştirmeler:** (1) Resmi URL ve requisition düzeyinde çapraz kaynak dedupe, (2) ilan canlılık teyidi, (3) işe alım ve çalışma izni şartlarının netleştirilmesi, (4) rol bazlı üç gerçek kanıtın eşleştirilmesi ve kırmızı bayrak, (5) kaydedilmiş pano filtreleri/shortlist, (6) iki aşamalı yerel LLM ve insan QA.
