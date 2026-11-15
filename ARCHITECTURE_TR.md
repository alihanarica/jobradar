# JobRadar v2.0 Architecture — manual, local-first

## Akış

Kullanıcının `./jr run` komutu → freehire HTTP API + Himalayas + Jobicy + yapılandırılmış ATS board'ları → normalize edilmiş alanlar → kesin pozisyon başlığı filtresi → ülke/remote eligibility kontrolü → SQLite ilk görülme / değişiklik geçmişi → yerel `output/dashboard.html`.

Dashboard: çevrimdışı statik HTML; her kolonda çoklu checkbox değer filtresi, alfabetik/nümerik sıralama, arama, farklı şehir/ülke alanları, kaynak ilan yaşı, durum ve isteğe bağlı teknik alanlar, CSV dışa aktarımı. Veri HTML içine güvenli JSON olarak gömülür; ilan metninden gelen HTML betik olarak çalıştırılmaz.

`./jr evaluate JOBID` → v4.1 Full Edition `prompts/ACTIVE.md` + saklanan ilan açıklaması + kısmi başvuru geçmişi → insan-onayı gerektiren karar → sadece localhost Ollama → JSON değerlendirme → `SKIP/CLARIFY` ise dosya hazırlanmaz; APPLY türleri için cover-letter-first DOCX/PDF + combined PDF + QA ve hash manifest.

## Güvenlik ve kontrol

- Hiçbir arka plan görevi kurulmaz. `remove_v1.sh` eski launchd görevini ve v1 klasörünü yazılı teyitten sonra kaldırır.
- Job discovery internet bağlantısı kullanır; kişisel prompt ve CV kanıtı Ollama ile sadece loopback adrese gönderilir.
- LinkedIn otomatik çekilmez. `./jr add-job` kullanıcı tarafından girilmiş başlık, şirket, link, konum ve isteğe bağlı tam JD metnini saklar.
- Kaynaktaki herhangi bir URL talimat değil, yalnızca veri kabul edilir. Resmi başvurunun açık olduğu otomatik garantisi yoktur.
- `status` veritabanında keşif ve başvuru aşamasını bir arada tutar: BASELINE/ DISCOVERED keşif semantiğidir; PREPARED ONLY/ SUBMITTED CONFIRMED başvuru yaşam döngüsü değerleridir. Gelecekte ayrı alanlara ayrılmalıdır.
- Geçmiş CSV'si kısmi olabilir. İşlem öncesi resmi requisition ve eski başvuru kontrolü gerekir.

## v2.1 teknik öncelikler

1. Resmi ATS URL ve requisition ID üzerinden çapraz kaynak duplicate cluster.
2. Gönderildi/ret/aktif başvuru yönetimi için uygulama içi kullanıcı eylemleri.
3. İlanın canlılık durumu, çalışma izni/sponsorluğu ve maaş kapsamının işveren düzeyinde teyidi.
4. Yerel LLM'i iki faza bölme: evidence mapping ve employer-facing package; JSON doğruluk, çok-aşamalı test ve otomatik eksik iddia kontrolü.
5. Safari UI ekran görüntüsü testi, mobil kolon seçimi, kalıcı filtre profilleri.

## Kod konumları

`jobradar/core.py`: SQLite, tarama, geçmiş statüsü, CLI core fonksiyonları.

`jobradar/v2_support.py`: ülke başlıkları/locale elemesi, Himalayas ve Jobicy adaptörleri.

`jobradar/sources.py`: freehire ve şirket bazlı Greenhouse/Lever/Ashby adaptörleri.

`jobradar/dashboard_v2.py`: offline HTML dashboard oluşturucu.

`jobradar/generator.py`, `render.py`: yerel Ollama karar ve PDF/DOCX taslakları.

`jobradar/doctor.py`: Ollama ve Mac bellek kontrolü.

Kaynak araştırması, ek sınırlar ve kurulum adımları: `SOURCES_RESEARCH_TR.md`, `README_TR.md`.
