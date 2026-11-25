# Polish (`pl_PL`)

There is no official Compassion Polish glossary. This one was derived from the MyCompassion portal's strings in the seven languages that already shipped, by carrying the *intention* behind their word choices into Polish. It is also the worked example of `new-language.md`: its rejected alternatives show the tests a term has to pass.

## The core term family: `patronat`

`patronat` is the Polish sibling of `Pate` and `parrain`, the godparent family the other languages use.

| EN | PL | note |
|---|---|---|
| sponsorship | **patronat** | countable: `patronat / patronaty / patronatów` |
| sponsor (noun) | **patron** | backend and admin text only |
| sponsored child | **dziecko objęte patronatem** | model names and legal text |
| your sponsored child | **Twoje dziecko** | in warm copy: the context already says which child, and the long form reads bureaucratic |
| to sponsor a child | **objąć dziecko patronatem** | |
| become a sponsor | **rozpocząć patronat** | gender-neutral, unlike `zostać patronem` |
| Sponsor me | **Obejmij mnie patronatem** | gender-neutral |
| you are sponsoring | **obejmujesz patronatem** | |
| Sponsorship Plus / Sponsorship+ | **Patronat Plus / Patronat+** | localised, as German, French and Italian do |

Polish precedent for this family: **SOS Wioski Dziecięce** runs "Patron SOS" and "Patron Rodzin", and **Ruch Maitri** describes its own programme as *"objęcie patronatem ubogiego dziecka"*. PWN defines `patronat` as *"sprawowanie opieki nad kimś"*. `patron` also means *patron saint*, a quiet plus in a Christian context.

The cost: `objąć patronatem` is slightly formal and reads institutional in warm copy. That is why `Twoje dziecko` stands wherever the English says *your sponsored child*, and the long form is kept for model names.

### Rejected alternatives

| Rejected | Why |
|---|---|
| `sponsor` / `sponsoring` / `sponsorowane dziecko` | The loanword `sponsoring` carries a well-known pejorative sense when it is about people. |
| `adopcja na odległość` / `adopcja serca` | The dominant term in the Polish sector, but Compassion refuses adoption wording for this relationship. |
| `opiekun` / `podopieczny` | Statutory guardianship terms in Polish family law (Kodeks rodzinny i opiekuńczy): they claim a legal status sponsorship does not have. The same goes for `zaopiekować się dzieckiem`. |
| `wsparcie` / `wspierane dziecko` (the Italian model) | Fails on countability. "My sponsorships", "Ended sponsorships", "Number of sponsorships" need a plural count noun, and `wsparcia` is unnatural. |

## Form of address: informal `Ty`, **capitalised**

Address the reader in the **second person singular** (`możesz`, `Twoje dziecko`), never `Pan/Pani`:

- `Pan/Pani` forces gender agreement on adjectives and participles, and the reader's gender is unknown.
- The present tense of the second person singular is gender-neutral.
- The child-voice timeline, "Sponsor me" and the prayer commitments are meant to read as intimate; a formal register reads wrong there.

Direct-address pronouns are **capitalised**: `Ty, Ciebie, Tobie, Cię, Ci, Twój, Twoja, Twoje, Twoim, Twojego, Twoich`. Verbs stay lowercase, and the reflexive `swój` is never capitalised. This courtesy marker is what makes informal address acceptable to readers who would expect `Pan/Pani`. Evidence:

- Odoo's own Polish uses 141 capitalised `Twój` forms against 19 lowercase, and no `Pan/Pani` in its portal, website or signup modules.
- Polish NGO donor copy (SOS, Caritas, Salezjanie, Maitri, UNICEF, Szlachetna Paczka) capitalises almost unanimously.
- The Microsoft Polish style guide prescribes it; the Rada Języka Polskiego calls it *"nie tylko poprawne, ale wręcz wskazane"*.

Backend strings (field labels, model names) stay impersonal noun phrases, with no second person.

## Money: three distinct words

| EN | PL |
|---|---|
| gift (a present sent to a child) | **prezent** |
| donation (money to a fund) | **darowizna** |
| contribution (the monthly payment) | **wpłata** |
| Open contributions (unpaid instalments) | **Do zapłaty** |
| Monthly contribution | **Wpłata miesięczna** |
| Monthly / One-time gifts (money) | **Darowizny miesięczne / jednorazowe** |
| Giving / donation limits | **Limity darowizn** |
| fund | **fundusz** |
| amount | **kwota** |

"Gift of compassion" is **`dar nadziei`**, following the German, French and Italian rename to *Gifts of Hope*.

## Other settled vocabulary

| EN | PL |
|---|---|
| letter / letters | list / listy |
| correspondence | korespondencja |
| template | szablon |
| draft | wersja robocza |
| inbox | skrzynka |
| pray for | modlić się za |
| child protection charter | karta ochrony dziecka |
| church partner / frontline church partner | kościół partnerski / lokalny kościół partnerski |
| community | społeczność |
| project (the child's Compassion centre) | projekt |
| testimony (a faith testimony) | świadectwo |
| impact statement | opis wpływu |
| salutation (the Mr/Mrs field) | zwrot grzecznościowy |
| poverty / extreme poverty | ubóstwo / skrajne ubóstwo |
| released from poverty | uwolnione od ubóstwa |
| hope / encouragement | nadzieja / otucha |
| payment method / payment mode | metoda płatności / tryb płatności |
| dashboard / my hub | panel / moja strona |
| contact details ("Coordinates" in the portal) | Dane kontaktowe |

## Traps

- Timeline labels would need gendered past-tense verbs. Write them as **noun phrases**: `Otrzymany prezent`, `Dotarł twój list`, `Nowy list do ciebie`, `Początek patronatu`.
- A string ending in a preposition is followed by a child's name that Polish cannot inflect. The children's names are mostly non-Slavic and stay undeclined, so use the natural case and leave the name as it is.
- The sponsorship-search filters (`I'd like to sponsor a`, `Between the ages of`, `Who lives in`) are three **separate** headings, not one sentence. Translate them as standalone labels, so the gender buttons (`Chłopiec` / `Dziewczynka`) stay nominative.
- **"Either"** is the boy-or-girl filter option: `Obojętnie`.
- **"From" / "To"** on the letter card are sender and recipient, followed by a name.
- **"Statement"** on an impact line is the bullet's text: `Treść`, not `Oświadczenie`.
- `obciążyć` takes the accusative: `obciążyć kartę`, never `obciążyć na czymś`.
- `dewocjonalia` are rosaries and holy medals, not devotionals. `Bóg zapłać` means *thank you*, not *God bless*; that is `Niech Bóg Ci błogosławi`.
- Polish has **three** plural forms where English has two. Ages use the abbreviation **`l.`**, correct after every numeral (`3 l.`, `62 l.`), because `lat` is wrong after 2 to 4. Where a count cannot agree, restructure: `Twoje aktywne patronaty:` + N.

## Writing conventions

- Sentence case for headings, menus and buttons, never English Title Case.
- Buttons are imperative: `Zapisz`, `Wyślij`, `Anuluj`.
- Polish quotation marks: `„ ”`.
- `&` joining two nouns becomes **`i`**.
- `2FA` stays as the acronym.
- Example name: `Jan Kowalski`, in place of `John Doe`.
