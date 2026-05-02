# Furikaeri

A JLPT flashcard web app for the community. Import grammar, kanji, and vocabulary from CSV, study with spaced repetition (FSRS-style scheduler), and manage your decks in one place.

![Furikaeri](imgs/Furikaeri.gif)

---

## Features

- **Study** — Start sessions per deck; see due, new, and learning cards. Rate with Again / Hard / Good / Easy. You can also **study by label**: choose a label (e.g. from your CSV) and run a label-only session. Add a per-card **My note** (mnemonics, reminders) on the back of a card. Optional session goals (e.g. “N reviews” or “M minutes”), daily goal and streak, catch-up mode (no new cards), and option to exclude listening cards when you can’t use sound.
- **Decks** — Create decks by importing Grammar, Kanji, or Vocabulary from header-based CSVs (one format per type; see [CSV formats](#csv-import-formats-very-important)). **Export** a deck as CSV, **delete** a deck, or **reimport / sync** an updated CSV (see [How to use](#how-to-use-the-app)). Card counts and deck list are on the same screen.
- **Search** — Full-text search across cards; open results to see grammar and examples.
- **Metrics** — Retention proxy, streak, daily goal, rating distribution (Again/Hard/Good/Easy), and average time per card.
- **Leeches** — View and manage cards you keep forgetting; see [Leeches](#leeches) below.
- **Audio (TTS)** — Cached text-to-speech for reading and listening cards; optional autoplay for listening cards.

---

## How to run

You need **Docker** and **Docker Compose**. From the **project root** (the folder that contains `compose.yml` and `Makefile`):

1. Copy environment config:

```bash
cp .env.example .env
```

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

2. **Sign up or log in** — On the landing page, register or sign in. Once you’re in the app, open the **Account** menu in the header (your username) to see who’s logged in or to **Log out**. You need an account to import and study.

3. **Import and manage decks (Decks tab)**
   - Choose a **Level** (e.g. N5, N3, or **Custom** for non-JLPT decks). Optionally set a **Deck name**; if you leave it blank, a default name (e.g. "N3 Grammar") is used.
   - Choose the **Grammar / Vocabulary / Kanji** import source, then use a CSV that matches the header shown under that source (see [CSV formats](#csv-import-formats-very-important)). Click **Choose file**, pick your CSV, then **Import**.
   - A new deck is created. To update an existing deck, open **Reimport / Sync**: pick the deck, level, and CSV format, then upload an updated file. Sync modes: **Skip (only add new)**, **Merge examples into existing**, and **Replace existing from CSV (fields)** (overwrite mapped fields such as examples, notes, labels, and meanings from the CSV).
   - **Export to CSV** downloads the deck in the same column layout as import (including merged deck notes and your **My note** text when you export). **Delete deck** removes a deck entirely.

4. **Study tab**
   - Select a **deck** from the dropdown.
   - **Deck session:** Click **Start** to study all cards in the deck (or use session options for goals). You’ll see due, new, and learning cards.
   - **Label session:** To study only cards with a specific label, choose a **Label** from the dropdown (labels come from your imported data) and click **Start label session**. Only cards with that label will appear until the session ends.
   - For each card: read the front, reveal the back, then rate **Again** / **Hard** / **Good** / **Easy**. The scheduler will show the card again based on your rating. You can add a personal **My note** on the back (separate from the deck’s CSV **Deck note**).

5. **Other tabs**
   - **Search** — Full-text search across cards.
   - **Metrics** — Retention, streak, daily goal, and rating distribution.
   - **Leeches** — Cards you often fail; you can suspend or search for examples (see [Leeches](#leeches)).
   - **Account** — Use the header account menu to log out.

---

## Quick start: import and study N5 (data/jlpt)

The repo includes JLPT CSV files in **`data/jlpt/`**. This example uses **N5** only: log in, import the N5 files, then study.

1. **Start the app and open it**
   - From the project root: `make run`
   - Open [http://localhost:8000](http://localhost:8000) in your browser.

2. **Log in (or sign up)**
   - On the landing page, sign up with a username, email, and password, or log in if you already have an account.
   - After that you’ll see the main app with tabs: **Study**, **Decks**, **Search**, **Metrics**, and **Leeches**. Account actions are in the header menu.

3. **Import N5**
   - Open the **Decks** tab.
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

Use **one header-based format per type**. The importer matches columns by **name** (not position), so order can vary.

### Required columns

- **Grammar:** `japanese_expression`, `english_meaning`
- **Kanji:** `kanji`, `meaning`
- **Vocabulary:** `word`, `meaning`

### Common optional columns

- `labels` — short tags (e.g. `jlpt_n2;verb`) used for study-by-label.
- `notes` — free text shown on card back as **Deck note**.
- `example_1`, `example_2`, … — examples.

### Simple example (Grammar)

```csv
japanese_expression,english_meaning,grammar_structure,labels,notes,example_1
だ,to be,Noun + だ,jlpt_n5;basic,Used in casual speech,これは本だ。
```

### Simple example (Kanji)

```csv
kanji,meaning,labels,notes,example_1
日,day sun,jlpt_n5;time,My hint,日本
```

### Simple example (Vocabulary)

```csv
word,meaning,labels,notes,example_1
大切,important,jlpt_n5;core,Remembering 大切,大切にする
```

### Round-trip tip

- Export from **Decks → Export to CSV** to get a valid template.
- Edit the file, then import or sync it again.
- Exported `notes` includes deck note + your per-card **My note** text for your account, merged into the same cell.

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
