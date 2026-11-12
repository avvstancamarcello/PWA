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
1. **Front-End Client (JavaScript Fetch):** Pannello di controllo interattivo integrabile in qualsiasi form o motore di ricerca che mostra visivamente il verdetto (Scudo Verde per PWA valida, Pallino Rosso per Sito Standard).
2. **Reverse Proxy (Nginx + SSL):** Punto di accesso pubblico che gestisce i certificati di crittografia e dirotta in modo sicuro le richieste.
3. **Application Engine (FastAPI + Uvicorn):** Il cuore pulsante dell'algoritmo scritto in Python, ottimizzato con multi-worker per gestire flussi massivi di scansioni simultanee.
4. **Permanent Daemon (Systemd):** Servizio Linux di background che garantisce la persistenza del processo, l'avvio automatico al boot del server e l'auto-restart in caso di crash.

---

## 🔍 Analisi Comparativa e Ambito del Progetto

Il **PWA Detector Engine** offre un controllo remoto e automatizzabile di alcuni elementi strutturali associati alle PWA. Si affianca agli strumenti per sviluppatori e ai servizi di analisi o creazione PWA, che rispondono a esigenze diverse; non intende sostituirli né certificare che un sito sia sicuro o installabile in ogni browser.

### 📊 Confronto orientativo

| Aspetto | DevTools del browser | PWABuilder | Lighthouse | PWA Detector Engine |
| :--- | :--- | :--- | :--- | :--- |
| **Uso tipico** | Ispezione e debug manuale durante lo sviluppo. | Analisi e strumenti per creare o distribuire PWA. | Audit automatici di pagine web, incluse verifiche PWA. | Verifica remota via API della presenza e validità di alcuni elementi PWA. |
| **Modalità** | Interattiva, nel browser dello sviluppatore. | Servizio web e strumenti di sviluppo. | Audit avviato tramite strumenti compatibili. | Endpoint HTTP utilizzabile da un client o da un'integrazione. |
| **Controlli del progetto** | Dipendono dagli strumenti del browser e dalla pagina aperta. | Dipendono dalle funzioni offerte dal servizio. | Valutazione più ampia secondo gli audit Lighthouse disponibili. | Tag manifest, validità strutturale essenziale del manifest e parole chiave per la registrazione del Service Worker negli script inline. |
| **Controlli di rete del progetto** | Il browser gestisce le richieste della pagina. | Dipendono dall'implementazione del servizio. | Dipendono dal contesto in cui viene eseguito l'audit. | Rifiuta destinazioni non pubbliche, valida ogni redirect, applica pinning dell'IP e limita la dimensione della risposta. |
| **Limiti principali** | Richiede accesso manuale e competenze tecniche. | Non è l'obiettivo di questa API. | Non è un servizio API di questo progetto. | Non esegue JavaScript né determina affidabilità, assenza di phishing o installabilità effettiva. |

Il confronto è **orientativo**: descrive scopi e controlli di questo progetto, non costituisce un test indipendente delle funzionalità o della sicurezza degli altri strumenti.

### 💡 Quale contributo offre il progetto

1. **Controllo automatizzabile:** l'endpoint permette a un'interfaccia o a un altro client di richiedere una verifica senza dover aprire manualmente i DevTools.
2. **Risultato leggibile:** la risposta JSON espone separatamente il tag manifest, la validità essenziale del file e il rilevamento basato sugli script inline.
3. **Richieste in uscita con protezioni:** l'engine valida gli indirizzi IP risolti, evita proxy d'ambiente, mantiene il pinning dell'IP per la connessione, controlla i redirect uno per uno e limita i byte letti.

Questi controlli riducono alcuni rischi lato server, ma **non rendono l'applicazione un sistema anti-phishing né attestano che il sito esaminato sia sicuro**. Il rilevamento del Service Worker è limitato agli script inline e il verdetto PWA si basa sulla validità strutturale essenziale del manifest, non sull'esecuzione o sull'installabilità reale nel browser.

---

## 🔒 Hardening & Protocolli di Sicurezza dell'Infrastruttura

Per garantire l'integrità del microservizio contro attacchi cyber ed intrusioni, l'infrastruttura di rete applica tre livelli di blindatura:

*   **SSH Jail (Porta Custom):** Il demone SSH è stato spostato dalla porta standard 22 a una porta alta casuale (es. `2224`) mitigando il 99% dei bot automatici di brute-force. L'accesso all'utente `root` e l'autenticazione tramite password sono disabilitati in favore delle sole chiavi crittografiche asimmetriche (`PasswordAuthentication no`).
*   **Intrusion Prevention (Fail2Ban):** Monitoraggio costante dei log di sistema per il ban automatico a livello di IPtables degli indirizzi IP che mostrano comportamenti ostili o tentativi di connessione falliti.
*   **Firewall Perimetrale (UFW):** Politica restrittiva totale (`default deny incoming`). Sono autorizzate esclusivamente le porte essenziali per il funzionamento e la gestione del servizio:
    *   `2224/tcp` (Accesso SSH Protetto)
    *   `80/tcp` & `443/tcp` (Traffico Web HTTP/HTTPS gestito da Nginx)

---

## 🚀 Guida al Deployment Rapido sul Server

### 1. Installazione Dipendenze e Firewall
Esegui sul terminale della tua VPS Linux (Ubuntu/Debian):
```bash
# Aggiornamento sistema e installazione pacchetti
sudo apt update && sudo apt install python3-pip nginx certbot python3-certbot-nginx fail2ban ufw -y

# Configurazione e attivazione Firewall (Attenzione alla porta SSH corretta!)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 2224/tcp comment 'SSH Protetto'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw enable

# Installazione librerie Python dell'API
pip install fastapi uvicorn requests beautifulsoup4 pydantic
```

### 2. Configurazione dell'Engine in Background (Systemd)
Crea il file `/etc/systemd/system/pwa_api.service`:
```ini
[Unit]
Description=Uvicorn Instance per API Web PWA Detector
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/pwa_detector
ExecStart=/var/www/pwa_detector/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```
Abilita e avvia il servizio permanentemente:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pwa_api.service
sudo systemctl start pwa_api.service
```

### 3. Configurazione di Nginx e Certificato SSL Gratis
Crea il file di blocco `/etc/nginx/sites-available/api.tuosito.it`:
```nginx
server {
    listen 80;
    server_name api.tuosito.it;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Attiva il sito e genera il certificato HTTPS automatico:
```bash
sudo ln -s /etc/nginx/sites-available/api.tuosito.it /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo certbot --nginx -d api.tuosito.it
```

---

## 🔄 Aggiornare e distribuire tramite Git

### Dal computer di sviluppo

Dopo aver modificato i file, esegui i test e pubblica le modifiche sul branch `main` di GitHub:

```bash
git status
git switch main
git pull --rebase origin main
# Esegui i test del progetto
git add README.md
git commit -m "docs: update README"
git push origin main
```

Sostituisci `README.md` con i percorsi dei file modificati. Se hai modifiche locali non ancora salvate, completale con un commit oppure mettile da parte prima di cambiare branch o fare pull.

### Sulla VPS

Il push su GitHub **non distribuisce automaticamente** l'app sulla VPS. Per aggiornare il checkout del server:

```bash
cd /percorso/del/progetto
git switch main
git pull --ff-only origin main
```

Dopo aver aggiornato il codice dell'API, se il servizio `systemd` è configurato e attivo, riavvialo e controllane lo stato:

```bash
sudo systemctl restart pwa_api.service
sudo systemctl status pwa_api.service
```

Sostituisci `/percorso/del/progetto` con la directory effettiva del repository sul server. Non aggiungere al repository ambienti virtuali, password, chiavi private o altri segreti.

---

## 📬 Specifiche dell'Endpoint API (Esempio di Risposta JSON)

L'interfaccia usa `GET` per le verifiche e `POST` per le segnalazioni al database. Una documentazione interattiva ed esplorabile (Swagger UI) viene autogenerata dal framework all'indirizzo `/docs`.

**Richiesta d'esempio:**
`GET https://api.tuosito.it/api/v1/check-pwa?url=europa.eu`

**Risposta del server (Payload JSON):**
```json
{
    "url": "https://europa.eu",
    "is_pwa": true,
    "manifest_tag_found": true,
    "manifest_file_valid": true,
    "service_worker_detected": true
}
```

### Invio al database per revisione

Dopo una scansione che rileva un manifest valido, il frontend offre
**Aggiungi al database**. L'endpoint `POST /api/v1/submissions` ripete la
scansione lato server e salva solo URL che superano nuovamente il controllo.
La risposta indica `pending_review`; URL e indicatori tecnici sono conservati
in SQLite, senza dati personali. L'endpoint non espone l'elenco e le
segnalazioni non diventano pubbliche automaticamente.

Il database si trova per impostazione predefinita in
`pwa-detector-engine/data/pwa_radar.sqlite3`; in produzione imposta
`PWA_DATABASE_PATH` a una directory privata e persistente, scrivibile
dall'utente del servizio e fuori dalla document root. Il file è escluso da
Git. La configurazione systemd di esempio usa `/var/lib/pwa-radar/`;
per Plesk segui i passaggi in `deploy-plesk-debian13.txt`.

Le segnalazioni in attesa possono essere controllate direttamente nel file
SQLite, ad esempio:

```sql
SELECT id, url, submitted_at, status, manifest_file_valid,
       service_worker_detected
FROM pwa_submissions
WHERE status = 'pending_review'
ORDER BY submitted_at;
```

Non pubblicare una voce prima di averne verificato manualmente contenuti,
identità del sito e pertinenza. Il database è una coda di proposte e non un
registro di autorizzazioni o una certificazione di sicurezza.

---

## ⚠️ Known Limitations

*   **Script esterni:** il Service Worker viene cercato solo negli script inline della pagina. Se la registrazione è in un file `.js` esterno, `service_worker_detected` può essere `false` (falso negativo). Il verdetto `is_pwa` dipende comunque solo dal manifest valido.
*   **Rendering:** non viene eseguito JavaScript; il tool privilegia velocità e sicurezza rispetto a un browser headless.
*   **Codice:** l'app è in `pwa-detector-engine/` (API, front-end, file di deploy e test).

## PWA Radar installabile

Il frontend in `pwa-detector-engine/frontend/` include manifest, icone PNG
e Service Worker. Pubblica `index.html`, `manifest.webmanifest`, `sw.js`
e la cartella `pwa-icons/` su HTTPS (non la cartella `tests/`);
la base API è vuota per usare lo stesso dominio. Per Plesk segui
`deploy-plesk-debian13.txt`, non i comandi di installazione nginx generici.

Nei browser compatibili compare il pulsante di installazione oppure puoi
usare il menu del browser. Su iPhone/iPad usa Safari, Condividi,
Aggiungi alla schermata Home. L'interfaccia resta disponibile offline
dopo la prima apertura online e l'attivazione del Service Worker, ma
**le analisi richiedono Internet**. Le risposte API non sono memorizzate
dal Service Worker.

Il verdetto visualizzato indica il rilevamento essenziale del manifest,
non certifica installabilità o sicurezza del sito esaminato.
La sitemap (`sitemap.xml`) elenca la homepage e la pagina metodologica
canonica; `robots.txt` la pubblica ai crawler. Inviare la sitemap a
Google Search Console non garantisce indicizzazione o posizionamento.
La metodologia pubblica, i limiti del rilevamento e l'esempio Europol sono
descritti in `pwa-detector-engine/frontend/metodologia.html`; pubblica anche
questa pagina nella document root. Non attribuisce intenzioni tecniche a
Europol sulla base del solo pulsante d'installazione.
I test della shell si eseguono senza dipendenze aggiuntive con:

```bash
node --test pwa-detector-engine/frontend/tests/*.test.cjs
```

---

## 🎨 Logica di Visualizzazione Front-End (Checklist Grafica)
Il client JavaScript estrae selettivamente i parametri booleani mappandoli nell'interfaccia utente in questo modo:

*   **`is_pwa: true`** ──► **Manifest PWA rilevato** (controllo essenziale, non certificazione).
*   **`is_pwa: false`** ──► **Manifest PWA valido non rilevato**.
*   **Checklist di Ispezione Tecnica (Dettaglio Dinamico):**
    *   `manifest_tag_found` ──► ✅ / ❌ Tag `<link rel="manifest">` rilevato
    *   `manifest_file_valid` ──► ✅ / ❌ Manifest valido secondo il controllo essenziale
    *   `service_worker_detected` ──► ✅ / ❌ Registrazione Service Worker rilevata negli script inline

---
*© 2026 Marcello Stanca Project PWA Detector Engine. 
