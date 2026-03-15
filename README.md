# Furikaeri

A JLPT flashcard web app for the community. Import grammar, kanji, and vocabulary from CSV, study with spaced repetition (FSRS-style scheduler), and manage your decks in one place.

![Furikaeri](imgs/Furikaeri.gif)

---

## Features

- **Study** — Start sessions per deck; see due, new, and learning cards. Rate with Again / Hard / Good / Easy. You can also **study by label**: choose a label (e.g. from your CSV) and run a label-only session. Optional session goals (e.g. “N reviews” or “M minutes”), daily goal and streak, catch-up mode (no new cards), and option to exclude listening cards when you can’t use sound.
- **Import** — One-off or re-import Grammar, Kanji, and Vocabulary from header-based CSVs (one format per type; see [CSV formats](#csv-import-formats-very-important)). Reimport/sync adds new rows to existing decks (configurable merge/skip).
- **Decks** — List decks, view card counts by type, export deck cards as CSV (formula-safe).
- **Search** — Full-text search across cards; open results to see grammar and examples.
- **Metrics** — Retention proxy, streak, daily goal, rating distribution (Again/Hard/Good/Easy), and average time per card.
- **Leeches** — View and manage cards you keep forgetting; see [Leeches](#leeches) below.
- **Audio (TTS)** — Cached text-to-speech for reading and listening cards; optional autoplay for listening cards.

---

## How to run

You need **Docker** and **Docker Compose**. From the **project root** (the folder that contains `compose.yml` and `Makefile`):

```bash
make run
```

Open **[http://localhost:8000](http://localhost:8000)** in your browser.

To stop the app:

```bash
make stop
```

---

## How to use the app

1. **Start the app** — Run `make run` and open [http://localhost:8000](http://localhost:8000).

2. **Sign up or log in** — Use the **Account** tab to create an account or sign in. You need an account to import and study.

3. **Import your data (Import tab)**
   - Choose a **Level** (e.g. N5, N3, or **Custom** for non-JLPT decks). Optionally set a **Deck name**; if you leave it blank, a default name (e.g. "N3 Grammar") is used.
   - For **Grammar**, **Vocabulary**, or **Kanji**: use a CSV that matches the header shown under that section (see [CSV formats](#csv-import-formats-very-important)). Click **Choose file**, pick your CSV, then **Import**.
   - A new deck is created. You can **Reimport / Sync** later: select the deck from the list, choose the same level and format, then upload an updated CSV to add or merge new rows.

4. **Study (Study tab)**
   - Select a **deck** from the dropdown.
   - **Deck session:** Click **Start** to study all cards in the deck (or use session options for goals). You’ll see due, new, and learning cards.
   - **Label session:** To study only cards with a specific label, choose a **Label** from the dropdown (labels come from your imported data) and click **Start label session**. Only cards with that label will appear until the session ends.
   - For each card: read the front, reveal the back, then rate **Again** / **Hard** / **Good** / **Easy**. The scheduler will show the card again based on your rating.

5. **Other tabs**
   - **Decks** — View all decks, card counts, and export deck cards as CSV.
   - **Search** — Full-text search across cards.
   - **Metrics** — Retention, streak, daily goal, and rating distribution.
   - **Leeches** — Cards you often fail; you can suspend or search for examples (see [Leeches](#leeches)).
   - **Account** — Log out or manage your account.

---

## Quick start: import and study N5 (data/jlpt)

The repo includes JLPT CSV files in **`data/jlpt/`**. This example uses **N5** only: log in, import the N5 files, then study.

1. **Start the app and open it**
   - From the project root: `make run`
   - Open [http://localhost:8000](http://localhost:8000) in your browser.

2. **Log in (or sign up)**
   - On the landing page, sign up with a username, email, and password, or log in if you already have an account.
   - After that you’ll see the main app with tabs: Study, Import, Decks, Search, Metrics, Leeches, Account.

3. **Import N5**
   - Open the **Import** tab.
   - Set **Level** to **N5**.
   - **Grammar:** Click **Choose file**, select **`data/jlpt/jlpt_N5_grammar.csv`** from this repo, then click **Import**. A deck like “N5 Grammar” is created.
   - **Kanji (optional):** Level N5, choose **`data/jlpt/jlpt_N5_kanji.csv`**, then **Import**. Creates “N5 Kanji”.
   - **Vocabulary (optional):** Level N5, choose **`data/jlpt/jlpt_N5_vocabulary.csv`**, then **Import**. Creates “N5 Vocabulary”.
   - You can leave **Deck name** blank; the app will use the default names above.

4. **Study**
   - Open the **Study** tab.
   - In the deck dropdown, select the deck you want (e.g. **N5 Grammar**).
   - Click **Start** to begin a session. You’ll see due, new, and learning cards.
   - For each card: read the front, reveal the back, then choose **Again**, **Hard**, **Good**, or **Easy**. The app will schedule the next review from your rating.

---

## CSV import formats

The app uses **one format per type**: Grammar, Kanji, and Vocabulary each have a single header-based CSV format. The **Import** tab shows the exact header to use. If your CSV headers or column order don’t match, the import will fail with a clear error.

### Grammar CSV

- **Header row (required):** `japanese_expression`, `english_meaning`, `grammar_structure`, `labels`, `example_1`, `example_2`, …
- **Required columns:** `japanese_expression`, `english_meaning`
- **Optional:** `grammar_structure`; **`labels`** (semicolon- or comma-separated, e.g. `jlpt_n3; formal` — used for study-by-label; place before `example_1`); `example_1`, `example_2`, … (extra columns are collected as examples)

**On cards:** Front = expression + first example; Back = meaning, structure, and up to 5 examples. Rows with empty `japanese_expression` or `english_meaning` are skipped.

### Kanji CSV

- **Header row (required):** `rank`, `kanji`, `onyomi`, `kunyomi`, `meaning`, `labels`, `example_1`, `example_2`, …
- **Required columns:** `kanji`, `meaning`
- **Optional:** `rank`, `onyomi`, `kunyomi`; **`labels`** (semicolon- or comma-separated; place before `example_1`); `example_1`, `example_2`, … (each example can be one line or three lines `jp` / `romaji` / `en`)

**On cards:** Reading card (front: kanji → recall readings); meaning card (front: kanji → recall meaning); usage card when an example sentence is present. Rows with empty `kanji` or `meaning` are skipped.

### Vocabulary CSV

- **Header row (required):** `rank`, `word`, `reading_kana`, `reading_romaji`, `part_of_speech`, `meaning`, `labels`, `example_1`, `example_2`, …
- **Required columns:** `word`, `meaning`
- **Optional:** `rank`, `reading_kana`, `reading_romaji`, `part_of_speech`; **`labels`** (semicolon- or comma-separated, e.g. `jlpt_n2; verb` — used for study-by-label; place before `example_1`); `example_1`, `example_2`, … (each example can be one line or three lines `jp` / `romaji` / `en`)

**On cards:** Front = word + first example line (Japanese only); Back = word, reading, meaning, and list of examples. Rows missing `word` or `meaning` are skipped.

**Tip:** In the app, open the **Import** tab to see the exact header for each type. Use **Reimport / Sync** to add new rows to an existing deck without replacing it. When adding new expressions and choosing labels for the `labels` column, **`data/labels.txt`** can be used as a reference for suggested label names (e.g. `jlpt_n5`, `business`, `work`).

---

## Leeches

A **leech** is a card you keep failing: each time you rate it **Again**, its lapse count goes up. When that count reaches the **leech threshold** (default **8**), the card is marked as a leech. Leeches are a useful signal that a card may need different handling (e.g. more context, a mnemonic, or a break).

- **How cards become leeches** — Automatically. If you press Again enough times (e.g. 8), the scheduler sets its leech flag and it appears in the **Leeches** tab.
- **Leeches tab** — Pick a deck to see all its leech cards. You can **suspend** a leech (so it no longer appears in study until you unsuspend) or **unsuspend** it. Use “Search examples” to open the Search tab with that card’s content so you can review context.
- **Session limits** — The app can cap how many new cards you get per day when a deck has many leeches, so leeches don’t overwhelm your queue.

---

## Resetting data

To clear all decks, cards, and review state and start over:

**Option 1 — Reset script (recommended)**

From the project root:

```bash
make reset-data
```

You will be prompted to type `yes` to confirm.

**Option 2 — Remove the volume**

Stop the app, then remove the volume so the next run starts with a fresh database:

```bash
make stop
docker compose down -v
make run
```

---

## Customizing or self-hosting?

For environment variables, data paths, optional study config, project layout, testing, and syncing to a server, see **[developers.md](developers.md)**.

**Never commit `.env` or real secrets to the repo.** In production, serve the app over **HTTPS** so the session cookie’s `Secure` flag takes effect (see developers.md).
