# Carrier Routing — Booking Backend Map

Used by `scripts/book.py` to decide which backend handles a given carrier.
IATA airline code → backend.

## duffel

Legacy / flag carriers with NDC distribution through Duffel. Bookable
end-to-end via API. Sandbox key works for all of these in test mode.

| IATA | Carrier               | Notes                              |
|------|-----------------------|------------------------------------|
| TP   | TAP Air Portugal      | Star Alliance                      |
| EI   | Aer Lingus            |                                    |
| BA   | British Airways       |                                    |
| IB   | Iberia                |                                    |
| AF   | Air France            |                                    |
| KL   | KLM                   |                                    |
| LH   | Lufthansa             |                                    |
| LX   | Swiss                 |                                    |
| OS   | Austrian              |                                    |
| SN   | Brussels Airlines     |                                    |
| AY   | Finnair               |                                    |
| SK   | SAS                   |                                    |
| AZ   | ITA Airways           |                                    |
| UX   | Air Europa            |                                    |
| TK   | Turkish Airlines      |                                    |
| EK   | Emirates              |                                    |
| QR   | Qatar Airways         |                                    |
| AA   | American Airlines     |                                    |
| DL   | Delta                 |                                    |
| UA   | United                |                                    |
| AC   | Air Canada            |                                    |

If a carrier not listed here returns offers in a Duffel offer-request,
treat it as duffel-supported and add it here.

## browser

API-blocked carriers requiring browser automation. Per-carrier driver
under `scripts/drivers/`. Each driver fills the checkout up to the
payment page, then stops for human SCA / 3DS.

| IATA | Carrier               | Driver status   |
|------|-----------------------|-----------------|
| FR   | Ryanair               | not built (v2)  |
| U2   | easyJet               | not built (v2)  |
| W6   | Wizz Air              | not built (v2)  |
| VY   | Vueling               | not built (v2)  |
| W9   | Wizz Air UK           | not built (v2)  |

## manual

No API, no robust browser path. Dispatcher prints a deep-link and the
user books by hand.

| Category                  | Notes                                  |
|---------------------------|----------------------------------------|
| Award / points bookings   | Airline portals, alliance award space  |
| Hidden city (Skiplagged)  | TOS-risk; never auto-book              |
| Charter / unusual routes  | Unknown distribution                   |

## Default

Unknown IATA → manual. Surface the dispatch decision and let the user
override via `--backend duffel|browser|manual`.
