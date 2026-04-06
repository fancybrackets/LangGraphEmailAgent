# LangGraph Email Agent (Local, Privacy-First)

Bu proje, **tamamen lokal calisan** bir LangGraph tabanli e-posta asistani ve sohbet arayuzudur.
FastAPI backend, Ollama modelleri, IMAP e-posta araclari ve web UI birlikte calisir.

## Proje Ozeti

Sistem iki ana ihtiyaci cozer:

1. Lokal LLM ile sohbet ve arac kullanan agent akisi
2. E-posta kutusu uzerinde operasyonel otomasyon (listeleme, ozetleme, attachment islemleri, taslak olusturma)

Araclar LangGraph icinde tool-calling ile kullanilir. Sohbetler thread mantiginda tutulur ve arayuzde ayrik oturumlar olarak yonetilir.

## Baslica Ozellikler

- Lokal ve privacy-first calisma (Ollama + yerel servis)
- Sol panelde coklu sohbet oturumu ve otomatik sohbet basliklari
- Agent tarafinda LangGraph + MemorySaver ile thread bazli baglam
- IMAP araclari ile okunmamis mailleri listeleme
- IMAP araclari ile UID bazli mail ozetleme
- IMAP araclari ile aksiyon maddesi ve deadline benzeri kaliplari cikarma
- IMAP araclari ile ek dosya listesi alma
- IMAP araclari ile konuya gore mail metadata export etme
- IMAP araclari ile konuya gore attachment kaydetme
- IMAP araclari ile kullanici stiline yakin e-posta taslagi olusturma
- Model Settings ekraninda katalogdan model indirme
- Model Settings ekraninda kurulu modeli silme
- Model Settings ekraninda aktif modeli degistirme
- Benchmark modulu ile coklu model karsilastirmasi
- Benchmark modulu ile CSV ozetleri ve Markdown/HTML rapor uretimi

## Mimari

- `app/main.py`: FastAPI girisi, UI route'lari ve API router kaydi
- `app/agent/graph.py`: LangGraph is akisi (agent -> tools -> agent)
- `app/agent/tool_registry.py`: Agent arac katalogu
- `app/agent/tools/email_tools.py`: IMAP tabanli email tool'lari
- `app/services/ollama_service.py`: Ollama model yonetimi ve katalog dogrulamasi
- `app/web/*`: Chat ve model ayarlari frontend'i
- `bench/*`: Benchmark ve raporlama scriptleri

## Gereksinimler

- Python 3.10+
- [Ollama](https://ollama.com/) kurulu ve calisiyor olmasi
- IMAP destekli bir e-posta hesabi (email araclarini kullanacaksan)

## Kurulum

```bash
cd LocalAgentDissertation
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` dosyasini kendi bilgilerinizle duzenleyin.

## Ortam Degiskenleri

| Degisken | Aciklama | Varsayilan |
|---|---|---|
| `APP_NAME` | API basligi | `Step 13 Model Panel API` |
| `PRIVACY_MODE` | `/health` icinde privacy modu bilgisi | `true` |
| `OLLAMA_BASE_URL` | Ollama taban URL | `http://127.0.0.1:11434` |
| `DEFAULT_MODEL` | Varsayilan model | `qwen2.5:7b` |
| `IMAP_HOST` | IMAP sunucu host'u | bos |
| `IMAP_USER` | IMAP kullanici | bos |
| `IMAP_PASSWORD` | IMAP sifre/app password | bos |
| `IMAP_FOLDER` | Okuma klasoru | `INBOX` |
| `IMAP_SENT_FOLDER` | Giden klasoru (stil analizi) | `Sent` |

## Calistirma

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8013 --env-file .env
```

Arayuz ve dokuman:

- Chat UI: `http://127.0.0.1:8013/`
- Model Settings: `http://127.0.0.1:8013/settings`
- Swagger: `http://127.0.0.1:8013/docs`

## API Uclari

- `GET /health`
- `GET /tools`
- `POST /chat`
- `GET /models/catalog`
- `GET /models`
- `POST /models/pull` (yalniz katalogdaki modeller)
- `POST /models/delete`
- `GET /models/active`
- `POST /models/active`

## Ornek Kullanim Akisi

1. `/settings` ekraninda katalogdan bir model indirin.
2. Indirdiginiz modeli aktif hale getirin.
3. `/` ekranina donup yeni sohbet olusturun.
4. Agent'a mail odakli prompt verin. Ornekler: `Son 5 okunmamis maili listele`, `UID 1234 mailini ozetle`, `Konu: invoice olan maillerin eklerini kaydet`.

## Benchmark ve Raporlama

Benchmark scripti, uygun modeller icin `/chat` endpoint'ine test istekleri atar ve su metrikleri toplar:

- latency
- success/error rate
- yaklasik RAM/CPU kullanim ortalamasi

Calistirma:

```bash
source .venv/bin/activate
python bench/run_benchmark.py
python bench/generate_report.py
```

Uretilen dosyalar:

- `bench/results.csv`
- `bench/summary.csv`
- `bench/report.md`
- `bench/report.html`

## Gizlilik Notu

Bu proje lokal calisma odaklidir; yine de IMAP araclari gercek e-posta verisiyle calisacagi icin:

- `.env` dosyasini kesinlikle repoya eklemeyin
- app password kullanin (hesap ana sifresi yerine)
- export dosyalarini (`email_exports/` benzeri klasorler) paylasmadan once kontrol edin

## Lisans

Bu depoda lisans dosyasi bulunmuyor. Acik kaynak dagitim planlaniyorsa uygun bir `LICENSE` eklenmesi onerilir.
