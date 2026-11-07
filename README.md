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

## 📬 Specifiche dell'Endpoint API (Esempio di Risposta JSON)

L'interfaccia risponde a chiamate in modalità `GET`. Una documentazione interattiva ed esplorabile (Swagger UI) viene autogenerata dal framework all'indirizzo `/docs`.

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

---

## ⚠️ Known Limitations

*   **Script esterni:** il Service Worker viene cercato solo negli script inline della pagina. Se la registrazione è in un file `.js` esterno, `service_worker_detected` può essere `false` (falso negativo). Il verdetto `is_pwa` dipende comunque solo dal manifest valido.
*   **Rendering:** non viene eseguito JavaScript; il tool privilegia velocità e sicurezza rispetto a un browser headless.
*   **Codice:** l'app è in `pwa-detector-engine/` (API, front-end, file di deploy e test).

---

## 🎨 Logica di Visualizzazione Front-End (Checklist Grafica)
Il client JavaScript estrae selettivamente i parametri booleani mappandoli nell'interfaccia utente in questo modo:

*   **`is_pwa: true`** ──► Mostra Badge: **🛡️ VERDETTO: PWA ESISTENTE** (Sito installabile sicuro).
*   **`is_pwa: false`** ──► Mostra Badge: **🔴 VERDETTO: NO PWA** (Sito standard).
*   **Checklist di Ispezione Tecnica (Dettaglio Dinamico):**
    *   `manifest_tag_found` ──► ✅ / ❌ Tag `<link rel="manifest">` rilevato
    *   `manifest_file_valid` ──► ✅ / ❌ File 'manifest.json' integro e valido
    *   `service_worker_detected` ──► ✅ / ❌ Script Service Worker in esecuzione

---
*© 2026 Marcello Stanca Project PWA Detector Engine. 
