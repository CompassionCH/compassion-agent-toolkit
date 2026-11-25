# Nordic: Swedish, Norwegian, Danish, Finnish (`sv_SE`, `nb_NO`, `da_DK`, `fi_FI`)

The terms the Nordic offices agreed in their existing translations of the MyCompassion portal. Use them as settled; do not re-decide them.

## The core term family

All four use a **godparent** word.

| EN | sv_SE | nb_NO | da_DK | fi_FI |
|---|---|---|---|---|
| sponsorship | fadderskap | fadderskap | fadderskab | kummius |
| sponsor (noun) | fadder | fadder | fadder | kummi |
| sponsored child | fadderbarn | fadderbarn | fadderbarn | kummilapsi |
| become a sponsor | bli fadder | bli fadder | bliv fadder | ryhdy kummiksi |
| sponsor a child | bli fadder till ett barn | bli fadder for et barn | bliv fadder for et barn | ryhdy lapsen kummiksi |
| ex-sponsor | tidigare fadder | tidligere fadder | tidligere fadder | entinen kummi |

**Close compounds.** Swedish, Norwegian and Danish write compounds as one word: `fadderskapsbetalningar`, not `fadderskaps betalningar`. A split compound is the most common mistake in these languages, and it changes the meaning. Finnish compounds too: `kummiuslahja`, `kummilapsi`.

## Money

Swedish, Norwegian and Danish use one word for both *gift* and *donation* (`gåva` / `gave`), so **their wording cannot tell you which of the two a text means.** Finnish keeps them apart and is the reliable Nordic reference:

| EN | sv_SE | nb_NO | da_DK | fi_FI |
|---|---|---|---|---|
| gift (a present for a child) | gåva | gave | gave | **lahja** |
| donation (money to a fund) | gåva | gave | gave | **lahjoitus** |
| contribution (the monthly payment) | bidrag | bidrag | bidrag | maksu |
| amount | belopp | beløp | beløb | summa |
| fund | fond | fond | fond | rahasto |

"Open contributions" means *unpaid instalments*.

## Gift types

| EN | sv_SE | nb_NO | da_DK | fi_FI |
|---|---|---|---|---|
| Birthday gift | Födelsedagsgåva | Bursdagsgave | Fødselsdagsgave | Syntymäpäivälahja |
| Family gift | Familjegåva | Familiegave | Familiegave | Perhelahja |
| General gift | Allmän gåva | Generell gave | Generel gave | Yleislahja |
| Graduation/Final gift | Examens-/avslutningsgåva | Avslutnings-/sluttgave | Dimissions-/afslutningsgave | Valmistumis-/päätöslahja |
| Gift Basket | Gåvokorg | Gavekurv | Gavekurv | Lahjakori |

## Letters

| EN | sv_SE | nb_NO | da_DK | fi_FI |
|---|---|---|---|---|
| letter | brev | brev | brev | kirje |
| write a letter | skriv ett brev | skriv et brev | skriv et brev | kirjoita kirje |
| correspondence | brevväxling | brevveksling | breve | kirjeenvaihto |
| template | mall | mal | skabelon | malli |
| inbox | inkorg | innboks | indbakke | postilaatikko |

Danish uses *breve* for correspondence; the others have a separate letter-exchange word.

## Other settled terms

| EN | sv_SE | nb_NO | da_DK | fi_FI |
|---|---|---|---|---|
| child protection charter | barnskyddspolicy | erklæring om barns beskyttelse | børnebeskyttelseserklæring | lastensuojelun periaatteet |
| church partner | kyrkopartner | kirkepartner | kirkepartner | kirkkokumppani |
| community | samhälle | lokalsamfunn | lokalsamfund | yhteisö |
| project (the child's centre) | projekt | prosjekt | projekt | projekti |
| testimony (a faith story) | vittnesmål | vitnesbyrd | vidnesbyrd | todistus |
| payment method | betalningsmetod | betalingsmåte | betalingsmetode | maksutapa |
| payment mode | betalningssätt | betalingsmåte | betalingsmåde | maksumuoto |

## Form of address

All four use **`du`** / **`sinä`**: none has a formal second person in current use.

Danish and Norwegian keep the politeness marker in prompts (`venligst`, `vennligst`); Swedish and Finnish drop it. English "Please select" is `Vælg venligst` in Danish but plain `Välj` in Swedish.

## Writing conventions

- `2FA` stays as the acronym.
- Example names: `Anna Andersson` (sv), `Ola Nordmann` (nb), `Jens Jensen` (da), `Matti Meikäläinen` (fi), in place of `John Doe`.
- **Open decision:** "Sponsorship Plus" stays in English in Swedish and Finnish but is `Fadder Plus` in Norwegian and Danish. Ask before changing either; the communication team decides.

## Traps in the MyCompassion portal strings

Each of these has already been mistranslated once:

- **"Salutation"** is the Mr/Mrs title field, not a greeting. Norwegian and Danish `Tiltale` and Finnish `Puhuttelu` are right; Swedish `Hälsning` is wrong.
- **"Medium"** is the marketing channel of a campaign, not "medium-sized" (Finnish `Keskisuuri` is wrong). "Medium Amount" does mean mid-sized.
- **"Code"** on the signup form is the **postal code** (`input_id="zip"`).
- **"Coordinates"** is **contact details** (French *coordonnées*), not a map position. All four languages have it as coordinates (`Koordinater`, `Koordinaatit`), which is wrong.
- **"I'm in"** is "I'm in [grade 4]", a school level.
- **"Either"** is the boy-or-girl filter option.
- Timeline event labels speak from the child's side in the past tense and are shared across children: avoid anything that must agree with the child's gender.
