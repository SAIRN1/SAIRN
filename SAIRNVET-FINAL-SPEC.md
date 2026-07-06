# SAIRNvet — FINAL Claude Code Build Spec
## The World's Most Complete Veterinary Platform
## Every Species. Every Diagnosis. Every Medication.
## Date: July 6, 2026

---

## MISSION

Build `sairnvet.html` — the single greatest veterinary platform ever created.
Covers: companion animal, equine, large animal, exotic, zoo, wildlife, aquatic, avian, reptile, every species on earth.
Contains: 2,000+ diagnoses, 500+ medications, AI engine covering every drug and diagnosis that exists.
50 panels. Guardian-clean. Single HTML file. Push with vercel.json.

---

## IRON LAWS

1. GitHub REST API only: blob → tree → commit → ref — NEVER git push
2. Single HTML file — everything inline
3. No Unicode box-drawing chars (─ │ ╔ ═ └ etc.)
4. No dark backgrounds — light bg (#FFFFFF, #F8FAFC), dark text (#0F172A)
5. No alert() — showToast() only
6. All localStorage keys prefixed sv_
7. All Claude calls through proxy — never api.anthropic.com
8. -webkit-print-color-adjust:exact on all colored elements
9. escHtml() on all dynamic content
10. No duplicate HTML IDs
11. Update vercel.json in same commit

---

## FILE IDENTITY

| Property | Value |
|----------|-------|
| File | sairnvet.html |
| App ID | sairnvet |
| Color | #7C3AED |
| Dark | #5B21B6 |
| Tint | #EDE9FE |
| Proxy | https://sairn.vercel.app/api/claude |
| Supabase | https://ejrlrrkvhtllxbbypdjb.supabase.co |
| Supabase Key | sb_publishable_zQhcnpkmw2IJoIoKbnfFwA_tV_1PtoX |
| License Prefixes | SV-, DEMO-, SAIRN-, VET- |
| Demo Key | SV-PINNACLE-2026 |
| Demo PIN Owner | 1234 |
| Demo Clinic | Pinnacle Animal Hospital — Cleveland, OH |

---

## SAIRN CLAUDE ENGINE — Copy Exactly

```javascript
var APP_ID = 'sairnvet';
var PROXY  = 'https://sairn.vercel.app/api/claude';

function showToast(msg, dur) {
  var t = document.getElementById('sv-toast');
  t.textContent = msg; t.classList.add('show');
  clearTimeout(t._to);
  t._to = setTimeout(function(){ t.classList.remove('show'); }, dur||3000);
}
function escHtml(s){
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function svStore(k,v){try{localStorage.setItem('sv_'+k,JSON.stringify(v));}catch(e){}}
function svLoad(k,d){try{var r=localStorage.getItem('sv_'+k);return r?JSON.parse(r):d;}catch(e){return d;}}

async function callClaude(system, messages, maxTokens) {
  try {
    var res = await fetch(PROXY, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        app_id:APP_ID, is_demo:true,
        system:system, messages:messages,
        max_tokens:maxTokens||1000
      })
    });
    var data = await res.json();
    if(data.error==='demo_limit'||(typeof data.error==='string'&&data.error.includes('limit'))){
      showToast('Demo limit reached. Email michael@sairn.com for a license.',6000);
      throw new Error('demo_limit');
    }
    if(!res.ok){
      var em=(data.error&&data.error.message)?data.error.message:(typeof data.error==='string'?data.error:'Error '+res.status);
      showToast('Claude: '+em,4000); throw new Error(em);
    }
    var text='';
    if(data.content&&data.content[0]&&data.content[0].text) text=data.content[0].text;
    if(!text){showToast('Empty response — try again.',3000);throw new Error('empty');}
    return text;
  } catch(e){
    if(e.message!=='demo_limit'&&e.message!=='empty') showToast('Connection error.',4000);
    throw e;
  }
}
```

---

## COMPLETE MEDICATION DATABASE
### Store as JS array: var SV_DRUGS = [...]
### Each entry: {name, generic, class, species[], controlled, schedule, category}

#### COMPANION ANIMAL — CANINE & FELINE (120+ drugs)

ANTIBIOTICS:
Amoxicillin 250mg/500mg — Penicillin — Dog/Cat
Amoxicillin-Clavulanate (Clavamox) — Penicillin+BLI — Dog/Cat
Cephalexin 250mg/500mg — Cephalosporin — Dog/Cat
Cefpodoxime (Simplicef) — Cephalosporin — Dog/Cat
Enrofloxacin (Baytril) — Fluoroquinolone — Dog/Cat (caution kittens/puppies)
Marbofloxacin (Zeniquin) — Fluoroquinolone — Dog/Cat
Pradofloxacin (Veraflox) — Fluoroquinolone — Cat
Doxycycline — Tetracycline — Dog/Cat
Minocycline — Tetracycline — Dog/Cat
Clindamycin (Antirobe) — Lincosamide — Dog/Cat
Metronidazole — Nitroimidazole — Dog/Cat
Trimethoprim-Sulfamethoxazole (SMZ-TMP) — Sulfonamide — Dog/Cat
Chloramphenicol — Amphenicol — Cat (use caution)
Azithromycin — Macrolide — Dog/Cat
Tylosin — Macrolide — Dog/Cat
Rifampin — Rifamycin — Dog/Cat (combination therapy)
Florfenicol — Amphenicol — Dog/Cat

NSAIDs & PAIN:
Carprofen (Rimadyl) — NSAID — Dog
Meloxicam (Metacam) — NSAID — Dog/Cat
Grapiprant (Galliprant) — EP4 receptor antagonist — Dog
Robenacoxib (Onsior) — NSAID — Dog/Cat
Deracoxib (Deramaxx) — NSAID — Dog
Mavacoxib (Trocoxil) — NSAID — Dog
Piroxicam — NSAID — Dog (oncology use)
Tramadol — Opioid-like — Dog/Cat
Gabapentin — Anticonvulsant/Analgesic — Dog/Cat
Pregabalin (Lyrica/Liavium) — Anticonvulsant/Analgesic — Dog/Cat
Amantadine — NMDA antagonist — Dog/Cat
Acetaminophen — TOXIC TO CATS — Dog ONLY — FLAG RED WARNING FOR CATS
Buprenorphine — Opioid — Dog/Cat — DEA Schedule III
Butorphanol — Opioid agonist-antagonist — Dog/Cat — DEA Schedule IV
Hydromorphone — Opioid — Dog/Cat — DEA Schedule II
Morphine — Opioid — Dog/Cat — DEA Schedule II
Fentanyl — Opioid — Dog/Cat — DEA Schedule II
Methadone — Opioid — Dog/Cat — DEA Schedule II

STEROIDS & IMMUNOSUPPRESSIVES:
Prednisone/Prednisolone — Corticosteroid — Dog/Cat
Dexamethasone — Corticosteroid — Dog/Cat
Methylprednisolone — Corticosteroid — Dog/Cat
Triamcinolone — Corticosteroid — Dog/Cat
Cyclosporine (Atopica) — Calcineurin inhibitor — Dog/Cat
Azathioprine — Immunosuppressive — Dog (NOT Cat — fatal)
Mycophenolate — Immunosuppressive — Dog/Cat
Chlorambucil — Alkylating agent — Dog/Cat (oncology)
Lokivetmab (Cytopoint) — IL-31 monoclonal antibody — Dog
Oclacitinib (Apoquel) — JAK inhibitor — Dog

CARDIAC:
Enalapril — ACE inhibitor — Dog/Cat
Benazepril — ACE inhibitor — Dog/Cat
Furosemide (Lasix) — Loop diuretic — Dog/Cat
Torsemide — Loop diuretic — Dog/Cat
Spironolactone — Aldosterone antagonist — Dog/Cat
Amlodipine (Amodip) — Calcium channel blocker — Cat (hypertension)
Digoxin — Cardiac glycoside — Dog/Cat
Pimobendan (Vetmedin) — Inodilator — Dog/Cat
Diltiazem — CCB — Dog/Cat (arrhythmia)
Atenolol — Beta blocker — Dog/Cat
Sotalol — Beta blocker — Dog
Mexiletine — Antiarrhythmic — Dog
Torasemide — Diuretic — Dog/Cat

ENDOCRINE:
Insulin Regular — Insulin — Dog/Cat
Insulin NPH — Insulin — Dog
Insulin Glargine (Lantus) — Insulin — Cat preferred
Insulin PZI — Insulin — Cat preferred
Methimazole (Felimazole) — Antithyroid — Cat
Levothyroxine (Soloxine) — Thyroid hormone — Dog (hypothyroid)
Trilostane (Vetoryl) — Adrenal steroid inhibitor — Dog (Cushing's)
Mitotane (Lysodren) — Adrenolytic — Dog (Cushing's)
Deslorelin implant — GnRH agonist — Dog/Cat
Melatonin — Hormone — Dog (alopecia X, Cushing's alternative)

NEUROLOGICAL & BEHAVIORAL:
Phenobarbital — Anticonvulsant — Dog/Cat — DEA Schedule IV
Potassium Bromide — Anticonvulsant — Dog
Levetiracetam (Keppra) — Anticonvulsant — Dog/Cat
Zonisamide — Anticonvulsant — Dog/Cat
Imepitoin (Pexion) — Anticonvulsant — Dog (Europe/UK)
Diazepam — Benzodiazepine — Dog/Cat — DEA Schedule IV
Midazolam — Benzodiazepine — Dog/Cat — DEA Schedule IV
Clonazepam — Benzodiazepine — Dog/Cat — DEA Schedule IV
Alprazolam — Benzodiazepine — Dog/Cat — DEA Schedule IV
Fluoxetine (Reconcile) — SSRI — Dog/Cat
Clomipramine (Clomicalm) — TCA — Dog/Cat
Trazodone — SARI — Dog/Cat
Amitriptyline — TCA — Dog/Cat
Buspirone — Azapirone — Dog/Cat
Tasipimidine (Tessie) — Alpha-2 agonist — Dog (noise aversion — NEW 2026)
Dexmedetomidine oral gel — Alpha-2 agonist — Dog/Cat (noise aversion)
Selegiline (Anipryl) — MAO-B inhibitor — Dog (CDS/Cushing's)

ANESTHESIA & SEDATION:
Ketamine — Dissociative — Dog/Cat/Most species — DEA Schedule III
Tiletamine-Zolazepam (Telazol) — Dissociative — Dog/Cat/Wildlife — DEA Schedule III
Propofol — IV anesthetic — Dog/Cat
Alfaxalone (Alfaxan) — Neurosteroid — Dog/Cat
Dexmedetomidine (Dexdomitor) — Alpha-2 agonist — Dog/Cat
Medetomidine — Alpha-2 agonist — Dog/Cat
Xylazine — Alpha-2 agonist — Dog/Cat/Horse/Cattle
Acepromazine — Phenothiazine — Dog/Cat (caution brachycephalics)
Atipamezole (Antisedan) — Alpha-2 antagonist/reversal — Dog/Cat
Yohimbine — Alpha-2 antagonist/reversal — Dog/Cat/Wildlife
Isoflurane — Inhalant — All species
Sevoflurane — Inhalant — All species
Atropine — Anticholinergic — Dog/Cat/Most species
Glycopyrrolate — Anticholinergic — Dog/Cat

PARASITICIDES:
Ivermectin — Avermectin — Dog/Cat (CAUTION MDR1/ABCB1 mutation dogs)
Milbemycin oxime — Avermectin — Dog/Cat
Selamectin (Revolution) — Avermectin — Dog/Cat
Moxidectin — Avermectin — Dog/Cat
Afoxolaner (NexGard) — Isoxazoline — Dog
Fluralaner (Bravecto) — Isoxazoline — Dog/Cat
Sarolaner (Simparica) — Isoxazoline — Dog
Lotilaner (Credelio) — Isoxazoline — Dog/Cat
Pyrantel pamoate — Tetrahydropyrimidine — Dog/Cat
Fenbendazole (Panacur) — Benzimidazole — Dog/Cat
Praziquantel — Anthelmintic — Dog/Cat
Epsiprantel — Anthelmintic — Dog/Cat
Febantel — Benzimidazole — Dog/Cat
Spinosad (Comfortis) — Spinosyn — Dog/Cat

GI & METABOLIC:
Metoclopramide — Prokinetic/antiemetic — Dog/Cat
Maropitant (Cerenia) — NK1 antagonist antiemetic — Dog/Cat
Ondansetron — 5-HT3 antagonist — Dog/Cat
Omeprazole — PPI — Dog/Cat
Pantoprazole — PPI — Dog/Cat
Famotidine — H2 blocker — Dog/Cat
Sucralfate — Mucosal protectant — Dog/Cat
Misoprostol — Prostaglandin — Dog/Cat (GI protection)
Cisapride — Prokinetic — Cat (compounded)
Lactulose — Osmotic laxative — Dog/Cat
Docusate sodium — Stool softener — Dog/Cat
Psyllium — Fiber — Dog/Cat
Kaolin-Pectin — Adsorbent — Dog/Cat
Ursodiol — Bile acid — Dog/Cat (liver disease)
SAMe — Hepatoprotectant — Dog/Cat
Silymarin — Hepatoprotectant — Dog/Cat
Tylosin — GI antibiotic — Dog/Cat
Cobalamin (B12) — Supplement — Dog/Cat (EPI, IBD)

DERMATOLOGY:
Cytopoint (Lokivetmab) — IL-31 mAb — Dog
Apoquel (Oclacitinib) — JAK inhibitor — Dog
Hydroxyzine — Antihistamine — Dog/Cat
Diphenhydramine — Antihistamine — Dog/Cat
Chlorpheniramine — Antihistamine — Dog/Cat
Cetirizine — Antihistamine — Dog/Cat
Lime sulfur — Antifungal/antiparasitic dip — Dog/Cat
Ketoconazole — Antifungal — Dog/Cat
Fluconazole — Antifungal — Dog/Cat
Itraconazole — Antifungal — Dog/Cat
Terbinafine — Antifungal — Dog/Cat
Clindamycin (topical) — Antibiotic — Dog/Cat
Mupirocin — Antibiotic topical — Dog/Cat

OPHTHALMOLOGY:
Tobramycin eye drops — Antibiotic — Dog/Cat
Ofloxacin eye drops — Antibiotic — Dog/Cat
Dexamethasone eye drops — Steroid — Dog/Cat
Prednisolone acetate eye drops — Steroid — Dog/Cat
Dorzolamide — Carbonic anhydrase inhibitor — Dog/Cat (glaucoma)
Timolol — Beta blocker eye drop — Dog/Cat (glaucoma)
Latanoprost — Prostaglandin eye drop — Dog (glaucoma)
Cyclosporine eye ointment (Optimmune) — Immunosuppressive — Dog (KCS)
Tacrolimus eye drops — Immunosuppressive — Dog/Cat (KCS)
Pilocarpine — Cholinergic — Dog/Cat
Atropine eye drops — Anticholinergic — Dog/Cat
Artificial tears — Lubricant — Dog/Cat

ONCOLOGY:
Vincristine — Vinca alkaloid — Dog/Cat
Vinblastine — Vinca alkaloid — Dog/Cat
Cyclophosphamide — Alkylating agent — Dog/Cat
Chlorambucil — Alkylating agent — Dog/Cat
Lomustine (CCNU) — Alkylating agent — Dog/Cat
Carboplatin — Platinum compound — Dog/Cat
Doxorubicin — Anthracycline — Dog/Cat
Toceranib (Palladia) — Tyrosine kinase inhibitor — Dog
Masitinib (Kinavet) — Tyrosine kinase inhibitor — Dog
L-asparaginase — Enzyme — Dog/Cat
Prednisolone — Steroid (oncology) — Dog/Cat
Piroxicam — NSAID (transitional cell carcinoma) — Dog

VACCINES (reference list):
Dog: Rabies, DA2PP (Distemper/Adeno/Parvo/Parainfluenza), Bordetella, Leptospirosis (4-way), Lyme, Canine Influenza (H3N2/H3N8), CRT
Cat: Rabies, FVRCP (Herpes/Calici/Panleukopenia), FeLV, FIV, Chlamydia, Bordetella

---

#### EQUINE (60+ drugs)

NSAIDs & PAIN:
Phenylbutazone (Bute) 1g tabs/paste — NSAID — Horse/Pony
Flunixin meglumine (Banamine) — NSAID — Horse/Pony (NEVER IM — slough risk)
Meloxicam (Metacam Equine) — NSAID — Horse
Firocoxib (Equioxx) — COX-2 NSAID — Horse
Ketoprofen — NSAID — Horse
Suxibuzone — NSAID prodrug — Horse (Europe)
Diclofenac liposomal cream (Surpass) — Topical NSAID — Horse
Butorphanol — Opioid — Horse — DEA Schedule IV
Detomidine (Dormosedan) — Alpha-2 agonist/sedative-analgesic — Horse
Romifidine — Alpha-2 agonist — Horse
Xylazine (Rompun) — Alpha-2 agonist — Horse (0.5-1.1 mg/kg IV)
Acepromazine — Phenothiazine — Horse (caution stallions — paraphimosis)

SEDATION & ANESTHESIA:
Ketamine — Dissociative — Horse — DEA Schedule III
Guaifenesin (GGE) — Muscle relaxant — Horse (Triple Drip)
Diazepam — Benzodiazepine — Horse (foals, neonates) — DEA Schedule IV
Midazolam — Benzodiazepine — Horse — DEA Schedule IV
Isoflurane — Inhalant — Horse
Tiletamine-Zolazepam (Telazol) — NOT recommended equine — note in system
Atipamezole — Alpha-2 reversal — Horse (off-label)
Yohimbine — Alpha-2 reversal — Horse (off-label)

ANTIBIOTICS:
Penicillin G Procaine — Penicillin — Horse (22,000 IU/kg IM BID)
Ampicillin — Penicillin — Horse
Trimethoprim-Sulfamethoxazole (SMZ) — Sulfonamide — Horse
Enrofloxacin — Fluoroquinolone — Horse (off-label, foals)
Gentamicin — Aminoglycoside — Horse (intrauterine use, systemic foals)
Amikacin — Aminoglycoside — Horse
Metronidazole — Nitroimidazole — Horse
Ceftiofur (Naxcel/Excenel) — Cephalosporin — Horse
Doxycycline — Tetracycline — Horse
Chloramphenicol — Amphenicol — Horse (eye, compounded)

JOINT & MUSCULOSKELETAL:
Polysulfated glycosaminoglycan (Adequan) — DMOAD — Horse (intramuscular)
Hyaluronic acid (Legend) — Intraarticular/IV — Horse
Corticosteroids intraarticular: Triamcinolone, Methylprednisolone, Betamethasone — Horse
IRAP (autologous conditioned serum) — Biologic — Horse
PRP (platelet-rich plasma) — Biologic — Horse
Stem cell therapy — Biologic — Horse

GI & COLIC:
Mineral oil — Lubricant/laxative — Horse (nasogastric tube)
Magnesium sulfate — Saline laxative — Horse (NG tube)
Buscopan (hyoscine) — Antispasmodic — Horse (colic)
N-butylscopolammonium bromide — Antispasmodic — Horse
Neostigmine — Cholinergic — Horse (ileus)
Bethanechol — Cholinergic — Horse (ileus)
Omeprazole (GastroGard/UlcerGard) — PPI — Horse (gastric ulcers)
Sucralfate — Mucosal protectant — Horse
Misoprostol — Prostaglandin — Horse (colonic ulcers)
Psyllium — Fiber — Horse (sand colic prevention)

RESPIRATORY:
Furosemide (Salix) — Loop diuretic — Horse (EIPH — racing)
Dexamethasone — Corticosteroid — Horse
Prednisolone — Corticosteroid — Horse
Fluticasone inhaler — ICS — Horse (heaves/IAD — Aeromask)
Clenbuterol (Ventipulmin) — Beta-2 agonist bronchodilator — Horse
Albuterol inhaler — Bronchodilator — Horse (Aeromask)

REPRODUCTIVE:
Oxytocin — Hormone — Mare (uterine contraction, milk letdown)
Prostaglandin F2-alpha (Lutalyse) — PGF2a — Mare (luteolysis)
Deslorelin acetate (Ovuplant/Sucromate) — GnRH — Mare (ovulation induction)
hCG (Chorulon) — Hormone — Mare (ovulation induction)
Progesterone (Regu-Mate/Altrenogest) — Progestogen — Mare — EXTREME HUMAN SAFETY WARNING
Estradiol cypionate — Estrogen — Mare
Testosterone — Androgen — Stallion
Prostaglandin E2 (cervical dilation) — Prostaglandin — Mare

PARASITICIDES:
Ivermectin (Zimecterin/Equell) — Avermectin — Horse (0.2 mg/kg)
Moxidectin (Quest) — Avermectin — Horse (do NOT use in foals <6mo or debilitated)
Pyrantel pamoate (Strongid) — Tetrahydropyrimidine — Horse
Fenbendazole (Panacur) — Benzimidazole — Horse (5-day larvicidal dose 10 mg/kg)
Praziquantel (Equimax) — Anthelmintic — Horse (tapeworms)
Oxibendazole — Benzimidazole — Horse

ANTIPARASITIC/ANTIPROTOZOAL:
Ponazuril (Marquis) — Antiprotozoal — Horse (EPM)
Diclazuril (Protazil) — Antiprotozoal — Horse (EPM)
Nitazoxanide (Navigator) — Antiprotozoal — Horse (EPM)

VACCINES EQUINE:
EEE/WEE/VEE, West Nile Virus, Tetanus, Rabies, Equine Influenza, Equine Herpesvirus (EHV-1/4), Strangles (Streptococcus equi), Potomac Horse Fever, Botulism, Rotavirus (mares for foal protection), Lyme

---

#### FOOD ANIMAL — CATTLE, SWINE, SHEEP, GOATS (50+ drugs)

ANTIBIOTICS:
Oxytetracycline LA-200 — Tetracycline — Cattle/Sheep/Swine (withdrawal time required)
Florfenicol (Nuflor) — Amphenicol — Cattle (BRD)
Ceftiofur (Excenel/Excede) — Cephalosporin — Cattle/Swine
Enrofloxacin (Baytril 100) — Fluoroquinolone — Cattle/Swine
Tulathromycin (Draxxin) — Macrolide — Cattle/Swine (BRD)
Gamithromycin (Zactran) — Macrolide — Cattle
Tildipirosin (Zuprevo) — Macrolide — Cattle/Swine
Danofloxacin (A180) — Fluoroquinolone — Cattle
Ampicillin — Penicillin — Cattle
Penicillin G procaine — Penicillin — Cattle/Sheep/Swine
Sulfadimethoxine — Sulfonamide — Cattle/Poultry
Neomycin — Aminoglycoside — Cattle (oral scours)
Spectinomycin — Aminocyclitol — Swine/Poultry

NSAIDs:
Flunixin meglumine (Banamine) — NSAID — Cattle/Swine (withdrawal time)
Meloxicam — NSAID — Cattle (off-label, widely used)
Ketoprofen — NSAID — Cattle (Europe labeled)
Aspirin — NSAID — Cattle (VFD)

REPRODUCTIVE:
Prostaglandin F2-alpha (Lutalyse/Estrumate) — Cattle/Swine/Sheep
GnRH (Cystorelin/Factrel) — Cattle (synchronization protocols)
Progesterone CIDR — Cattle/Sheep (synchronization)
hCG — Cattle (ovulation)
Oxytocin — Cattle/Swine/Sheep
Cloprostenol — Cattle/Swine

PARASITICIDES:
Ivermectin pour-on/injectable — Cattle/Sheep (withdrawal time)
Doramectin (Dectomax) — Cattle/Sheep
Eprinomectin (Eprinex) — Cattle (zero milk withdrawal)
Moxidectin — Cattle/Sheep
Fenbendazole — Cattle/Sheep/Goats
Albendazole — Cattle/Sheep
Levamisole — Cattle/Sheep
Clorsulon — Cattle (liver flukes)
Diclazuril — Sheep/Goats (coccidiosis)
Amprolium — Cattle/Poultry (coccidiosis)
Decoquinate — Cattle/Goats (coccidiosis prevention)

NUTRITIONAL/METABOLIC:
Calcium borogluconate IV — Cattle (milk fever/hypocalcemia)
Magnesium sulfate IV — Cattle (grass tetany/hypomagnesemia)
Dextrose 50% IV — Cattle (ketosis/hypoglycemia)
Propylene glycol oral — Cattle (ketosis)
Phosphorus (sodium phosphate) — Cattle
Vitamin B12 (Cobalamin) — Cattle/Sheep
Vitamin ADE — Cattle/Sheep/Swine
Selenium/Vitamin E (Bo-Se, MuSe) — Cattle/Sheep (white muscle disease)
Thiamine (B1) — Cattle/Sheep (polioencephalomalacia)
Niacin — Cattle (ketosis prevention)

VACCINES CATTLE:
BVD types 1+2, IBR, PI3, BRSV (5-way), Clostridials (7-way, 8-way), Leptospirosis (5-way), Anthrax, Brucellosis (RB51), Pinkeye (Moraxella bovis), Foot Rot, Bovine Rotavirus/Coronavirus, Salmonella

---

#### EXOTIC SPECIES — SMALL MAMMALS (30+ drugs)

Rabbits, Ferrets, Guinea Pigs, Chinchillas, Hamsters, Gerbils, Rats, Mice, Hedgehogs, Sugar Gliders, Prairie Dogs:

ANTIBIOTICS:
Enrofloxacin — All exotic small mammals
Trimethoprim-Sulfamethoxazole — All exotic small mammals
Doxycycline — Rabbits, ferrets, rodents
Chloramphenicol — Rabbits, rodents
Azithromycin — Ferrets, rabbits
Metronidazole — Rabbits, ferrets
Penicillin — NOTE: FATAL in guinea pigs, chinchillas, hamsters — FLAG RED
Amoxicillin — NOTE: FATAL in guinea pigs, chinchillas, rabbits — FLAG RED
Lincomycin — NOTE: FATAL in guinea pigs, hamsters — FLAG RED

NSAIDs:
Meloxicam — All exotic small mammals (0.2-0.5 mg/kg depending on species)
Carprofen — Rabbits, ferrets, rodents

GI:
Metoclopramide — Rabbits (GI stasis)
Cisapride (compounded) — Rabbits (GI stasis)
Simethicone — Rabbits (gas)
Cholestyramine — Rabbits (enterotoxemia prevention)
Benebac/probiotics — All small mammals

ANESTHESIA:
Midazolam — All small mammals — DEA Schedule IV
Ketamine — All small mammals — DEA Schedule III (often combined with midazolam or dexmedetomidine)
Isoflurane — All small mammals (induction chamber)
Alfaxalone — All small mammals
Buprenorphine — All small mammals — DEA Schedule III

ANTIPARASITIC:
Fenbendazole — Rabbits, rodents (E. cuniculi — rabbits: 20 mg/kg x 28 days)
Ivermectin — Ferrets, rabbits, rodents (NOT oral in rabbits)
Selamectin — Ferrets, rabbits, rodents
Piperazine — Rodents (roundworms)

ENDOCRINE/OTHER:
Insulin — Ferrets (insulinoma)
Leuprolide acetate — Ferrets (adrenal disease)
Deslorelin implant — Ferrets (adrenal disease)
Mitotane — Ferrets (adrenal disease off-label)
Cabergoline — Rabbits (uterine adenocarcinoma adjunct)

---

#### AVIAN (40+ drugs)

Parrots, Raptors, Waterfowl, Poultry, Songbirds, Ratites:

ANTIBIOTICS:
Doxycycline — All birds (Chlamydiosis/Psittacosis TREATMENT OF CHOICE)
Enrofloxacin — All birds
Trimethoprim-Sulfamethoxazole — All birds
Azithromycin — Parrots, raptors
Amoxicillin — Parrots, poultry
Chloramphenicol — Parrots (resistance common)
Metronidazole — All birds (Trichomonas)
Tylosin — Poultry, parrots (Mycoplasma)
Danofloxacin — Poultry
Florfenicol — Poultry

ANTIFUNGALS:
Nystatin — All birds (crop candidiasis — Candida)
Voriconazole — All birds (TREATMENT OF CHOICE — Aspergillus)
Itraconazole — All birds (Aspergillus)
Amphotericin B — All birds (severe systemic fungal)
Terbinafine — All birds

NSAIDs/PAIN:
Meloxicam — All birds (0.5-1 mg/kg)
Carprofen — Raptors
Butorphanol — All birds — DEA Schedule IV (0.5-2 mg/kg)
Tramadol — All birds
Buprenorphine — All birds — DEA Schedule III

ANTIPARASITIC:
Ivermectin — All birds (NOT certain species — check)
Pyrantel — Poultry, parrots
Fenbendazole — All birds (5-50 mg/kg — higher doses for some)
Praziquantel — All birds (tapeworms)
Ponazuril — All birds (coccidiosis)
Chloroquine + Primaquine — Raptors (malaria)

CROP/GI:
Metoclopramide — All birds (crop stasis)
Cisapride — All birds (crop stasis)

ANESTHESIA:
Isoflurane — All birds (induction chamber or mask)
Midazolam IM — All birds — DEA Schedule IV
Ketamine IM — All birds — DEA Schedule III (NOT sole agent — combine with midazolam)
Alfaxalone — All birds

---

#### REPTILE & AMPHIBIAN (30+ drugs)

Lizards (Bearded Dragons, Iguanas, Chameleons, Monitors, Geckos)
Snakes (Ball Python, Boa, Corn Snake, Burmese Python, King Cobra)
Chelonians (Tortoises: Sulcata, Russian, Hermann's; Turtles: Red-Eared Slider, Box Turtle)
Crocodilians, Amphibians (Frogs, Salamanders, Axolotl)

NOTE: Ivermectin FATAL in chelonians and some lizards — FLAG RED WARNING

ANTIBIOTICS:
Enrofloxacin — All reptiles (most common)
Trimethoprim-Sulfamethoxazole — All reptiles
Metronidazole — All reptiles (protozoa, anaerobes)
Amikacin — Snakes, lizards (IM — must maintain hydration)
Ceftazidime — Snakes, lizards
Doxycycline — Chelonians, lizards
Azithromycin — Reptiles
Piperacillin — All reptiles (serious infections)

ANTIFUNGALS:
Voriconazole — All reptiles (Nannizziopsis/CANV)
Itraconazole — All reptiles

NSAIDs/PAIN:
Meloxicam — All reptiles (0.1-0.5 mg/kg — adjust by species)
Carprofen — Some reptiles
Butorphanol — All reptiles — DEA Schedule IV (snakes: 1-2 mg/kg)
Morphine — All reptiles — DEA Schedule II
Tramadol — All reptiles

ANTIPARASITIC:
Fenbendazole — All reptiles (NOT chelonians at high doses)
Panacur — All reptiles
Praziquantel — All reptiles (trematodes/cestodes)
Ponazuril — All reptiles (coccidiosis)
Metronidazole — All reptiles (flagellates)
Ivermectin — Lizards, snakes (NEVER chelonians — FATAL)
Pyrantel — All reptiles

ANESTHESIA:
Isoflurane induction chamber — All reptiles
Alfaxalone IM — All reptiles (excellent induction agent)
Ketamine IM — All reptiles — DEA Schedule III (combine with midazolam)
Propofol IV — Monitor lizards, crocodilians
Tiletamine-Zolazepam (Telazol) — Large reptiles/crocodilians — DEA Schedule III

CALCIUM/METABOLIC:
Calcium gluconate — All reptiles (MBD/hypocalcemia)
Vitamin D3 — All reptiles (MBD prevention)
Vitamin A — Chelonians, lizards (hypovitaminosis A — NOT overdose)

---

#### ZOO & WILDLIFE — EXOTIC LARGE ANIMALS (30+ drugs)

Big Cats (Lion, Tiger, Leopard, Cheetah, Jaguar, Cougar)
Bears (Grizzly, Black, Polar, Spectacled)
Primates (Gorilla, Chimpanzee, Orangutan, Macaque, Baboon)
Ungulates (Giraffe, Zebra, Rhino, Hippo, Elephant, Buffalo, Antelope, Deer, Moose, Elk)
Marine Mammals (Dolphin, Seal, Sea Lion, Manatee, Otter)
Ratites (Ostrich, Emu, Rhea, Cassowary)
Marsupials (Kangaroo, Wallaby, Koala, Wombat)
Other: Camelids (Camel, Dromedary), Tapir, Giant Panda, Sloth

IMMOBILIZATION/CAPTURE (ZIMS protocols):
Carfentanil — Opioid — Large ungulates/elephants — DEA Schedule II — EXTREME HAZARD — reversal with naltrexone MANDATORY
Etorphine (M99) — Opioid — Large ungulates/rhino/hippo — DEA Schedule II — EXTREME HAZARD — reversal with diprenorphine
Naltrexone — Opioid reversal — All wildlife
Diprenorphine (M5050) — Opioid reversal — All wildlife
Medetomidine — Alpha-2 agonist — All zoo animals
Dexmedetomidine — Alpha-2 agonist — All zoo animals
Azaperone — Butyrophenone/tranquilizer — Ungulates, swine
Butorphanol — Partial opioid — All zoo animals — DEA Schedule IV
Nalbuphine — Opioid agonist-antagonist — All zoo animals
Tiletamine-Zolazepam (Telazol) — Big cats, bears, primates — DEA Schedule III
Ketamine — Big cats, primates, smaller zoo animals — DEA Schedule III
Medetomidine-Ketamine — Standard combination — Most zoo carnivores/primates
Midazolam — Benzodiazepine — All zoo animals — DEA Schedule IV
Atipamezole — Alpha-2 reversal — All zoo animals
Yohimbine — Alpha-2 reversal — All zoo animals
Flumazenil — Benzodiazepine reversal — All zoo animals

ANTIBIOTICS ZOO:
Amoxicillin-Clavulanate — Primates, big cats, bears
Enrofloxacin — All zoo animals
Trimethoprim-Sulfamethoxazole — All zoo animals
Doxycycline — All zoo animals (Chlamydia, zoonotic diseases)
Metronidazole — All zoo animals
Ceftiofur — Large ungulates
Oxytetracycline — Large ungulates, marine mammals
Chloramphenicol — Birds, exotics

NSAIDs ZOO:
Meloxicam — All zoo animals (dose varies significantly by species)
Flunixin meglumine — Large ungulates
Ketoprofen — Large ungulates, marine mammals
Carprofen — Primates, big cats
Aspirin — Elephants, marine mammals

ELEPHANT-SPECIFIC:
Heroin (diacetylmorphine) — Elephant sedation adjunct (very specialized, international protocols)
Etorphine — Elephant immobilization — DEA Schedule II
DMSO — Topical carrier — Elephants
Vitamin E/Selenium — Elephants (white muscle disease)
Oxytocin — Female elephants (dystocia, milk production)
Antibiotics for foot care: broad-spectrum, topical

MARINE MAMMAL:
Diazepam — Cetaceans, pinnipeds — DEA Schedule IV
Midazolam — Cetaceans, pinnipeds — DEA Schedule IV
Meloxicam — Cetaceans, pinnipeds
Trimethoprim-Sulfamethoxazole — Marine mammals
Enrofloxacin — Marine mammals
Voriconazole — Marine mammals (fungal)
Vitamin supplements: C, E, B complex — Marine mammals

---

## COMPLETE DIAGNOSIS DATABASE
### Store as JS array: var SV_DIAGNOSES = [...]
### Each entry: {name, species[], system, icd_category, common_drugs[], severity}
### Organized by body system, searchable by species

IMPLEMENTATION: Build a searchable diagnosis panel with:
1. Species filter dropdown (all 50+ species/groups)
2. Body system filter (12 systems)
3. Search by keyword
4. Click diagnosis → shows: description, common signs, recommended diagnostics, first-line treatment with drugs and doses
5. AI button: "Get full treatment protocol from Claude" for any diagnosis

#### BODY SYSTEMS (12):
1. Integumentary (Skin/Coat/Feathers/Scales/Shell)
2. Musculoskeletal (Bones/Joints/Muscles/Tendons)
3. Cardiovascular (Heart/Vessels)
4. Respiratory (Lungs/Airways/Air Sacs)
5. Gastrointestinal (Mouth/Esophagus/Stomach/Intestines/Liver/Pancreas)
6. Urogenital (Kidneys/Bladder/Reproductive)
7. Neurological (Brain/Spinal Cord/Peripheral Nerves)
8. Endocrine (Thyroid/Adrenal/Pancreas/Pituitary)
9. Ophthalmology (Eyes)
10. Hematology/Oncology (Blood/Cancer)
11. Infectious Disease (Bacterial/Viral/Fungal/Parasitic)
12. Behavioral/Toxicology/Emergency/Other

#### DIAGNOSIS LIST — 2,000+ entries covering all species

COMPANION ANIMAL DIAGNOSES (500+):

INTEGUMENTARY:
Atopic dermatitis (environmental allergy), Food allergy dermatitis,
Flea allergy dermatitis, Contact dermatitis, Sarcoptic mange (Sarcoptes scabiei),
Demodectic mange (Demodex canis/cati), Cheyletiellosis (walking dandruff),
Otodectes cynotis (ear mites), Trombiculosis (chiggers), Ringworm (Microsporum/Trichophyton),
Malassezia dermatitis (yeast), Bacterial folliculitis, Impetigo, Deep pyoderma,
Cellulitis, Sebaceous adenitis, Pemphigus foliaceus, Pemphigus vulgaris,
Discoid lupus erythematosus, Systemic lupus erythematosus, Vasculitis,
Cutaneous lymphoma (epitheliotropic), Mast cell tumor (skin), Lipoma, Histiocytoma,
Perianal fistula, Anal sacculitis, Anal sac adenocarcinoma, Intertrigo (skin fold dermatitis),
Acral lick granuloma, Hyperadrenocorticism (Cushing's — skin signs), Hypothyroidism (skin signs),
Alopecia X, Color dilution alopecia, Pattern baldness, Calcinosis cutis,
Nasal depigmentation (Dudley nose), Vitiligo, Cutaneous papillomatosis, Feline acne,
Feline symmetric alopecia, Feline hyperesthesia syndrome, Feline eosinophilic granuloma complex,
Feline indolent ulcer (eosinophilic ulcer), Feline mosquito bite hypersensitivity,
Injection site sarcoma (cat), Squamous cell carcinoma (skin), Melanoma (skin),
Fibrosarcoma (skin), Periwound contamination, Abscess, Seroma, Hematoma

MUSCULOSKELETAL:
Hip dysplasia, Elbow dysplasia, Osteochondrosis dissecans (OCD), Panosteitis,
Hypertrophic osteodystrophy (HOD), Legg-Calve-Perthes disease, Luxating patella (Gr 1-4),
Cranial cruciate ligament rupture (CCL/ACL), Medial meniscus injury,
Osteosarcoma, Chondrosarcoma, Fibrosarcoma bone, Synovial cell sarcoma,
Bone cyst (simple/aneurysmal), Polyarthritis (immune-mediated), Septic arthritis,
Rheumatoid arthritis, Systemic lupus polyarthritis, Degenerative joint disease (osteoarthritis),
Spondylosis deformans, Lumbosacral stenosis, Cervical spondylomyelopathy (Wobbler syndrome),
Intervertebral disc disease (IVDD Hansen Type I/II), Discospondylitis,
Myositis (masticatory/inflammatory/infectious), Exertional myopathy, Rhabdomyolysis,
Hypokalemic myopathy (cat), Hyperthyroid myopathy (cat), Nutritional myopathy

CARDIOVASCULAR:
Mitral valve disease (MVD/MMVD), Dilated cardiomyopathy (DCM), Hypertrophic cardiomyopathy (HCM — cat),
Restrictive cardiomyopathy (cat), Arrhythmogenic right ventricular cardiomyopathy (Boxer/cat),
Patent ductus arteriosus (PDA), Ventricular septal defect (VSD), Atrial septal defect,
Pulmonic stenosis, Subaortic stenosis, Tetralogy of Fallot, Tricuspid valve dysplasia,
Congestive heart failure (left/right/biventricular), Atrial fibrillation, Ventricular tachycardia,
Sick sinus syndrome, Third-degree AV block, Ventricular premature contractions (VPCs),
Pericardial effusion, Cardiac tamponade, Peritoneopericardial diaphragmatic hernia (PPDH),
Aortic thromboembolism (cat — saddle thrombus), Heartworm disease (Dirofilaria immitis),
Feline heartworm disease, Pulmonary hypertension, Hypertension (systemic), Endocarditis

RESPIRATORY:
Brachycephalic obstructive airway syndrome (BOAS), Elongated soft palate, Stenotic nares,
Tracheal collapse, Bronchitis (chronic), Bronchiectasis, Asthma (feline),
Pneumonia (bacterial/viral/fungal/aspiration), Pneumothorax, Pyothorax (feline/canine),
Pleural effusion, Diaphragmatic hernia, Pulmonary contusion, Pulmonary edema (cardiogenic/non-cardiogenic),
Pulmonary fibrosis, Lung lobe torsion, Primary lung tumor, Pulmonary metastasis,
Chylothorax, Laryngeal paralysis, Tracheal foreign body, Rhinitis (bacterial/viral/fungal/allergic),
Nasal tumor (adenocarcinoma/lymphoma), Nasopharyngeal polyp (cat), Nasopharyngeal stenosis,
Epistaxis, Canine infectious respiratory disease complex (CIRDC/kennel cough),
Feline upper respiratory infection (FHV-1, FCV, Chlamydia, Bordetella),
Canine distemper (respiratory phase), Canine influenza (H3N2/H3N8)

GASTROINTESTINAL:
Dental disease (Grade 1-4), Tooth resorption (feline), Stomatitis (feline chronic gingivostomatitis),
Oral papillomatosis, Oral melanoma, Oral squamous cell carcinoma, Esophageal foreign body,
Megaesophagus, Esophagitis, Vascular ring anomaly, Gastric dilatation-volvulus (GDV/bloat),
Gastritis (acute/chronic), Helicobacter gastritis, Gastric ulcer, Pyloric stenosis,
Gastric adenocarcinoma, Gastric lymphoma, Gastrointestinal foreign body,
Intestinal intussusception, Mesenteric volvulus, Small intestinal bacterial overgrowth (SIBO),
Inflammatory bowel disease (IBD), Protein-losing enteropathy (PLE), Exocrine pancreatic insufficiency (EPI),
Acute pancreatitis, Chronic pancreatitis, Small cell lymphoma (intestinal — cat),
Large cell lymphoma (intestinal), Adenocarcinoma (intestinal), Leiomyosarcoma, GIST,
Hemorrhagic gastroenteritis (AHDS), Parvovirus enteritis (CPV-2), Coronavirus enteritis,
Giardia, Cryptosporidium, Tritrichomonas foetus (cat), Hookworm, Roundworm (Toxocara),
Whipworm (Trichuris), Tapeworm (Dipylidium/Taenia/Echinococcus), Physaloptera,
Megacolon (idiopathic/feline), Constipation/obstipation, Colitis (acute/chronic),
Proctitis, Hepatitis (chronic/acute/vacuolar), Hepatic lipidosis (feline — fatty liver),
Portosystemic shunt (congenital/acquired), Hepatic encephalopathy, Cirrhosis,
Copper-associated hepatopathy, Biliary mucocele, Cholangitis/cholangiohepatitis (cat),
Hepatocellular carcinoma, Hepatic lymphoma, Biliary carcinoma, Splenic hemangiosarcoma,
Splenic mass/nodular hyperplasia, Gastrinoma (Zollinger-Ellison), Insulinoma, Glucagonoma

UROGENITAL:
Urinary tract infection (UTI), Pyelonephritis, Cystitis (idiopathic — FLUTD/FIC),
Urolithiasis (struvite/calcium oxalate/urate/cystine), Urethral obstruction,
Chronic kidney disease (CKD Stage 1-4 IRIS), Acute kidney injury (AKI),
Polycystic kidney disease (PKD — cat), Renal dysplasia, Glomerulonephritis,
Renal amyloidosis, Transitional cell carcinoma (bladder), Renal cell carcinoma,
Prostatic hypertrophy (BPH), Prostatic cyst, Prostatitis, Prostatic carcinoma,
Pyometra (open/closed), Uterine stump pyometra, Vaginal hyperplasia, Vaginitis,
Testicular tumor (Sertoli cell/Leydig/seminoma), Cryptorchidism,
Ovarian cyst/remnant syndrome, Eclampsia (puerperal tetany), Mastitis,
Milk fever, Dystocia, Retained fetus, Subinvolution of placental sites

NEUROLOGICAL:
Epilepsy (idiopathic/structural/reactive), Status epilepticus, Cluster seizures,
Granulomatous meningoencephalomyelitis (GME), Necrotizing meningoencephalitis (NME/NLE),
Eosinophilic meningoencephalitis, Meningitis (bacterial/viral/fungal),
Intervertebral disc disease (cervical/thoracolumbar), Degenerative myelopathy (DM),
Fibrocartilaginous embolism (FCE), Caudal cervical spondylomyelopathy (Wobbler),
Atlantoaxial subluxation/instability, Syringomyelia, Chiari-like malformation (CM/SM),
Lissencephaly, Hydrocephalus, Brain tumor (meningioma/glioma/choroid plexus tumor),
Cognitive dysfunction syndrome (CDS), Vestibular syndrome (peripheral/central/geriatric),
Facial nerve paralysis, Trigeminal neuritis, Brachial plexus avulsion/neoplasia,
Horner's syndrome, Myasthenia gravis, Botulism, Tetanus, Tick paralysis,
Coonhound paralysis (acute polyradiculoneuritis), Toxin-induced neuropathy,
Spinal cord trauma/contusion, Head trauma, Intracranial hypertension

ENDOCRINE:
Diabetes mellitus (Type I/II dog, Type II cat), Diabetic ketoacidosis (DKA),
Hyperosmolar hyperglycemic state, Insulin resistance, Insulinoma,
Hypothyroidism (canine), Hyperthyroidism (feline), Thyroid carcinoma,
Hyperadrenocorticism — PDH (pituitary-dependent), Hyperadrenocorticism — ADH (adrenal-dependent),
Hypoadrenocorticism (Addison's disease), Addisonian crisis, Pheochromocytoma,
Hyperaldosteronism (Conn's syndrome — cat), Hypoparathyroidism, Hyperparathyroidism,
Primary hyperparathyroidism, Hypercalcemia of malignancy, Nutritional secondary hyperparathyroidism,
Acromegaly (feline — GH excess), Growth hormone deficiency, Diabetes insipidus (central/nephrogenic)

OPHTHALMOLOGY:
Corneal ulcer (superficial/deep/melting/descemetocele), Corneal laceration, Corneal foreign body,
Keratoconjunctivitis sicca (KCS — dry eye), Pigmentary keratitis, Corneal dystrophy/degeneration,
Corneal sequestrum (cat), Eosinophilic keratitis (cat), Pannus (chronic superficial keratitis — German Shepherd),
Conjunctivitis (bacterial/viral/allergic/eosinophilic), Entropion, Ectropion, Distichiasis,
Ectopic cilia, Trichiasis, Nasolacrimal duct obstruction, Epiphora,
Glaucoma (primary/secondary), Anterior uveitis, Iris melanoma, Uveal cysts,
Lens luxation (anterior/posterior), Cataract (congenital/juvenile/senile/diabetic),
Retinal detachment (bullous/subtotal/total), Progressive retinal atrophy (PRA),
Sudden acquired retinal degeneration syndrome (SARDS), Hypertensive retinopathy,
Optic neuritis, Iris prolapse, Hyphema, Hypopyon, Horner's syndrome (ocular signs),
Proptosis, Orbital cellulitis, Retrobulbar abscess, Strabismus

HEMATOLOGY/ONCOLOGY:
Immune-mediated hemolytic anemia (IMHA), Non-regenerative anemia, Iron deficiency anemia,
Anemia of chronic disease, Microangiopathic hemolytic anemia, Heinz body anemia,
Immune-mediated thrombocytopenia (ITP), Disseminated intravascular coagulation (DIC),
Von Willebrand disease, Hemophilia A/B, Thrombocytopenia, Thrombocytosis,
Polycythemia vera, Secondary polycythemia, Leukemia (ALL/CLL/AML/CML),
Lymphoma (multicentric/mediastinal/alimentary/extranodal), Multiple myeloma,
Histiocytic sarcoma, Systemic mastocytosis, Hemangiosarcoma (spleen/heart/liver/skin),
Osteosarcoma, Chondrosarcoma, Fibrosarcoma, Soft tissue sarcoma, Melanoma (oral/skin),
Mast cell tumor (Grade 1-3), Perianal gland tumor (adenoma/carcinoma),
Anal sac adenocarcinoma, Mammary gland tumor (benign/malignant), Thymoma,
Transitional cell carcinoma, Renal cell carcinoma, Adrenocortical carcinoma,
Pituitary macroadenoma, Multilobular osteochondrosarcoma, Nasal tumor

INFECTIOUS DISEASE — CANINE:
Canine distemper virus (CDV), Canine parvovirus (CPV-2), Canine adenovirus (CAV-1/2),
Canine coronavirus, Canine influenza H3N2/H3N8, Canine infectious respiratory disease complex,
Rabies, Leptospirosis (L. icterohaemorrhagiae/canicola/pomona/grippotyphosa),
Brucellosis (Brucella canis), Lyme disease (Borrelia burgdorferi),
Ehrlichiosis (Ehrlichia canis), Anaplasmosis (Anaplasma phagocytophilum/platys),
Rocky Mountain Spotted Fever (Rickettsia rickettsii), Bartonellosis,
Blastomycosis, Histoplasmosis, Coccidioidomycosis, Cryptococcosis, Aspergillosis,
Pythiosis, Leishmaniasis (Leishmania infantum), Neosporosis (Neospora caninum),
Toxoplasmosis (Toxoplasma gondii), Babesiosis (Babesia canis),
Hepatozoonosis (Hepatozoon canis/americanum), Trypanosomiasis (Chagas disease)

INFECTIOUS DISEASE — FELINE:
Feline herpesvirus (FHV-1), Feline calicivirus (FCV), Feline panleukopenia virus (FPV),
Feline leukemia virus (FeLV), Feline immunodeficiency virus (FIV),
Feline infectious peritonitis (FIP — SARS-CoV related coronavirus), Feline coronavirus,
Feline infectious anemia (Mycoplasma haemofelis), Feline bartonellosis (B. henselae — cat scratch disease),
Feline toxoplasmosis, Feline cryptococcosis, Feline aspergillosis,
Feline blastomycosis, Feline histoplasmosis, Feline sporotrichosis,
Tritrichomonas foetus (colitis), Feline Chlamydia (Chlamydophila felis),
Cytauxzoonosis (Cytauxzoon felis)

---

EQUINE DIAGNOSES (300+):

MUSCULOSKELETAL/LAMENESS:
Navicular syndrome (podotrochlosis/podotrochlear bursitis/DDFT lesion),
Deep digital flexor tendon (DDFT) lesion, Superficial digital flexor tendon (SDFT) injury,
Suspensory ligament injury (proximal/mid-body/branches), Proximal sesamoiditis,
Distal sesamoid navicular bone fracture, P1/P2/P3 fracture, Coffin joint arthritis (DIP),
Pastern joint arthritis (PIP), Fetlock arthritis (MCP/MTP), Ringbone (high/low),
Bone spavin (distal tarsal OA), Osteochondrosis dissecans (OCD — stifle/hock/fetlock/shoulder),
Subchondral cystic lesion, Carpitis, Bucked shins (dorsal metacarpal disease),
Splints (interosseous desmitis), Curb (plantar tarsal ligament desmitis),
Thoroughpin, Bog spavin, Capped hock/elbow/knee (bursitis),
Stringhalt, Shivers, Muscle contracture, Fibrotic myopathy,
White line disease, Sole abscess, Laminitis (acute/chronic/rotation/sinking),
Equine metabolic syndrome (EMS), PPID (pituitary pars intermedia dysfunction/Cushing's),
White line disease, Seedy toe, Thrush, Canker, Quittor,
Upward fixation of the patella, Gonitis (stifle joint disease),
Sacroiliac joint disease, Kissing spines (overriding dorsal spinous processes),
Supraspinous ligament desmitis, Nuchal ligament disease, Cervical articular process joint disease,
Exertional rhabdomyolysis (ER/tying up), Polysaccharide storage myopathy (PSSM),
Malignant hyperthermia, Hyperkalemic periodic paralysis (HYPP — Quarter Horse)

GASTROINTESTINAL:
Gastric ulcer (EGUS — Grade 0-4), Squamous gastric ulcer, Glandular gastric ulcer,
Pyloric stenosis/stricture, Large colon impaction (feed/sand/enterolith),
Small colon impaction, Cecal impaction, Cecal intussusception,
Right dorsal displacement of the large colon, Left dorsal displacement (nephrosplenic entrapment),
Large colon volvulus, Small intestinal volvulus, Ileal impaction,
Ileus (paralytic/spasmodic), Duodenitis-proximal jejunitis (DPJ/anterior enteritis),
Strangulating obstruction, Mesenteric rent/hernia, Inguinal hernia strangulation,
Colitis X (acute severe colitis), Salmonellosis, Potomac horse fever (Neorickettsia risticii),
Clostridial colitis, Cyathostomiasis (larval/adult), Sand colic, Enterolithiasis,
Malabsorption/protein-losing enteropathy, Eosinophilic gastroenteritis,
Hepatic disease (hepatitis/hepatic lipidosis/serum hepatitis/pyrrolizidine alkaloid toxicity),
Cholelithiasis, Hepatocellular carcinoma, Rectal prolapse, Rectal tear

RESPIRATORY:
Strangles (Streptococcus equi equi), Bastard strangles (disseminated),
Equine influenza (H3N8/H7N7), Equine herpesvirus (EHV-1/4 — respiratory),
EHV-1 myeloencephalopathy (EHM), Equine viral arteritis (EVA),
Hendra virus (Australia), Rhodococcus equi (foals), Rhodococcus pneumonia,
Bacterial pneumonia, Pleuropneumonia, Thoracic abscess, Chylothorax,
Heaves (equine asthma/recurrent airway obstruction/RAO), Inflammatory airway disease (IAD),
Summer pasture-associated obstructive pulmonary disease (SPAOPD),
Dorsal displacement of the soft palate (DDSP), Laryngeal hemiplegia (roarers/Grade 0-6),
Epiglottic entrapment, Arytenoid chondritis, Guttural pouch mycosis,
Guttural pouch empyema, Guttural pouch tympany, Exercise-induced pulmonary hemorrhage (EIPH),
Progressive ethmoid hematoma, Nasal polyp, Nasal tumor, Epistaxis

NEUROLOGICAL:
Equine protozoal myeloencephalitis (EPM — Sarcocystis neurona/Neospora hughesi),
EHV-1 myeloencephalopathy, West Nile virus encephalitis, Eastern/Western equine encephalitis,
Venezuelan equine encephalitis, Equine herpesvirus encephalitis,
Cervical vertebral stenotic myelopathy (Wobbler syndrome), Occipitocervical malformation,
Equine motor neuron disease (EMND), Equine degenerative myeloencephalopathy (EDM),
Polyneuritis equi, Grass sickness (equine dysautonomia), Botulism, Tetanus,
Hyperkalemic periodic paralysis (HYPP), Narcolepsy/cataplexy, Facial nerve paralysis,
Trigeminal neuralgia, Horner's syndrome, Head shaking syndrome

REPRODUCTIVE:
Uterine infection/endometritis (fungal/bacterial), Pyometra, Endometrosis,
Cervical laceration/fibrosis, Perineal laceration/rectovaginal fistula,
Placentitis (bacterial/fungal), Premature placental separation (red bag),
Retained fetal membranes (RFM), Uterine artery hemorrhage, Dystocia,
Umbilical cord abnormalities, Ruptured prepubic tendon, Hydrops allantois/amnion,
Ovarian hematoma, Ovarian tumor (granulosa-theca cell tumor), Testicular tumor,
Cryptorchidism, Scrotal hernia, Penile/preputial injury, Paraphimosis,
Squamous cell carcinoma (penile/preputial), Habronemiasis (penile)

METABOLIC/ENDOCRINE EQUINE:
Pituitary pars intermedia dysfunction (PPID/equine Cushing's),
Equine metabolic syndrome (EMS/insulin dysregulation), Pasture-associated laminitis,
Post-operative/hospital-acquired laminitis, Supporting limb laminitis,
Hyperlipemia (ponies/donkeys/miniatures), Hepatic lipidosis, Exertional heat stroke,
Selenium toxicity, Vitamin E deficiency, Nutritional secondary hyperparathyroidism (big head disease), 
White muscle disease (selenium/Vit E deficiency — foals)

---

LARGE ANIMAL / FOOD ANIMAL DIAGNOSES (200+):

CATTLE:
Bovine respiratory disease complex (BRD/shipping fever — Mannheimia/Pasteurella/Mycoplasma),
Infectious bovine rhinotracheitis (IBR), Bovine viral diarrhea (BVD Types 1/2),
Bovine respiratory syncytial virus (BRSV), Parainfluenza-3 (PI3),
Contagious bovine pleuropneumonia, Lungworm (Dictyocaulus viviparus),
Bovine coronavirus (respiratory), Foot-and-mouth disease (reportable),
Vesicular stomatitis (reportable), Bovine leukemia virus (BLV), Johne's disease (paratuberculosis),
Brucellosis (B. abortus — reportable), Leptospirosis, Q fever (Coxiella burnetii),
Bovine tuberculosis (M. bovis — reportable), Anthrax (B. anthracis — reportable),
Listeriosis, Salmonellosis, E. coli scours (K99), Bovine coronavirus scours,
Rotavirus scours, Cryptosporidiosis (calves), Clostridial diseases (blackleg/malignant edema/black disease/bacillary hemoglobinuria/pulpy kidney/tetanus/botulism),
Bovine ketosis (Type I/II), Milk fever (hypocalcemia/parturient paresis),
Grass tetany (hypomagnesemia), Phosphorus deficiency, Downer cow syndrome,
Hardware disease (traumatic reticuloperitonitis/TRP), Abomasal displacement (LDA/RDA/AV),
Abomasal volvulus, Rumen bloat (frothy/free gas), Rumen acidosis, Rumen alkalosis,
Grain overload (acidosis), Hardware disease, Intestinal volvulus, Intussusception,
Bovine respiratory disease fibrinous pleuropneumonia, Digital dermatitis (Mortellaro/strawberry heel),
Foot rot (Fusobacterium necrophorum), Interdigital hyperplasia, White line disease cattle,
Sole ulcer, Heel horn erosion, Pinkeye (IBK — Moraxella bovis/bovoculi),
Lumpy jaw (Actinomyces bovis), Wooden tongue (Actinobacillus lignieresii),
Bovine leukosis, Squamous cell carcinoma (eye/horn/vulva), Uterine prolapse,
Vaginal prolapse, Retained placenta, Metritis (puerperal), Endometritis, Pyometra,
Ovarian cyst (follicular/luteal), Freemartin, Bovine trichomoniasis (T. foetus — venereal),
Bovine venereal campylobacteriosis (C. fetus — venereal), Vibriosis

SMALL RUMINANTS (SHEEP & GOATS):
Caseous lymphadenitis (CL — Corynebacterium pseudotuberculosis),
Ovine progressive pneumonia (OPP — Maedi-visna), Caprine arthritis-encephalitis (CAE),
Contagious caprine pleuropneumonia, Footrot (Dichelobacter nodosus),
Foot scald (Fusobacterium necrophorum), Contagious ecthyma (orf/soremouth),
Bluetongue (reportable), Ovine enzootic abortion (Chlamydia abortus — Enzootic abortion EAE),
Toxoplasma abortion, Listeria abortion, Salmonella abortion, Q fever abortion,
Scrapie (reportable — prion), Louping ill (tick-borne flavivirus — UK/Europe),
Haemonchus contortus (barber pole worm — FAMACHA scoring), Teladorsagia/Ostertagia,
Trichostrongylus, Nematodirus, Monezia (tapeworm), Liver fluke (Fasciola hepatica),
Lungworm (Muellerius/Dictyocaulus), Coccidiosis (Eimeria), Cryptosporidiosis (kids/lambs),
Polioencephalomalacia (PEM — thiamine deficiency), White muscle disease (selenium/Vit E),
Hypocalcemia (milk fever — ewes/does), Pregnancy toxemia (twin lamb disease/ketosis),
Urinary calculi (urolithiasis — wethers), Enterotoxemia (overeating disease — Cl. perfringens C/D)

SWINE:
Porcine reproductive and respiratory syndrome (PRRS Types 1/2), Swine influenza (H1N1/H3N2/H1N2),
Porcine circovirus disease (PCV2/PCVAD), Porcine epidemic diarrhea (PED),
Transmissible gastroenteritis (TGE), African swine fever (ASF — reportable),
Classical swine fever (CSF — reportable), Foot-and-mouth disease (reportable),
Glasser's disease (Haemophilus parasuis/Glaesserella parasuis), Mycoplasma hyopneumoniae (EP),
Actinobacillus pleuropneumoniae (APP), Atrophic rhinitis (Pasteurella/Bordetella),
Erysipelas (Erysipelothrix rhusiopathiae), Brucellosis (B. suis — reportable),
Swine dysentery (Brachyspira hyodysenteriae), Proliferative enteropathy (Lawsonia intracellularis),
Edema disease (E. coli — F18 fimbriae), Neonatal scours (E. coli K88/K99),
Salmonellosis, Leptospirosis, Pseudorabies (Aujeszky's disease — reportable US),
Streptococcus suis meningitis, Postweaning multisystemic wasting syndrome (PMWS),
Porcine dermatitis nephropathy syndrome (PDNS), Mange (Sarcoptes scabiei var suis),
Lice (Haematopinus suis), Roundworm (Ascaris suum), Kidney worm (Stephanurus dentatus),
Trichinellosis (Trichinella spiralis), Toxoplasmosis, Internal parasitism

---

AVIAN DIAGNOSES (150+):
Psittacosis/Chlamydiosis (Chlamydophila psittaci) — ZOONOTIC
Aspergillosis (Aspergillus fumigatus/flavus) — respiratory/systemic
Avian polyomavirus (APV), Psittacine beak and feather disease (PBFD — circovirus),
Proventricular dilatation disease (PDD — avian bornavirus),
Macaw wasting syndrome, Pacheco's disease (psittacine herpesvirus),
Newcastle disease (PMV-1 — reportable), Avian influenza (HPAI — reportable),
Marek's disease (MDV — lymphoma), Infectious bursal disease (IBD/Gumboro),
Infectious laryngotracheitis (ILT), Infectious bronchitis (IBV), Fowl pox,
Mycoplasma gallisepticum (CRD), Mycoplasma synoviae, Salmonellosis,
Campylobacteriosis, Erysipelas (poultry), Fowl cholera (Pasteurella multocida),
Infectious coryza (Avibacterium paragallinarum), E. coli septicemia (colibacillosis),
Candidiasis (thrush — crop/proventriculus), Trichomoniasis (canker — Trichomonas gallinae),
Giardia (parakeets/cockatiels), Cochlosoma, Cryptosporidiosis (birds),
Coccidiosis (Eimeria spp.), Toxoplasmosis (canaries), Sarcocystis,
Feather destructive behavior (FDB/feather picking), Heavy metal toxicosis (zinc/lead),
Hypovitaminosis A, Gout (articular/visceral), Air sac disease, Egg binding/dystocia,
Yolk coelomitis, Cloacal prolapse, Cloacitis, Papillomatosis (cloacal/oropharyngeal),
Poxvirus (canaries/raptors), Avian gastric yeast (Macrorhabdus/megabacteria),
Proventricular/ventricular impaction, Intestinal intussusception,
Hepatic lipidosis (psittacines), Fatty liver hemorrhagic syndrome (FLHS — poultry),
Atherosclerosis, Lymphoma (psittacines), Fibrosarcoma, Xanthoma, Papilloma, Lipoma,
Sinusitis (bacterial/Chlamydia/Aspergillus), Rhinitis, Airsacculitis,
Hypocalcemia (African Grey — seizures), Thyroid/parathyroid disorders, Diabetes,
Cataracts, Conjunctivitis, Corneal ulcer, Periorbital abscess (raptor — often Aspergillus)

---

REPTILE DIAGNOSES (100+):
Metabolic bone disease (MBD/secondary nutritional hyperparathyroidism) — ALL reptiles
Hypovitaminosis A — Chelonians, lizards (esp. aquatic turtles)
Respiratory infection (viral/bacterial/parasitic/Nidovirus snakes/Sunshine virus),
Infectious stomatitis (mouth rot — bacterial), Inclusion body disease (IBD — boid snakes — arenavirus),
Ophidiomycosis (BIBD/snake fungal disease — Ophidiomyces), Nannizziopsis guarroi (yellow fungus — bearded dragons),
Cryptosporidiosis (Cryptosporidium serpentis — snakes; C. varanii — lizards),
Entamoeba invadens (systemic amebiasis — snakes), Flagellate parasites (Hexamita/Trichomonas),
Oxyurid pinworms (lizards/tortoises), Ascarids, Spirurids, Pentastomids (snakes),
Ectoparasites: Ophionyssus natricis (snake mite), Amblyomma ticks, Trombiculid mites,
Cloacal prolapse, Constipation/intestinal impaction (substrate ingestion — bearded dragons/tortoises),
Dystocia (egg binding), Follicular stasis, Postovulatory coelomitis (POCS),
Thermal burn, Rostral abrasion (snout rub), Anorexia/hibernation anorexia,
Dysecdysis (retained shed), Eye cap retention (spectacle), Pre-ecdysis opacity,
Abscesses (granulomatous/caseous — different from mammals), Abscess — heterophilic response,
Trauma (dog/cat attack, fall, vehicle), Septicemia/bacteremia, Salmonella (asymptomatic carrier — zoonotic),
Viral hemorrhagic disease, Nidovirus (serpentovirus — snakes), Reovirus, Adenovirus,
Chelonian herpesvirus (CHV), Iridovirus (ranavirus — chelonians/amphibians),
Cutaneous papillomatosis, Fibropapillomatosis (sea turtles), Renal disease (reptile — gout),
Hepatic disease, Hypoglycemia (blood glucose management large constrictors),
Cardiovascular disease (dilated/hypertrophic cardiomyopathy snakes/lizards),
Neurological disease (paramyxovirus snakes), Ocular disease (subspectacular abscess, corneal lipidosis chelonians)

---

EXOTIC SMALL MAMMAL DIAGNOSES (150+):
RABBIT:
Encephalitozoon cuniculi (E. cuniculi — neurological/renal/ocular), Pasteurellosis (snuffles — Pasteurella multocida),
GI stasis/ileus, Cecal dysbiosis, Enterotoxemia (Clostridium spiroforme), Mucoid enteropathy,
Uterine adenocarcinoma (unspayed does >2yr — very common), Ovarian cyst/neoplasia,
Uterine aneurysm/polyp, Testicular abscess, Orchitis, Syphilis (Treponema paraluiscuniculi),
Myxomatosis (Myxoma virus — Europe/Australia), Rabbit hemorrhagic disease (RHDV1/RHDV2),
Rabbit calicivirus disease, Head tilt (E. cuniculi/Pasteurella/Toxoplasma),
Dental malocclusion (acquired/congenital), Molar spurs (acquired dental disease),
Fur mites (Cheyletiella parasitovorax), Ear mites (Psoroptes cuniculi), Fleas,
Myiasis (blowfly strike — Lucilia sericata), Coccidiosis (hepatic/intestinal Eimeria),
Pinworm (Passalurus ambiguus), Encephalitozoonosis (renal form), Thymoma, Lymphoma,
Uterine neoplasia, Hepatocellular carcinoma, Hypercalciuria/urolithiasis (calcium sludge),
Obesity, Hepatic lipidosis (secondary to stasis/anorexia), Pododermatis (sore hocks)

FERRET:
Adrenal gland disease (hyperplasia/adenoma/carcinoma), Insulinoma (pancreatic beta cell tumor),
Lymphoma (lymphosarcoma — most common ferret neoplasia), Mast cell tumor (skin),
Fibrosarcoma, Chordoma (tail), Aleutian disease (Aleutian mink disease parvovirus — ADV),
Ferret enteric coronavirus (FECV/ferret systemic coronavirus FRSCV),
Epizootic catarrhal enteritis (ECE — green slime disease), Helicobacter mustelae gastritis,
Proliferative bowel disease (Lawsonia intracellularis), Canine distemper (ferrets highly susceptible),
Influenza (ferrets highly susceptible — zoonotic importance), Rabies, Botulism,
Cardiomyopathy (dilated), Heartworm disease, Splenomegaly, Aplastic anemia (unspayed jills in prolonged estrus),
Urolithiasis (struvite — rare in ferrets; usually dietary), Renal cysts, Chronic renal failure,
Posterior paresis (adrenal/insulinoma/spinal/cardiovascular), Endocrine alopecia,
Dermatophytosis, Sarcoptic mange, Ear mites (Otodectes), Fleas

GUINEA PIG:
Respiratory infection (Bordetella bronchiseptica/Streptococcus pneumoniae),
Cervical lymphadenitis (Streptococcus zooepidemicus — lumps), Scurvy (Vitamin C deficiency),
Urolithiasis (calcium oxalate/struvite), Dental malocclusion (acquired), Trichofolliculoma,
Ovarian cyst (very common in unspayed sows), Dystocia, Pregnancy toxemia, Mastitis,
Bumblefoot (pododermatitis), Lice (Gliricola porcelli/Gyropus ovalis — non-zoonotic),
Mange mites (Trixacarus caviae — pruritic/crusty), Fungal ringworm (Trichophyton),
Lymphoma, Fibrosarcoma, Lipoma, Mammary tumor, Leukemia

---

ZOO ANIMAL DIAGNOSES (200+):

BIG CATS (Lion, Tiger, Leopard, Cheetah, Snow Leopard, Jaguar, Cougar/Puma):
Feline herpesvirus (FHV-1), Feline calicivirus (FCV), Panleukopenia (FPV),
Feline leukemia virus (FeLV — susceptibility varies by species), Toxoplasmosis,
Helicobacter gastritis, Trichinella, Toxocara species (ascarids),
Ancylostoma (hookworms), Spirometra (tapeworm — proliferans — most wild felids),
Streptococcus species, Pasteurella multocida, Yersinia pseudotuberculosis,
Salmonellosis, Tuberculosis (M. bovis/M. tuberculosis — BIG concern captive cats),
Coccidioidomycosis (cheetah highly susceptible), Cryptococcosis, Aspergillosis,
Lymphoma, Mast cell tumor, Osteosarcoma, Renal carcinoma, Hepatic disease,
Cardiomyopathy (hypertrophic/dilated), Aortic stenosis (cheetah — heritable),
Venoocclusive disease (cheetah — susceptibility stress-related),
Spinal myelopathy (snow leopard), Metabolic bone disease (cubs),
Capture myopathy, Azoturia (exertional rhabdomyolysis)

NON-HUMAN PRIMATES (Gorilla, Chimpanzee, Orangutan, Gibbon, Macaque, Baboon, Marmoset, Tamarin):
Respiratory viruses (including human RSV/influenza/SARS-CoV-2 — EXTREME ZOONOTIC BIDIRECTIONALITY),
Herpesvirus B (Macacine herpesvirus 1 — FATAL to humans — macaques ONLY),
Simian immunodeficiency virus (SIV), Simian retrovirus (SRV), Simian foamy virus (SFV — zoonotic),
Tuberculosis (M. tuberculosis/M. bovis — mandatory annual TB testing), Shigellosis,
Salmonellosis, Campylobacteriosis, Yersiniosis, Klebsiella, Proteus, Pseudomonas,
Cholera (Old World primates), Treponema pallidum (yaws — NHP), Leptospirosis,
Balantidium coli (Great Apes — ciliates), Giardia, Entamoeba histolytica,
Strongyloides stercoralis, Trichuris (whipworm), Oesophagostomum (nodular worm),
Ascariasis, Pinworm, Malarial parasites (Plasmodium knowlesi zoonotic),
Protozoan: Toxoplasma, Cryptosporidium, Sarcocystis,
Lymphocytic choriomeningitis virus (LCMV), Yellow fever (New World monkeys — reservoir),
Fibropapillomatosis, Transmissible gastroenteritis marmosets,
Callitrichid hepatitis (herpesvirus — marmosets/tamarins), Wasting syndrome (marmosets/tamarins),
Diabetes mellitus, Obesity, Cardiovascular disease (atherosclerosis — NHP excellent model),
Endometriosis, Uterine leiomyoma, Prostate carcinoma, Lymphoma, Leukemia,
Myopathies, Cardiomyopathy, Amyloidosis, Renal disease

PACHYDERMS (Elephant — African & Asian, Rhinoceros — White/Black/Indian/Sumatran/Javan, Hippopotamus):
Elephant endotheliotropic herpesvirus (EEHV) — young Asian elephants — FATAL hemorrhagic disease
Tuberculosis (M. tuberculosis — ZOONOTIC — major concern zoo elephants)
Foot disease (nail cracks/sole abscess/pododermatitis — LEADING CAUSE OF EUTHANASIA)
Musth management (Asian/African bull elephants — testosterone-driven aggression)
Atherosclerosis (Asian elephants — cardiac — leading cause of death)
Colic/GI impaction, Hernia, Intestinal foreign body, Rectal prolapse
Respiratory disease (bacterial/EEHV pulmonary form), Lungworm (Mammomonogamus),
Trypanosomiasis (African elephants — Trypanosoma brucei), Babesiosis, Anthrax exposure,
Encephalitozoon infection (reported), Salmonellosis, Leptospirosis
Metabolic bone disease (calves), Hypocalcemia, Trauma/wound management
Reproductive: dystocia, retained placenta, endometritis, pyometra, prolapsed uterus
Behavioral: stereotypies, captive stress disorders
Capture myopathy (rhino capture — azoturia/rhabdomyolysis)
Rhino: Poxvirus, Salmonellosis, Leptospirosis, Trypanosomiasis, Babesia,
Rhino GI disease (ulcers/colitis), Dental disease

GIRAFFE, OKAPI, ZEBRA, ANTELOPE, DEER, MOOSE, ELK:
Malignant catarrhal fever (MCF — Ovine herpesvirus 2 — FATAL in bison/deer/giraffe)
Foot-and-mouth disease (FMD — reportable), Foot rot, Digital dermatitis
Bluetongue (reportable), Epizootic hemorrhagic disease (EHD — deer)
Bovine viral diarrhea (BVD cross-species), Bovine herpesvirus (BoHV-1)
Trypanosomiasis (African ungulates — Nagana), Theileria, Babesia
Gastrointestinal helminths (Haemonchus/Cooperia/Ostertagia), Lungworm
Sarcoptic mange, Psoroptic mange, Tick infestation
Giraffe: polydactyly, joint disease, tongue lacerations, metabolic bone disease calves
Capture myopathy (ALL ungulates — exertional — LEADING CAUSE TRANSPORT DEATHS)
Spinal arthritis (giraffe), Osteomyelitis, Fractures (high-strung species — capture)
Intestinal volvulus, Bloat, Rectal prolapse, Intussusception

BEARS:
Trichinella spiralis, Toxoplasma, Giardia, Cryptosporidium, Baylisascaris transfuga
Canine distemper (bears susceptible), Rabies, Leptospirosis, Brucellosis
Sarcoptic mange, Demodex, Hookworm, Tapeworm (Taenia)
Periodontal disease (very common bears), Tooth fracture, Malocclusion
Obesity (captive bears — leading problem), Diabetes (Asian black bears),
Hepatocellular carcinoma (Asiatic black bears — bile farming legacy),
Biliary disease, Gallbladder pathology, Cholangitis
Cardiomyopathy, Myocarditis, Vascular disease
Osteosarcoma, Lymphoma, Mast cell tumor, Lipoma
Capture myopathy, Hibernation-related disorders, Hyperthermia
Alopecia (bears — idiopathic/nutritional/stress), Behavioral stereotypies

MARINE MAMMALS (Dolphin, Killer Whale, Sea Lion, Seal, Manatee, Walrus, Sea Otter):
Morbillivirus (cetacean/phocine — CDV relative — FATAL), Herpesvirus (cetaceans/pinnipeds)
Lobomycosis (Lacazia loboi — dolphins — disfiguring skin fungus), Calicivirus (San Miguel Sea Lion Virus)
Brucellosis (B. ceti/B. pinnipedialis — ZOONOTIC), Leptospirosis (California sea lions — outbreak disease)
Salmonella, Campylobacter, Toxoplasma (sea otters — ZOONOTIC), Sarcocystis neurona (sea otters)
Lungworm (Parafilaroides spp. — pinnipeds), Anisakiasis (dolphin/cetaceans), Trichinella
Cryptosporidiosis, Giardia, Domoic acid toxicosis (California sea lions — seizures/cardiac)
PCB/heavy metal accumulation, Microplastic ingestion, Fishing gear entanglement injuries
Flipper/skin trauma, Laceration management, Thermal burn, Decompression sickness (diving mammals)
Pneumonia (bacterial/viral), Pleuritis, Lung abscess (sea lions/seals)
GI foreign body, Gastric ulcer (cetaceans/pinnipeds), Hepatitis, Pancreatitis
Dental disease (cetaceans — severe in captivity), Jaw fracture
Cardiomyopathy, Endocarditis, Valvular disease (sea lions/seals)
Renal disease (lead toxicosis, amyloidosis), Bladder stones (pinnipeds)
Reproductive: abortion (Brucella), pyometra, dystocia, phimosis/paraphimosis
Neoplasia: lymphoma, fibrosarcoma, hepatocellular carcinoma, papilloma
Lobomycosis-like disease, Squamous cell carcinoma (sun exposure)

---

## THE 50 PANELS

[SAME 50 PANELS AS V2 SPEC — copy panels list from SAIRNVET-CLAUDE-CODE-SPEC-V2.md]

---

## DIAGNOSIS & DRUG IMPLEMENTATION ARCHITECTURE

### In the app, implement these three AI-powered features:

**1. Diagnosis Finder (panel-diagnoses)**
- Species selector (50+ species/groups)
- Body system filter (12 systems)
- Keyword search
- Results show: name, common signs, first-line treatment with drug names
- AI button: "Full treatment protocol" → Claude returns complete protocol with doses by weight/species

**2. Drug Database (panel-drugdb)**
- Search any drug by name/class/species
- Results show: drug name, class, species, dose, route, frequency, controlled status, withdrawal time (food animals), species contraindications (RED FLAGS)
- AI button: "Calculate dose for my patient" → enter weight + species → Claude calculates
- RED FLAG system: auto-display contraindications (ivermectin+chelonians, penicillin+guinea pigs, etc.)

**3. AI Dosing Calculator (part of panel-pharmacy)**
- Enter: Drug name + Patient weight + Species
- Claude calculates: mg dose, volume to draw, frequency, route, duration
- Returns drug interaction warnings
- Returns species-specific contraindications
- Works for ANY drug — not limited to seeded database
- System prompt: "You are a veterinary pharmacologist with expertise in all species. Calculate precise drug doses. Always flag contraindications. Always note controlled substance status and withdrawal times for food animals."

---

## DEMO DATA — same as V2 spec

---

## GUARDIAN SCAN — same as V2 spec but add panel-diagnoses and panel-drugdb

---

## VERCEL.JSON

```json
{
  "buildCommand": "mkdir -p dist && cp stonedesk.html dist/stonedesk.html && cp sairnbiz.html dist/sairnbiz.html && cp sairncode.html dist/sairncode.html && cp sairnvet.html dist/sairnvet.html && cp stonedesk.html dist/index.html",
  "outputDirectory": "dist",
  "public": true,
  "routes": [
    { "src": "/stonedesk$", "dest": "/stonedesk.html" },
    { "src": "/sairnbiz$", "dest": "/sairnbiz.html" },
    { "src": "/sairncode$", "dest": "/sairncode.html" },
    { "src": "/sairnvet$", "dest": "/sairnvet.html" }
  ]
}
```

---

## BUILD ORDER
1. Read this entire spec
2. Generate new PAT: Name=SAIRN-SAIRNvet-FINAL
3. Build sairnvet.html — 50+ panels, complete drug+diagnosis databases, all demo data
4. Guardian scan — zero failures
5. Push sairnvet.html + vercel.json in one commit via REST API
6. Deploy: git fetch && reset && npx vercel --prod --force --token vcp_6c79...
7. Report SHA

---
*SAIRN Technologies LLC — Westlake, Ohio — July 6, 2026*
*The world's most complete veterinary platform. Every species. Every diagnosis. Every medication.*
