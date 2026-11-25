# Switzerland: German, Swiss French, Italian (`de`, `fr_CH`, `it`)

The terms Compassion Switzerland uses, taken from its existing translations (the MyCompassion portal and its communications).

Supporter copy in these three languages is often **adapted rather than translated**: a marketing sentence is rewritten for the reader. Take the terms from the tables below, and write each sentence the way the language says it, not the way the English or another language built it.

## The core term family

German and French use a **godparent** word. Italian uses a **support** word, the standard framing of the Italian third sector.

| EN | de | fr_CH | it |
|---|---|---|---|
| sponsorship | Patenschaft | parrainage | sostegno (a distanza) |
| sponsor (noun) | Pate / Patin | parrain / marraine | sostenitore |
| sponsored child | Patenkind | enfant parrainé / filleul(e) | bambino che sostieni |
| to sponsor | eine Patenschaft übernehmen | parrainer | sostenere |
| become a sponsor | Pate werden | devenir parrain | diventa sostenitore |
| ex-sponsor | Ex-Pate | ancien parrain | ex sostenitore |
| Sponsorship Plus | Patenschaft Plus | Parrainage Plus | Sostegno Plus |

German and French need **paired forms** where the sponsor's gender is unknown: `Patin oder Pate`, `parrain ou marraine`, `filleul(e)`. Use them rather than the masculine alone.

## Money

All three keep *gift* and *donation* apart:

| EN | de | fr_CH | it |
|---|---|---|---|
| gift (a present for a child) | Geschenk | cadeau | regalo |
| donation (money to a fund) | Spende | don | donazione |
| contribution (monthly payment) | Beitrag | contribution | contributo |
| amount | Betrag | montant | importo |
| fund | Fonds | fonds | fondo |

## Renamed programmes

These three languages **renamed** two programmes rather than translating them. Keep the renames:

| EN | de | fr_CH | it |
|---|---|---|---|
| Gift of compassion | Geschenke der Hoffnung | Cadeaux d'espoir | Regali di speranza |
| Compassion survival program | Überlebensprogramm für Mütter und Babys | Programme de survie pour les mamans et les bébés | Programma di sopravvivenza per mamme e neonati |

The child's Compassion site is a **centre**, where English says *project*: `Mein Zentrum`, `Mon centre`, `Il mio centro`.

## Form of address

| | address | note |
|---|---|---|
| `de` | **`du`**, throughout | A deliberate brand choice, imperatives included: `Werde Pate`, `Schreib deinem Patenkind`. A formal `Sie` in existing text is a leftover, not a precedent. |
| `fr_CH` | **`vous`** by default | `tu` only in the Write&Pray content for under-25s. |
| `it` | **`tu`** | |

## Writing conventions

- German uses **Swiss spelling**: `ss`, never `ß` (`Schliessen`, `weiss`, `Strasse`, `Grosszügigkeit`).
- French puts a space before `? ! :`. Apply it consistently through a text.
- Interface buttons are **infinitive** in German and French (`Hinzufügen`, `Ajouter`) and **imperative** in Italian (`Aggiungi`).
- German, French and Italian write `2FA` out as a phrase (two-factor authentication).
- Example names: `Max Mustermann` (de), `Jean Dupont` (fr), `Mario Rossi` (it), in place of `John Doe`.

## Traps in the MyCompassion portal strings

Each of these has already been mistranslated once:

- **"Code"** on the signup form is the **postal code** (`input_id="zip"`), not a child reference.
- **"Coordinates"** is **contact details** (French *coordonnées*). German `Koordinaten` and Italian `Coordinate` are wrong; French `Coordonnées` is right.
- **"I'm in"** is "I'm in [grade 4]", a school level, not "count me in". German `Ich gehe in die` is right.
- German slipped back to the loanword `Sponsor` in two backend field labels. Use `Pate` there too.
- Translate `aria-label` as well as `title` on the same element.
