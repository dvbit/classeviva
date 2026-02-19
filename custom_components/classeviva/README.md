# Classeviva per Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?logo=homeassistantcommunitystore)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/v/release/dvbit/ha-classeviva?sort=semver&logo=github)](https://github.com/dvbit/ha-classeviva/releases)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue?logo=homeassistant)](https://www.home-assistant.io)
[![Licenza: MIT](https://img.shields.io/badge/Licenza-MIT-yellow.svg)](LICENSE)

Integrazione per Home Assistant che permette di monitorare il **registro elettronico Classeviva** di [Spaggiari](https://web.spaggiari.eu) direttamente dalla tua dashboard.

Supporta account **genitore (G)** e **studente (S)**. I dati vengono aggiornati periodicamente tramite le API REST ufficiali di Classeviva.

---

## Funzionalità

| | Funzione | Descrizione |
|--|---------|-------------|
| 📊 | **Media generale** | Sensore numerico con la media complessiva; un attributo `media_MATERIA` per ogni materia |
| 📝 | **Ultimo voto** | Valore decimale dell'ultimo voto ricevuto, con materia, data e tipo negli attributi |
| 📚 | **Voti per materia** | Un sensore dedicato per ogni materia — stato = ultimo voto (utile per il grafico storico); attributi: `media`, `min_voto`, `max_voto` |
| 🚫 | **Assenze** | Conteggio totale con dettaglio dell'ultima assenza |
| ⏰ | **Ritardi** | Conteggio totale con dettaglio dell'ultimo ritardo |
| 🚪 | **Uscite anticipate** | Conteggio totale con dettaglio dell'ultima uscita |
| 📋 | **Compiti da fare** | Numero di compiti futuri con dettaglio del prossimo |
| ⚠️ | **Note disciplinari** | Conteggio totale con dettaglio dell'ultima nota |
| 🕐 | **Ultimo aggiornamento** | Timestamp dell'ultimo fetch completato con successo |
| 📅 | **4 Calendari** | Voti, Assenze, Compiti, Note come entità calendario di HA |
| 🔘 | **Pulsante Aggiorna** | Forza un aggiornamento immediato dei dati |
| ⚙️ | **Servizio** | `classeviva.refresh_data` utilizzabile nelle automazioni |
| 📈 | **Importazione storico voti** | Opzionale: inserisce tutti i voti passati nello storico del sensore usando le date reali delle valutazioni |

---

## Installazione

### Tramite HACS (consigliato)

1. Apri **HACS** in Home Assistant
2. Vai su **Integrazioni** → ⋮ → **Repository personalizzati**
3. Aggiungi `https://github.com/dvbit/ha-classeviva` come tipo **Integrazione**
4. Cerca **Classeviva** e clicca **Scarica**
5. Riavvia Home Assistant

### Manuale

1. Copia la cartella `custom_components/classeviva/` nella cartella `config/custom_components/` di Home Assistant
2. Riavvia Home Assistant

---

## Configurazione

Vai su **Impostazioni → Dispositivi e servizi → Aggiungi integrazione** e cerca **Classeviva**.

### Parametri di configurazione

| Campo | Descrizione | Default |
|-------|-------------|---------|
| **ID Studente** | Codice di accesso fornito dalla scuola (es. `G12345678P` per genitore, `S12345678P` per studente) | — |
| **Password** | Password del registro Classeviva | — |
| **Nome Studente** | Etichetta opzionale usata come suffisso negli ID delle entità (es. `mario`) | ID Studente |
| **Frequenza aggiornamento** | Minuti tra un aggiornamento e l'altro (60–1440) | `60` |
| **Nome calendario** | Prefisso per le 4 entità calendario | `Classeviva` |
| **Importa storico voti** | Al primo avvio di HA, inserisce tutti i voti passati nello storico dei sensori usando le **date reali** delle valutazioni | `No` |

> **Account genitore vs studente:** Gli account studente (`S...`) potrebbero non avere accesso alle API REST. In caso di sensori che restano `unknown`, usa le credenziali del genitore (`G...`).

---

## Entità create

Tutti gli ID delle entità usano il nome dello studente come suffisso. Gli esempi qui sotto usano `mario`.

### Sensori

| Entità | Stato | Unità | Attributi principali |
|--------|-------|-------|----------------------|
| `sensor.classeviva_mario_media_generale` | Media complessiva (decimale) | — | `voti_totali`, `media_<materia>` per ogni materia |
| `sensor.classeviva_mario_ultimo_voto` | Ultimo voto (decimale) | — | `materia`, `data`, `voto`, `tipo`, `commento` |
| `sensor.classeviva_mario_media_<materia>` | Ultimo voto nella materia (decimale) | — | `media`, `min_voto`, `max_voto`, `num_voti`, `data`, `voto`, `tipo`, `commento` |
| `sensor.classeviva_mario_assenze` | Totale assenze | assenze | `data`, `giustificata`, `motivo` |
| `sensor.classeviva_mario_ritardi` | Totale ritardi | ritardi | `data`, `giustificata` |
| `sensor.classeviva_mario_uscite_anticipate` | Totale uscite anticipate | uscite | `data`, `giustificata` |
| `sensor.classeviva_mario_compiti` | Compiti futuri | compiti | `data`, `materia`, `descrizione`, `autore` |
| `sensor.classeviva_mario_note` | Totale note disciplinari | note | `data`, `testo`, `autore`, `letta` |
| `sensor.classeviva_mario_ultimo_aggiornamento` | Timestamp ultimo aggiornamento | — | — |

#### Sensori per materia

I sensori `media_<materia>` vengono creati automaticamente in base alle materie presenti nel registro. Il **nome dell'entità** si ricava dal nome della materia: tutto minuscolo, accenti rimossi, spazi sostituiti da `_`. Ad esempio:

| Materia nel registro | Entità HA |
|----------------------|-----------|
| `MATEMATICA` | `sensor.classeviva_mario_media_matematica` |
| `LINGUA E LETTERATURA ITALIANA` | `sensor.classeviva_mario_media_lingua_e_letteratura_italiana` |
| `SCIENZE NATURALI` | `sensor.classeviva_mario_media_scienze_naturali` |
| `STORIA E GEOGRAFIA` | `sensor.classeviva_mario_media_storia_e_geografia` |

> Lo **stato del sensore è l'ultimo voto ricevuto** (non la media). Questo permette al grafico storico di HA di mostrare la progressione delle valutazioni nel tempo. La media è disponibile nell'attributo `media`.

### Calendari

| Entità | Contenuto |
|--------|-----------|
| `calendar.classeviva_mario_voti` | Tutti i voti (titolo: valore — materia — tipo) |
| `calendar.classeviva_mario_assenze` | Assenze, ritardi e uscite anticipate |
| `calendar.classeviva_mario_compiti` | Compiti con materia e descrizione completa |
| `calendar.classeviva_mario_note` | Note disciplinari con testo integrale |

I calendari contengono il **registro storico completo** di ogni evento con le date corrette — ideali per consultare i voti passati o verificare i compiti futuri.

### Pulsante

| Entità | Descrizione |
|--------|-------------|
| `button.classeviva_mario_refresh` | Forza un aggiornamento immediato dei dati |

---

## Card Lovelace

> Sostituisci `mario` con il suffisso del tuo studente in tutti gli esempi.

### Riepilogo generale

```yaml
type: markdown
title: "📚 Classeviva"
content: |
  {% set media = states.sensor.classeviva_mario_media_generale %}
  {% set ultimo = states.sensor.classeviva_mario_ultimo_voto %}
  {% set assenze = states.sensor.classeviva_mario_assenze %}
  {% set ritardi = states.sensor.classeviva_mario_ritardi %}
  {% set uscite = states.sensor.classeviva_mario_uscite_anticipate %}
  {% set compiti = states.sensor.classeviva_mario_compiti %}
  {% set note = states.sensor.classeviva_mario_note %}
  {% set upd = states.sensor.classeviva_mario_ultimo_aggiornamento %}
  | | |
  |---|---|
  | 📊 Media generale | **{{ media.state | default('—') }}** |
  | 📝 Ultimo voto | **{{ ultimo.state | default('—') }}** — {{ ultimo.attributes.materia | default('') }} |
  | 🚫 Assenze | {{ assenze.state | default(0) }} |
  | ⏰ Ritardi | {{ ritardi.state | default(0) }} |
  | 🚪 Uscite anticipate | {{ uscite.state | default(0) }} |
  | 📋 Compiti | {{ compiti.state | default(0) }} |
  | ⚠️ Note | {{ note.state | default(0) }} |
  | 🔄 Aggiornato | {{ as_timestamp(upd.state) | timestamp_custom('%d/%m/%Y %H:%M', true) if upd.state not in ['unknown','unavailable'] else '—' }} |
```

### Medie per materia

```yaml
type: markdown
title: "📊 Medie per Materia"
content: |
  {% set s = states.sensor.classeviva_mario_media_generale %}
  {% if s and s.state not in ['unknown','unavailable'] %}
  **Media generale: {{ s.state }}** · {{ s.attributes.voti_totali | default(0) }} voti totali

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

### Dettaglio materia

Da duplicare e adattare per ogni materia.

```yaml
type: markdown
title: "📝 Italiano"
content: |
  {% set s = states.sensor.classeviva_mario_media_lingua_e_letteratura_italiana %}
  {% if s and s.state not in ['unknown','unavailable'] %}
  ## Ultimo voto: {{ s.state }} ({{ s.attributes.voto | default('') }})
  | | |
  |---|---|
  | 📅 Data | {{ s.attributes.data | default('—') }} |
  {% if s.attributes.tipo %}| 📋 Tipo | {{ s.attributes.tipo }} |{% endif %}
  {% if s.attributes.commento %}| 💬 Commento | {{ s.attributes.commento }} |{% endif %}
  | 📊 Media | **{{ s.attributes.media | default('—') }}** |
  | ⬇️ Min | {{ s.attributes.min_voto | default('—') }} |
  | ⬆️ Max | {{ s.attributes.max_voto | default('—') }} |
  | 🔢 N. voti | {{ s.attributes.num_voti | default(0) }} |
  {% else %}
  Nessun voto disponibile
  {% endif %}
```

### Assenze e presenze

```yaml
type: markdown
title: "🚫 Presenze"
content: |
  {% set a = states.sensor.classeviva_mario_assenze %}
  {% set r = states.sensor.classeviva_mario_ritardi %}
  {% set u = states.sensor.classeviva_mario_uscite_anticipate %}
  | | |
  |---|---|
  | 🚫 Assenze | {{ a.state | default(0) }} |
  | ⏰ Ritardi | {{ r.state | default(0) }} |
  | 🚪 Uscite anticipate | {{ u.state | default(0) }} |
  {% if a.attributes.data is defined and a.attributes.data %}

  **Ultima assenza:** {{ a.attributes.data }}
  Giustificata: {{ 'Sì' if a.attributes.giustificata else 'No' }}
  {% if a.attributes.motivo %}Motivo: {{ a.attributes.motivo }}{% endif %}
  {% endif %}
```

### Compiti da fare

```yaml
type: markdown
title: "📋 Compiti"
content: |
  {% set s = states.sensor.classeviva_mario_compiti %}
  {% if s and s.state | int(0) > 0 %}
  ## {{ s.state }} compiti in programma
  **Prossimo:**
  | | |
  |---|---|
  | 📅 Data | {{ s.attributes.data | default('—') }} |
  | 📖 Materia | {{ s.attributes.materia | default('—') }} |
  | 📝 Descrizione | {{ s.attributes.descrizione | default('—') }} |
  {% if s.attributes.autore %}| 👨‍🏫 Docente | {{ s.attributes.autore }} |{% endif %}
  {% else %}
  ✅ Nessun compito in programma
  {% endif %}
```

### Calendari

```yaml
type: calendar
entities:
  - entity: calendar.classeviva_mario_voti
    color: green
  - entity: calendar.classeviva_mario_compiti
    color: blue
  - entity: calendar.classeviva_mario_assenze
    color: red
  - entity: calendar.classeviva_mario_note
    color: orange
```

### Grafico storico voti per materia

```yaml
type: history-graph
title: "📈 Andamento Matematica"
hours_to_show: 8760
entities:
  - entity: sensor.classeviva_mario_media_matematica
    name: Matematica
```

---

## Automazioni

### Notifica nuovo voto

```yaml
automation:
  alias: "Classeviva: nuovo voto"
  trigger:
    - platform: state
      entity_id: sensor.classeviva_mario_ultimo_voto
  condition:
    - condition: template
      value_template: >
        {{ trigger.from_state.state not in ['unknown', 'unavailable']
           and trigger.to_state.state not in ['unknown', 'unavailable']
           and trigger.from_state.state != trigger.to_state.state }}
  action:
    - service: notify.notify
      data:
        title: "📝 Nuovo voto!"
        message: >
          {{ state_attr('sensor.classeviva_mario_ultimo_voto', 'materia') }}:
          {{ state_attr('sensor.classeviva_mario_ultimo_voto', 'voto') }}
          ({{ states('sensor.classeviva_mario_ultimo_voto') | float | round(1) }})
```

### Notifica nuova assenza

```yaml
automation:
  alias: "Classeviva: nuova assenza"
  trigger:
    - platform: state
      entity_id: sensor.classeviva_mario_assenze
  condition:
    - condition: template
      value_template: >
        {{ trigger.to_state.state | int(0) > trigger.from_state.state | int(0) }}
  action:
    - service: notify.notify
      data:
        title: "🚫 Nuova assenza registrata"
        message: >
          Totale assenze: {{ states('sensor.classeviva_mario_assenze') }}
          — {{ state_attr('sensor.classeviva_mario_assenze', 'data') }}
```

### Promemoria compiti serale

```yaml
automation:
  alias: "Classeviva: promemoria compiti"
  trigger:
    - platform: time
      at: "20:00:00"
  condition:
    - condition: template
      value_template: "{{ states('sensor.classeviva_mario_compiti') | int(0) > 0 }}"
  action:
    - service: notify.notify
      data:
        title: "📚 Compiti da fare"
        message: >
          {{ states('sensor.classeviva_mario_compiti') }} compiti in programma.
          Prossimo: {{ state_attr('sensor.classeviva_mario_compiti', 'materia') }}
          il {{ state_attr('sensor.classeviva_mario_compiti', 'data') }}
```

### Notifica nuova nota disciplinare

```yaml
automation:
  alias: "Classeviva: nuova nota disciplinare"
  trigger:
    - platform: state
      entity_id: sensor.classeviva_mario_note
  condition:
    - condition: template
      value_template: >
        {{ trigger.to_state.state | int(0) > trigger.from_state.state | int(0) }}
  action:
    - service: notify.notify
      data:
        title: "⚠️ Nuova nota disciplinare"
        message: >
          {{ state_attr('sensor.classeviva_mario_note', 'testo') }}
          — {{ state_attr('sensor.classeviva_mario_note', 'data') }}
```

---

## Importazione storico voti

Quando l'opzione **"Importa storico voti al primo avvio"** è attiva:

1. Al **primo avvio di HA** dopo la configurazione, ogni sensore `media_<materia>` scrive tutti i voti passati nel registro degli stati di HA
2. Ogni voto viene registrato con la **data reale** della valutazione (non una data fittizia)
3. Nel grafico storico del sensore si vedrà la curva completa dei voti dall'inizio dell'anno scolastico
4. L'importazione avviene **una sola volta** — successivi riavvii di HA non re-importano i dati
5. Per voti con la stessa data, viene aggiunto un offset di 1 secondo per garantire che il recorder li registri come eventi distinti

> Questa opzione è utile principalmente al primo setup. I voti ricevuti dopo la configurazione vengono registrati automaticamente ad ogni aggiornamento.

---

## Servizio

```yaml
service: classeviva.refresh_data
# Opzionale: limita l'aggiornamento a un singolo entry
data:
  entity_id: sensor.classeviva_mario_media_generale
```

---

## Risoluzione problemi

| Problema | Soluzione |
|----------|-----------|
| I sensori restano `unknown` | Premi il pulsante Aggiorna; controlla i log HA per errori di autenticazione |
| L'account studente (`S...`) non funziona | Usa le credenziali del genitore (`G...`) — l'accesso API REST degli studenti è limitato |
| I calendari sono vuoti | Verifica che i sensori corrispondenti abbiano dati; controlla i log filtrati per `classeviva` |
| Lo storico non è stato importato | Rimuovi e riconfigura l'integrazione con l'opzione **Importa storico voti** attiva |

Controlla i log di HA in **Impostazioni → Sistema → Log**, filtra per `classeviva`.

---

## Migrazione da v1.x

| | v1.x | v2.0 |
|---|------|------|
| Attributi dei sensori | Liste (`voti`, `compiti`, …) | Piatti — solo ultimo evento |
| Storico completo | Non disponibile | 4 calendari dedicati |
| Sensori per materia | Non disponibili | `sensor.classeviva_<nome>_media_<materia>` |
| Stato sensori per materia | — | Ultimo voto (non la media) |
| Media per materia | — | Attributo `media` sul sensore della materia |
| Voto minimo / massimo | — | Attributi `min_voto`, `max_voto` |
| Opzioni di configurazione | Solo credenziali | + frequenza, calendario, importa storico |

Dopo l'aggiornamento, ricarica l'integrazione da **Impostazioni → Dispositivi e servizi → Classeviva → ⋮ → Ricarica**.

---

## Contribuire

Segnalazioni di bug e pull request sono benvenute su [github.com/dvbit/ha-classeviva](https://github.com/dvbit/ha-classeviva/issues).

---

## Licenza

MIT — vedi [LICENSE](LICENSE)
