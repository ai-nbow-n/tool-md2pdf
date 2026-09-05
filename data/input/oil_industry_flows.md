# Oil Industry — Flows & Market Dynamics

A visual reference for the main physical and commercial flows in the global oil industry,
from upstream extraction to end-consumer products and financial markets.

---

## 1. Upstream to Downstream — Physical supply chain

```mermaid
graph TD
  RES["Reservoir / Oil Field"]
  EXP["Exploration & Drilling"]
  PRD["Crude Production / Lifting"]
  SEP["Separation Plant / GOSP"]
  CRD["Crude Oil Storage"]
  EXP_T["Export Terminal"]
  TAN["VLCC / Tanker"]
  IMP["Import Terminal / SPM"]
  REF["Refinery"]
  FRAC["Fractionation Columns"]
  LPG["LPG"]
  NAP["Naphtha"]
  KER["Kerosene / Jet Fuel"]
  DSL["Diesel / Gasoil"]
  FO["Fuel Oil / Residuals"]
  BTM["Bitumen / Lube Base"]
  TERM["Product Terminal"]
  RET["Retail / End Consumer"]

  RES --> EXP --> PRD --> SEP --> CRD
  CRD --> EXP_T --> TAN --> IMP --> REF
  REF --> FRAC
  FRAC --> LPG
  FRAC --> NAP
  FRAC --> KER
  FRAC --> DSL
  FRAC --> FO
  FRAC --> BTM
  LPG --> TERM
  NAP --> TERM
  KER --> TERM
  DSL --> TERM
  FO --> TERM
  BTM --> TERM
  TERM --> RET
```

---

## 2. Crude oil pricing & trading flow

```mermaid
graph LR
  PROD["Producer / NOC / IOC"]
  SPOT["Spot Market / ICE Brent / NYMEX WTI"]
  TRAD["Trading House / Commodity Desk"]
  HEDG["Futures / Options Hedging"]
  PRIC["Price Benchmark / Platts / Argus"]
  REF2["Refiner / Buyer"]
  SETTL["Physical Settlement / Delivery"]
  FIN["Financial Settlement / Cash diff"]

  PROD -->|"term contract / spot cargo"| SPOT
  SPOT --> TRAD
  TRAD -->|"buys hedge"| HEDG
  HEDG -->|"marks to market"| PRIC
  PRIC -->|"assessed price"| SPOT
  TRAD -->|"sells physical cargo"| REF2
  REF2 -->|"receives cargo"| SETTL
  TRAD -->|"rolls / closes position"| FIN
```

---

## 3. Refinery internal flows — Conversion units

```mermaid
graph TD
  CDU["CDU - Crude Distillation Unit"]
  VDU["VDU - Vacuum Distillation"]
  NHT["Naphtha Hydrotreater"]
  CCR["CCR Platformer / Reformer"]
  HCK["Hydrocracker"]
  FCC["FCC - Fluid Catalytic Cracker"]
  DHT["Diesel Hydrotreater"]
  AKU["Alkylation Unit"]
  SRU["SRU - Sulfur Recovery"]
  BLEND["Blending / Mixing Header"]
  OUT_G["Gasoline Pool"]
  OUT_D["Diesel Pool"]
  OUT_J["Jet / Kerosene Pool"]

  CDU -->|"light naphtha"| NHT
  CDU -->|"heavy naphtha"| CCR
  CDU -->|"gasoil"| DHT
  CDU -->|"atm residue"| VDU
  VDU -->|"VGO"| HCK
  VDU -->|"VGO"| FCC
  NHT -->|"treated naphtha"| BLEND
  CCR -->|"reformate"| BLEND
  HCK -->|"cracked naphtha"| BLEND
  HCK -->|"cracked diesel"| DHT
  FCC -->|"FCC naphtha"| BLEND
  FCC -->|"LCO"| DHT
  FCC -->|"isobutylene"| AKU
  DHT -->|"ULSD"| OUT_D
  AKU -->|"alkylate"| BLEND
  BLEND --> OUT_G
  CDU -->|"kerosene cut"| OUT_J
  SRU -.->|"sulfur byproduct"| CDU
  SRU -.->|"sulfur byproduct"| DHT
```

---

## 4. OPEC+ production decision cycle

```mermaid
sequenceDiagram
  participant MON as Monitoring Committee (JMMC)
  participant MIN as Ministerial Meeting
  participant NOC as National Oil Companies
  participant MKT as Oil Market / ICE/NYMEX
  participant IEA as IEA / Analysts

  IEA->>MON: Supply-demand data / inventory levels
  MON->>MIN: Compliance report + market outlook
  MIN->>MIN: Deliberate quota adjustment
  MIN->>NOC: New production targets
  NOC->>MKT: Adjust lifting / export volumes
  MKT->>IEA: Price signal / flow data
  MKT->>MON: Market reaction (price, inventories)
```

---

## 5. LNG value chain — Gas to market

```mermaid
graph LR
  WELL["Gas Well / Reservoir"]
  PROC["Gas Processing Plant"]
  LIQ["Liquefaction Plant / Train"]
  LNG_T["LNG Loading Terminal"]
  SHP["LNG Carrier / Q-Flex / Q-Max"]
  REG["Regasification Terminal / FSRU"]
  GRID["Gas Transmission Grid"]
  POW["Power Plant / Gas Turbine"]
  IND["Industrial Consumer"]
  RES2["Residential / City Gas"]

  WELL -->|"wet gas"| PROC
  PROC -->|"lean gas"| LIQ
  PROC -->|"NGL / condensate"| LIQ
  LIQ -->|"-162 C liquid"| LNG_T
  LNG_T -->|"cargo load"| SHP
  SHP -->|"ocean voyage"| REG
  REG -->|"regasified"| GRID
  GRID --> POW
  GRID --> IND
  GRID --> RES2
```

---

## 6. Oil market information flow — From wellhead to price

```mermaid
graph TD
  FIELD["Field Operations / SCADA"]
  METER["Custody Transfer Metering"]
  NOM["Nomination / Scheduling"]
  SHIP["Shipping Agent / Port Log"]
  SURV["Independent Inspector / SGS / Bureau Veritas"]
  PRICE_RPT["Price Reporting Agency / Platts eWindow"]
  EXCH["Exchange / ICE / CME"]
  TRAD2["Trader Desk / ETRM System"]
  RISK["Risk Management / VaR"]
  FIN2["Finance / P&L / MTM"]

  FIELD -->|"volumes / quality"| METER
  METER -->|"bill of lading"| NOM
  NOM -->|"voyage order"| SHIP
  SHIP -->|"arrival notice"| SURV
  SURV -->|"certificate of quality"| PRICE_RPT
  PRICE_RPT -->|"assessed price"| EXCH
  EXCH -->|"settlement price"| TRAD2
  TRAD2 -->|"open positions"| RISK
  RISK -->|"exposure report"| FIN2
  TRAD2 -->|"trade ticket"| FIN2
```
