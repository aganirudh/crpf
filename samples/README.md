# Sample data

This folder will hold the demo tender + 10 mock bidder bundles used by `make seed`. Replace any of the placeholders here with real (redacted) procurement documents to test PRAMAAN end-to-end.

Layout:

```
samples/
├── README.md
└── tender_construction_2026/
    ├── tender.txt                 ← human-readable sample text (you can use this to author a PDF)
    ├── tender.pdf                 ← (you provide) a typed PDF of the same text
    └── bidders/
        ├── bidder_01_abc/
        │   ├── audited_fs_2023_24.pdf
        │   ├── ca_certificate.pdf
        │   ├── gst_rc.pdf
        │   ├── iso9001_cert.pdf
        │   └── completion_certs/...
        ├── bidder_02_xyz/
        │   └── ...
        └── ...
```

For Round 2 W1–W2 you only need `tender.pdf`. The bidder folders kick in at W3 when the Excavator lands.
