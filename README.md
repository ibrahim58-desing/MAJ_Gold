# MAJ GOLD — Inventory Management System

Gold manufacturing unit software for tracking the full production flow
from raw gold receipt to finished jewellery stock.

## Project Structure

```
maj_gold/
│
├── database/
│   ├── models/
│   │   ├── base.py            # SQLAlchemy engine, session, Base class
│   │   ├── masters.py         # Dealers, Workers, Teams, ProductType, DesignType, AlloyType
│   │   ├── daybook.py         # DaybookEntry — central double-entry ledger
│   │   ├── stock.py           # GoldReceipt, MeltBatch, MeltBatchAlloy, SolderReturn
│   │   ├── gold_box.py        # GoldBoxStock, GoldBoxIssue, GoldBoxDailyBalance
│   │   ├── process.py         # WireSheet, Goldsmith, GoldsmithWorkerLog,
│   │   │                      # GoldsmithDesignLog, Polish, Faceting, Kambi
│   │   ├── stock_register.py  # FinishedStock, ChainStock, TagStock, StockSummaryDaily
│   │   ├── ledger.py          # LedgerAccount, LedgerEntry
│   │   └── v_account.py       # VAccountEntry, VAccountDailyBalance
│   │
│   └── init_db.py             # Creates tables + seeds master data
│
├── services/                  # Business logic (separate from UI)
│   ├── daybook_service.py     # Create/query daybook entries
│   ├── melt_service.py        # Melt batch creation + alloy tracking
│   ├── goldsmith_service.py   # Goldsmith batch + worker log + pay calc
│   ├── faceting_service.py    # Faceting batch + V account management
│   ├── stock_service.py       # Stock summary + gold box balance
│   └── report_service.py      # GS-CLOSING, GS-PCS, Ledger report generation
│
├── ui/
│   ├── pages/
│   │   ├── daybook_page.py    # DAYBOOK sheet UI
│   │   ├── tot_stock_page.py  # TOT STOCK sheet UI
│   │   ├── gs_closing_page.py # GS-CLOSING sheet UI
│   │   ├── ledger_page.py     # LEDGER sheet UI
│   │   └── gs_pcs_page.py     # GS-PCS sheet UI
│   └── widgets/               # Reusable PyQt6 widgets
│
├── reports/                   # PDF/Excel report templates
├── utils/                     # Date helpers, weight calculators, validators
├── config/                    # App config, DB path, company info
├── requirements.txt
└── main.py                    # App entry point
```

## Database Tables

### Masters
| Table | Purpose |
|---|---|
| dealers | Gold suppliers (SJU, DL, ML) |
| workers | All factory workers (GS-*, FAC-*, KAMBI) |
| teams | Goldsmith & faceting teams |
| product_types | CHAIN, BOX, FACTORY, PURSE, 999, 995 |
| design_types | KCN, SEEMA, BABY, 4S, FS30, 30INC |
| alloy_types | SILVER, COPPER, EXTRA COPPER, ZINC, EXTRA ZINC |

### Core Ledger
| Table | Maps to Sheet |
|---|---|
| daybook_entries | DAYBOOK — INVENTORY DAY BOOK |
| ledger_accounts | LEDGER — account master |
| ledger_entries | LEDGER — per-account running entries |
| v_account_entries | V ACCOUNT entries (faceting workers) |
| v_account_daily_balance | STOCK_SUM — V ACCOUNT section |

### Raw Gold & Melting
| Table | Purpose |
|---|---|
| gold_receipts | Dealer deliveries (RECEIPT 24K - SJU/999) |
| melt_batches | NG MELTING + SCRAP MELTING sessions |
| melt_batch_inputs | Which receipts went into which melt |
| melt_batch_alloys | ADDED ALLOY - SILVER/COPPER/ZINC etc |
| solder_returns | Scrap from each process, tracked by source |

### Gold Box
| Table | Maps to Sheet |
|---|---|
| gold_box_stock | Gold added into the gold box |
| gold_box_issues | Gold issued to workers (any process) |
| gold_box_daily_balance | STOCK_SUM — GOLD BOX section |

### Process Chain
| Table | Process |
|---|---|
| wire_sheet_batches | Wire drawing + sheet rolling |
| goldsmith_batches | Goldsmith batch (debit/credit/loss) |
| goldsmith_worker_logs | Per-worker per-day log (GS-CLOSING) |
| goldsmith_design_logs | Per-worker per-design pcs (GS-PCS) |
| polish_batches | Polish (no weight loss tracked) |
| faceting_batches | Faceting (GS-CLOSING faceting section) |
| kambi_batches | Kambi / linking process |

### Stock
| Table | Maps to Sheet |
|---|---|
| finished_stock | Final jewellery stock |
| chain_stock | CHAIN STOCK entries in LEDGER |
| tag_stock | TAG NO items (TOT STOCK header) |
| stock_summary_daily | STOCK_SUM — all three sections |

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialise database (creates maj_gold.db + seeds master data)
python -m database.init_db

# 3. Run the application
python main.py
```

## Sheets to Build (Phase 1)
- [x] Schema designed
- [x] DAYBOOK page
- [x] TOT STOCK page
- [x] GS - CLOSING page
- [x] LEDGER page
- [x] GS - PCS page
