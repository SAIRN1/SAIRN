---
name: sairn-doc-intelligence
description: >
  Universal SAIRN document scanning and intelligence engine. Trigger on ANY of:
  "scan a document", "photo a bill", "upload a document", "read this invoice",
  "scan medical records", "upload EOB", "read this contract", "photo the invoice",
  "document scanner", "scan a check", "read this form", "photo a receipt",
  "scan insurance", "read lab results", "upload permit", "scan lien waiver",
  "document intelligence", "doc scan", "bill scanner", "medical document",
  "scan anything", or any request to photograph, upload, or analyze any paper document
  in any SAIRN app. This skill governs: the LiDAR vs camera truth (camera wins for flat
  documents, LiDAR assists autofocus only), Claude vision document classification,
  field extraction by document type, app routing logic, and the universal Document
  Intelligence panel that appears in every SAIRN app. Works on every phone.
  No special hardware required. Tap, photo, Claude reads it in seconds.
---

# SAIRN Document Intelligence

> *"Any document. Any app. Photo it. Claude reads it. Done."*

## The LiDAR Truth for Documents

LiDAR fires laser pulses at depth. A flat document has no depth to scan.
LiDAR does NOT read documents. What LiDAR does for documents:
- Makes iPhone Pro autofocus 6x faster in low light
- Helps camera stabilize over document surface
- Enables better edge detection

What reads the document: Claude vision. Camera captures. Claude extracts.

User-facing message:
"SAIRN Document Intelligence uses your camera — enhanced by LiDAR on iPhone Pro —
to photograph any document. Claude reads it instantly and routes it to the right place."

## Document Types Per App

### StoneDesk
Customer invoices, material POs, slab receipts, template sketches,
customer credit applications, lien waivers, permits.

### SAIRNbuild
Sub invoices, lien waivers, building permits, change orders, subcontracts,
inspection reports, blueprint sheets, safety incident reports,
material delivery tickets, insurance certificates.

### SAIRNlaw
Contracts, billing statements, court filings, settlement agreements,
retainer agreements, demand letters, deposition notices, corporate resolutions.

### SAIRNscape
Landscape proposals, plant invoices, irrigation permits, property surveys,
maintenance contracts, snow removal agreements, HOA approval letters.

### SAIRNbiz
W-2/W-4, pay stubs, I-9, direct deposit forms, vendor invoices,
bank statements, check images, 1099s, business licenses, insurance certificates.

### SAIRNcode
EOBs, superbills, medical records, prior authorizations,
claim denial letters, remittance advice.

### SAIRNcare
Care plans, physician orders, HIPAA authorizations,
medication administration records, incident reports, insurance cards.

### SAIRNvet
DEA logs, controlled substance invoices, patient records,
vaccination certificates, rabies certificates, lab results, surgical consents.

### SAIRNfuneral
Death certificates, funeral service contracts, burial permits,
pre-need contracts, obituary drafts.

## Claude Document Intelligence Prompt

```
You are the SAIRN Document Intelligence Engine.
A user has photographed a document. Your job:

1. IDENTIFY: What specific document type is this?
2. EXTRACT: Every field — names, dates, amounts, reference numbers, signatures present Y/N
3. CLASSIFY: Which SAIRN app (StoneDesk/SAIRNbuild/SAIRNlaw/SAIRNscape/SAIRNbiz/
   SAIRNcode/SAIRNcare/SAIRNvet/SAIRNfuneral)?
4. FLAG: Missing signatures, expired dates, math errors, incomplete fields
5. ACTION: Recommend exactly what to do with this document

OUTPUT FORMAT:
DOCUMENT TYPE: [specific type]
APP: [SAIRN app]
CONFIDENCE: [HIGH/MEDIUM/LOW]

EXTRACTED DATA:
[field]: [value]
...

FLAGS:
[issues or "None detected"]

RECOMMENDED ACTION:
[what to do]
```

## API Call Pattern

```javascript
async function sairnScanDocument(imageBase64, appId) {
  const res = await fetch('https://sairn.vercel.app/api/claude', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      app_id:   appId || 'sairn-doc',
      is_demo:  true,
      system:   DOC_INTEL_SYSTEM,  // prompt above
      messages: [{
        role: 'user',
        content: [
          { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: imageBase64 }},
          { type: 'text',  text: 'Scan and analyze this document.' }
        ]
      }]
    })
  });
  const data = await res.json();
  return data.content?.[0]?.text || '';
}
```

## UI: Universal Doc Scan Modal

Every app gets:
- "Scan Document" in sidebar (one tap)
- Camera capture modal
- Auto-analysis on photo capture
- Save to client file / print / share
- Document history per app

## Guardian Checklist

- [ ] Camera capture: accept="image/*,application/pdf" capture="environment"
- [ ] File to base64 client-side before API call
- [ ] API call via proxy only -- never api.anthropic.com
- [ ] app_id matches current app
- [ ] is_demo: true on every call
- [ ] try/catch on every fetch
- [ ] content?.[0]?.text null-safe extraction
- [ ] Results save to localStorage with app prefix
- [ ] Print button present on result
- [ ] Reset/scan-another button present

## Integration in SAIRNscan Standalone

SAIRNscan gets a 5th tab: Document Mode
Tabs: [LiDAR Scan] [Blueprint Photo] [PDF Upload] [Manual Entry] [Doc Scan]

In Doc mode: scan any document, Claude identifies and extracts, save or share.
Works for any contractor without a specific SAIRN vertical.

## Supabase Table

```sql
CREATE TABLE document_scans (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  app_id text NOT NULL,
  doc_type text,
  app_route text,
  extracted_data jsonb,
  flags text,
  recommended_action text,
  created_at timestamptz DEFAULT now(),
  user_role text
);
```

*SAIRN Document Intelligence: Any document. Any app. Photo it. Claude reads it.*
