# Step 13: Model Panel + Chat Sidebar

Bu adimda web arayuzune 3 yeni ozellik ekliyoruz:

1. Model yonetimini ayri `/settings` sayfasina tasima
2. `save_emails_by_topic` ciktilarini klasor yapisinda saklama
3. Solda ayri sohbetler paneli ve sohbet basliklari

## Hedef

- `/settings` sayfasinda katalogdan model indir/sil/aktif et akisini calistirmak
- Ayri sohbetler olusturup soldaki listede basliklarini gostermek
- `save_emails_by_topic` sonucunu `topic/tarih/saat` klasorlerinde saklamak

## Bu adimda olan endpoint/arayuz

1. `GET /` (web arayuz)
2. `GET /settings` (model settings)
3. `GET /health`
4. `GET /models/catalog`
5. `GET /models`
6. `POST /models/pull` (sadece katalog modeli)
7. `POST /models/delete`
8. `GET /models/active`
9. `POST /models/active`
10. `GET /tools`
11. `POST /chat`

## Kurulum

```bash
cd LocalAgentDissertation
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8013 --env-file .env
```

## Test

- Web app: `http://127.0.0.1:8013/`
- Settings: `http://127.0.0.1:8013/settings`
- Swagger: `http://127.0.0.1:8013/docs`

## Benchmark

`bench/run_benchmark.py` scripti, katalogdaki modelleri (otomatik) dener ve
`qwen2.5:7b` modelini otomatik olarak disarida birakir.

```bash
cd LocalAgentDissertation
source .venv/bin/activate
python bench/run_benchmark.py
```

Sonuclar:

- Detayli satirlar: `bench/results.csv`
- Ozet tablo: `bench/summary.csv`

Rapor (tablo + grafik):

```bash
python bench/generate_report.py
```

Uretilen dosyalar:

- Markdown tablo raporu: `bench/report.md`
- HTML grafik raporu: `bench/report.html`

## Neyi anlamalisin?

1. `app/web/index.html` chat odakli sayfa (sol sohbet paneli + mesaj alani)
2. `app/web/settings.html` model yonetim sayfasi (katalogdan indir/sil/aktif et)
3. `app/web/settings.js` model API akisi ve katalog bazli indirme
4. `app/services/ollama_service.py` katalog dogrulamasi + aktif model/state
5. `app/agent/tools/email_tools.py` topic/tarih/saat klasor yapisi ile email export
