# Classeviva per Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/v/release/dvbit/ha-classeviva)](https://github.com/dvbit/ha-classeviva/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Integrazione per Home Assistant che permette di monitorare il registro elettronico **Classeviva** (Spaggiari) direttamente dalla tua dashboard.

Supporta account **genitore (G)** 


Un ringraziamento all'autore della libreria Python che c'è dietro, Matteo Marchese aka FLAK-ZOSO [https://github.com/FLAK-ZOSO] senza il suo lavoro questo non sarebbe stato possibile.


ATTENZIONE: Non mi assumo responsabilità riguardo alla potenziale perdiata di dati privato dovuta alla errata configurazione della vostra istanza homeassistant.

Disclaimer: sviluppato mediante Claude Agent E il mio cervello per verificare e fargli fare esattamente quel che volevo controllando anche il codice.

Se l'integrazione ti è utile e ti va mi puoi e vuoi offire un caffè :-)

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/D1D01UKQ5C)

TODO: Custom Lovelace card

---

## Funzionalità

- **Media Generale** — media complessiva con attributi `media_MATERIA` per ogni materia
- **Ultimo Voto** — valore decimale del voto più recente, con materia/data/tipo in attributi
- **Media per Materia** — un sensore dedicato per ogni materia; lo stato è l'**ultimo voto** (utile per lo storico grafico); attributi: `media`, `min_voto`, `max_voto`, `num_voti`
- **Assenze** — conteggio totale con dettaglio ultima assenza
- **Ritardi** — conteggio totale con dettaglio ultimo ritardo
- **Uscite Anticipate** — conteggio totale con dettaglio
- **Compiti da Fare** — numero di compiti futuri con dettaglio del prossimo
- **Note Disciplinari** — conteggio totale con dettaglio ultima nota
- **Ultimo Aggiornamento** — timestamp dell'ultimo fetch completato
- **4 Calendari** — Voti, Assenze, Compiti, Note come eventi calendario HA
- **Pulsante Aggiorna** — per forzare un aggiornamento manuale
- **Servizio `refresh_data`** — utilizzabile nelle automazioni
- **Frequenza aggiornamento configurabile** (60–1440 minuti)
- **Importazione storico voti** — opzione per backfillare i voti passati con le date reali

---

## Installazione

### HACS (consigliato)

1. Apri HACS in Home Assistant
2. Vai su **Integrazioni** → clicca i tre puntini → **Repository personalizzati**
3. Aggiungi `https://github.com/dvbit/ha-classeviva` come tipo **Integrazione**
4. Cerca **Classeviva** e installalo
5. Riavvia Home Assistant

### Manuale

1. Copia la cartella `custom_components/classeviva/` nella cartella `config/custom_components/` di Home Assistant
2. Riavvia Home Assistant

---

## Configurazione

1. Vai su **Impostazioni → Dispositivi e servizi → Aggiungi integrazione**
2. Cerca **Classeviva**
3. Compila il modulo:

| Campo | Descrizione |
|-------|-------------|
| **ID Studente** | Codice utente (es. `G12345678P` genitore, `S12345678P` studente) |
| **Password** | Password del registro |
| **Nome Studente** | Opzionale — usato come suffisso nelle entity ID |
| **Frequenza aggiornamento** | Minuti tra un aggiornamento e l'altro (60–1440, default 60) |
| **Nome calendario** | Prefisso per i 4 calendari (default "Classeviva") |
| **Importa storico voti** | Se attivo, al primo avvio i voti passati vengono inseriti nello storico dei sensori per materia con le **date reali** delle valutazioni |

> **Nota**: gli account studente (S) potrebbero non avere accesso alle API REST. In questo caso usa le credenziali del genitore (G). L'integrazione gestisce automaticamente la conversione.

---

## Entità create

Dopo la configurazione (dove `NOME` è il nome studente impostato, in minuscolo):

### Sensori

| Entità | Stato | Attributi principali |
|--------|-------|----------------------|
| `sensor.classeviva_NOME_media_generale` | Media decimale | `voti_totali`, `media_MATERIA` per ogni materia |
| `sensor.classeviva_NOME_ultimo_voto` | Valore decimale | `materia`, `data`, `voto` (stringa), `tipo`, `commento` |
| `sensor.classeviva_NOME_media_MATERIA` | Ultimo voto decimale | `media`, `min_voto`, `max_voto`, `num_voti`, `data`, `voto`, `tipo`, `commento` |
| `sensor.classeviva_NOME_assenze` | Conteggio (int) | `data`, `giustificata`, `motivo` |
| `sensor.classeviva_NOME_ritardi` | Conteggio (int) | `data`, `giustificata` |
| `sensor.classeviva_NOME_uscite_anticipate` | Conteggio (int) | `data`, `giustificata` |
| `sensor.classeviva_NOME_compiti` | Compiti futuri (int) | `data`, `materia`, `descrizione`, `autore` |
| `sensor.classeviva_NOME_note` | Conteggio (int) | `data`, `testo`, `autore`, `letta` |
| `sensor.classeviva_NOME_ultimo_aggiornamento` | Timestamp ISO | — |

> I sensori `media_MATERIA` hanno **stato = voto più recente** (non la media). Questo permette di vedere la progressione dei voti nel grafico storico di HA. La media è disponibile nell'attributo `media`.

### Calendari

| Entità | Contenuto |
|--------|-----------|
| `calendar.classeviva_NOME_voti` | Tutti i voti (titolo: valore — materia — tipo) |
| `calendar.classeviva_NOME_assenze` | Assenze, ritardi, uscite anticipate |
| `calendar.classeviva_NOME_compiti` | Compiti con materia e descrizione |
| `calendar.classeviva_NOME_note` | Note disciplinari con testo completo |

### Pulsante

| Entità | Descrizione |
|--------|-------------|
| `button.classeviva_NOME_refresh` | Forza aggiornamento immediato |

---

## Card Lovelace di esempio

Sostituisci `NOME` con il suffisso del tuo studente (es. `ale`).

### 1 — Riepilogo Completo

```yaml
type: markdown
title: "Riepilogo Classeviva"
content: |
  {% set media = states.sensor.classeviva_NOME_media_generale %}
  {% set ultimo = states.sensor.classeviva_NOME_ultimo_voto %}
  {% set assenze = states.sensor.classeviva_NOME_assenze %}
  {% set ritardi = states.sensor.classeviva_NOME_ritardi %}
  {% set uscite = states.sensor.classeviva_NOME_uscite_anticipate %}
  {% set compiti = states.sensor.classeviva_NOME_compiti %}
  {% set note = states.sensor.classeviva_NOME_note %}
  {% set aggiorn = states.sensor.classeviva_NOME_ultimo_aggiornamento %}
  | | |
  |---|---|
  | 📊 Media Generale | **{{ media.state | default('N/A') }}** |
  | 📝 Ultimo Voto | **{{ ultimo.state | default('N/A') }}** — {{ ultimo.attributes.materia | default('') }} |
  | 🚫 Assenze | {{ assenze.state | default(0) }} |
  | ⏰ Ritardi | {{ ritardi.state | default(0) }} |
  | 🚪 Uscite | {{ uscite.state | default(0) }} |
  | 📚 Compiti | {{ compiti.state | default(0) }} |
  | ⚠️ Note | {{ note.state | default(0) }} |
  | 🔄 Aggiornato | {{ as_timestamp(aggiorn.state) | timestamp_custom('%d/%m/%Y %H:%M', true) if aggiorn.state not in ['unknown','unavailable'] else 'N/A' }} |
```

### 2 — Ultimo Voto

```yaml
type: markdown
title: "Ultimo Voto"
content: |
  {% set s = states.sensor.classeviva_NOME_ultimo_voto %}
  {% if s and s.state not in ['unknown','unavailable'] %}
  ## {{ s.attributes.materia | default('') }} — {{ s.state }}
  | | |
  |---|---|
  | 📅 Data | {{ s.attributes.data | default('') }} |
  | 🔢 Voto | **{{ s.attributes.voto | default('') }}** |
  {% if s.attributes.tipo %}| 📋 Tipo | {{ s.attributes.tipo }} |{% endif %}
  {% if s.attributes.commento %}| 💬 Commento | {{ s.attributes.commento }} |{% endif %}
  {% else %}
  Nessun voto disponibile
  {% endif %}
```

### 3 — Medie per Materia

```yaml
type: markdown
title: "Medie Voti"
content: |
  {% set s = states.sensor.classeviva_NOME_media_generale %}
  {% if s and s.state not in ['unknown','unavailable'] %}
  ## 📊 Media Generale: {{ s.state }}
  Voti totali: {{ s.attributes.voti_totali | default(0) }}
  | Materia | Media |
  |---------|-------|
  {% for key, val in s.attributes.items() | sort %}
  {% if key.startswith('media_') %}
  | {{ key[6:] | replace('_', ' ') | title }} | **{{ val }}** |
  {% endif %}
  {% endfor %}
  {% else %}
  Nessun dato disponibile
  {% endif %}
```

### 4 — Dettaglio Voti per Materia

Duplica per ogni materia (es. `LINGUA E LETTERATURA ITALIANA` → entity `media_lingua_e_letteratura_italiana`).

```yaml
type: markdown
title: "Voti Italiano"
content: |
  {% set s = states.sensor.classeviva_NOME_media_lingua_e_letteratura_italiana %}
  {% if s and s.state not in ['unknown','unavailable'] %}
  ## 📝 Ultimo voto: {{ s.state }} — {{ s.attributes.voto | default('') }}
  | | |
  |---|---|
  | 📅 Data | {{ s.attributes.data | default('') }} |
  {% if s.attributes.tipo %}| 📋 Tipo | {{ s.attributes.tipo }} |{% endif %}
  {% if s.attributes.commento %}| 💬 Commento | {{ s.attributes.commento }} |{% endif %}
  | 📊 Media | **{{ s.attributes.media | default('N/A') }}** |
  | ⬇️ Min | {{ s.attributes.min_voto | default('N/A') }} |
  | ⬆️ Max | {{ s.attributes.max_voto | default('N/A') }} |
  | 🔢 N. voti | {{ s.attributes.num_voti | default(0) }} |
  {% else %}
  Nessun voto disponibile
  {% endif %}
```

### 5 — Calendari

```yaml
type: calendar
entities:
  - entity: calendar.classeviva_NOME_voti
  - entity: calendar.classeviva_NOME_assenze
  - entity: calendar.classeviva_NOME_compiti
  - entity: calendar.classeviva_NOME_note
```

---

## Automazioni di esempio

### Notifica nuovo voto

```yaml
automation:
  - alias: "Notifica nuovo voto Classeviva"
    trigger:
      - platform: state
        entity_id: sensor.classeviva_NOME_ultimo_voto
    condition:
      - condition: template
        value_template: "{{ trigger.from_state.state not in ['unknown','unavailable'] }}"
    action:
      - service: notify.notify
        data:
          title: "Nuovo voto!"
          message: >
            {{ state_attr('sensor.classeviva_NOME_ultimo_voto', 'materia') }}:
            {{ state_attr('sensor.classeviva_NOME_ultimo_voto', 'voto') }}
            ({{ states('sensor.classeviva_NOME_ultimo_voto') }})
```

### Notifica nuova assenza

```yaml
automation:
  - alias: "Notifica assenza Classeviva"
    trigger:
      - platform: state
        entity_id: sensor.classeviva_NOME_assenze
    condition:
      - condition: template
        value_template: >
          {{ trigger.to_state.state | int > trigger.from_state.state | int }}
    action:
      - service: notify.notify
        data:
          title: "Nuova assenza registrata"
          message: "Totale assenze: {{ states('sensor.classeviva_NOME_assenze') }}"
```

---

## Servizio aggiornamento dati

```yaml
service: classeviva.refresh_data
# Opzionale: limita a uno specifico entry
data:
  entity_id: sensor.classeviva_NOME_media_generale
```

---

## Importazione storico voti

Quando l'opzione **"Importa storico voti al primo avvio"** è attiva:

1. Al primo avvio di HA dopo la configurazione, ogni sensore `media_MATERIA` scrive tutti i voti passati nel registro degli stati di HA
2. Ogni voto viene registrato con la **data reale** della valutazione, non con una data fittizia
3. Nel grafico storico del sensore si vedrà la curva completa dei voti dall'inizio dell'anno
4. L'importazione avviene **una sola volta** (viene marcata come completata); successivi riavvii di HA non re-importano

> Questa opzione è utile principalmente al primo setup. Per i voti successivi, ogni nuovo voto viene registrato automaticamente con la data del refresh di HA.

---

## Migrazione da v1.x

| Cosa cambia | v1.x | v2.0 |
|-------------|------|------|
| Attributi sensori | Liste (`voti`, `compiti`, ecc.) | Piatti — solo ultimo evento |
| Storico completo | — | 4 calendari dedicati |
| Sensori per materia | — | `sensor.classeviva_NOME_media_MATERIA` |
| Stato sensori materia | — | Ultimo voto (non media) |
| Config flow | Solo credenziali | + frequenza, calendario, importa storico |

---

## Risoluzione problemi

| Problema | Soluzione |
|----------|-----------|
| Account studente (S) non funziona | Usa le credenziali del genitore (G) |
| Sensori `unknown` | Premi il pulsante Aggiorna o attendi il primo ciclo |
| Calendari vuoti | Verifica che i sensori corrispondenti abbiano dati; controlla i log HA |
| Storico non importato | Rimuovi e riconfigura l'integrazione con l'opzione attiva |

Controlla i log HA filtrando per `classeviva` in **Impostazioni → Sistema → Log**.

---

## Licenza

MIT — vedi [LICENSE](LICENSE)
