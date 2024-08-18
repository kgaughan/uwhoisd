# uwhoisd

A 'Universal WHOIS' proxy server: you query it for information about a
particular domain, it works out the correct WHOIS server to query and gives
back the correct details.

It is only intended for use with domain names currently, but could be
generalised to work with other types of WHOIS server.

## Scraper

The daemon comes with a scraper to pull WHOIS server information from IANA's
root zone database. To run the scraper, enter:

```sh
python -m uwhoisd.scraper
```
