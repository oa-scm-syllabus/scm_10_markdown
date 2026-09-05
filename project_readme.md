# TaskFlow

**TaskFlow** je *jednoduchý* nástroj pro správu úkolů. Starší verze CLI byla ~~napsaná v Perlu~~, dnes je v Pythonu.

## Obsah

- [Funkce](#funkce)
- [Instalace](#instalace)

## Funkce

- Rychlé přidávání úkolů
  1. Přes CLI
  2. Přes konfigurační soubor
- Filtrování podle štítků
- Export do CSV
- Notifikace na e-mail

## Instalace

1. Nainstalujte Python 3.11+
2. Nainstalujte balíček přes `pip`
3. Spusťte inicializaci

```bash
pip install taskflow-cli
```

## Použití

Spusťte příkaz `taskflow add "Nový úkol"`.

## Konfigurace

| Parametr | Výchozí hodnota |
|----------|------------------|
| `--limit` | 50 |
| `--format` | table |
| `--verbose` | false |

## Ukázky a odkazy

![TaskFlow logo](https://example.com/logo.png)
![TaskFlow badge][badge]

[badge]: https://example.com/badge.png

Více v [dokumentaci](https://example.com/docs) nebo v [repozitáři][repo].

[repo]: https://example.com/repo

## Ohlasy uživatelů

> TaskFlow mi ušetřil hodiny práce každý týden.

## Řešení častých problémů

<details>
<summary>Nástroj nejde spustit</summary>

Zkontrolujte, že máte nainstalovaný Python 3.11+.

</details>

## Roadmapa

- [x] CLI základ
- [x] Export do CSV
- [ ] Webové rozhraní
- [ ] Mobilní aplikace

---

Aktuální verze je 1.2.0[^1].

[^1]: Licencováno pod MIT.
