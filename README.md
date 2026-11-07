# PWA
App "search PWA" per verificare esistenza di opzione PWA di qualsiasi webpage. Può essere usata anche come estensione di ogni browser.
# PWA Detector API & Security Engine 🛡️

**Il primo microservizio e motore di ricerca in tempo reale concepito per individuare ed evidenziare l'esistenza di versioni PWA (Progressive Web App) all'interno di qualsiasi pagina web.**

Questo progetto nasce da un'intuizione innovativa volta a colmare una carenza dei tradizionali motori di ricerca, che indicizzano i siti senza mapparne l'architettura applicativa avanzata. L'architettura esegue una scansione strutturale a tre livelli sul codice sorgente di un dominio, restituendo un verdetto binario (`true/false`) unito a una checklist tecnica dettagliata. Rappresenta uno strumento cruciale per l'analisi tecnica, la catalogazione pubblica e la difesa dei consumatori contro il phishing e i siti Web cloni.

---

## 🏗️ Architettura Completa del Sistema

Il sistema è stato ingegnerizzato seguendo i più rigorosi standard enterprise, segmentato in quattro livelli indipendenti e protetti:
[ FRONT-END CLIENT ]  ──( Chiamata HTTPS )──► [ NGINX REVERSE PROXY ]
│ (Porta 443 -> 8000)
▼
[ SYSTEMD SERVICE ]   ◄──( Auto-Restart )─── [ UVICORN / FASTAPI ENGINE ]

