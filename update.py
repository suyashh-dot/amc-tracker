#!/usr/bin/env python3
"""
AMC Portfolio Tracker — Monthly Update Script
=============================================
Usage:
    python update.py "path/to/new_month.xlsx"

What it does:
    1. Parses the new month's Excel file
    2. Merges with existing data in ../amc-data/
    3. Recomputes signals, sector rotation, first mover
    4. Pushes updated JSONs to GitHub (amc-data repo)

Requirements:
    pip install pandas openpyxl
"""

import sys, os, json, subprocess, hashlib
from collections import defaultdict
from datetime import datetime
import pandas as pd

# ── CONFIG ────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'amc-data')
GITHUB_USER = "suyashh-dot"
DATA_REPO = "amc-data"
MAX_SANE_WEIGHT = 0.30  # cap anomalous weights above 30%

MONTHS_ORDER = [
    'Jan-25','Feb-25','Mar-25','Apr-25','May-25','Jun-25','Jul-25',
    'Aug-25','Sep-25','Oct-25','Nov-25','Dec-25',
    'Jan-26','Feb-26','Mar-26','Apr-26','May-26','Jun-26','Jul-26',
    'Aug-26','Sep-26','Oct-26','Nov-26','Dec-26',
    'Jan-27','Feb-27','Mar-27','Apr-27','May-27','Jun-27','Jul-27',
    'Aug-27','Sep-27','Oct-27','Nov-27','Dec-27',
]

# ── SECTOR RULES ─────────────────────────────────────────────────────────
SECTOR_RULES = [
    ('Banking', ['bank']),
    ('Insurance', ['insurance', 'life insurance']),
    ('NBFC & Fintech', ['finance limited','financial services','muthoot','manappuram',
                        'shriram','cholamandalam','mahindra finance','jio financial',
                        'paytm','one97','iifl','pnb housing','can fin','aavas',
                        'aptus','home first','repco','credit access','rec limited',
                        'power finance','bajaj finance','bajaj finserv']),
    ('Capital Markets', ['asset management','stock exchange','depository','nse ','bse ',
                         'cdsl','nsdl','motilal oswal','nippon life india asset',
                         'angel one','5paisa','uti asset',' amc','cams','kfin',
                         'multi commodity exchange','crisil','prudent corporate',
                         '360 one wam','nuvama']),
    ('IT Services', ['tata consultancy','tcs','infosys','wipro','hcl tech',
                     'tech mahindra','ltimindtree','mphasis','hexaware','persistent',
                     'coforge','mastech','zensar','cyient','birlasoft','sonata',
                     'niit tech','intellect design','kpit tech','tata elxsi',
                     'inventurus','sagility']),
    ('IT Products & Platforms', ['route mobile','tanla','indiamart','info edge',
                                  'naukri','just dial','zomato','eternal limited',
                                  'swiggy','policybazaar','pb fintech','cartrade',
                                  'easy trip','ixigo','mapmyindia','tbo tek',
                                  'fsn e-commerce']),
    ('Electronics & Hardware', ['dixon technologies','amber enterprises','kaynes',
                                  'syrma','avalon','pg electroplast','optiemus',
                                  'bharat electronics','bel ','data patterns',
                                  'zen tech','astra microwave','centum','signaltron',
                                  'lg electronics','hyundai motor']),
    ('FMCG', ['hindustan unilever','hul ','itc limited','nestle','britannia',
               'dabur','marico','emami','godrej consumer','colgate','jyothy',
               'bajaj consumer','procter','gillette','varun beverages','radico',
               'united spirits','united breweries','tata consumer','patanjali',
               'kwality wall']),
    ('Retail & QSR', ['avenue supermarts','dmart','trent','v-mart','shoppers stop',
                       'westlife','jubilant foodworks','devyani','sapphire foods',
                       'burger king','barbeque nation','titan','kalyan jewellers',
                       'senco','thangamayil','pc jeweller','doms','metro brands',
                       'vedant fashions']),
    ('Consumer Durables', ['voltas','blue star','whirlpool','havells','orient electric',
                            'crompton','bajaj electricals','v-guard','symphony',
                            'finolex cables','polycab','rr kabel','cg power',
                            'td power','safari industries','lg electronics']),
    ('Textiles & Apparel', ['page industries','dollar industries','lux industries',
                             'raymond','arvind','vardhman','trident','welspun',
                             'grasim industries','century textiles','kewal kiran',
                             'monte carlo','go fashion','kpr mill']),
    ('Capital Goods & Engineering', ['larsen & toubro','l&t limited','bharat forge',
                                      'cummins','siemens','abb india','honeywell',
                                      'thermax','kec international','kalpataru',
                                      'praj industries','elgi','grindwell','timken',
                                      'schaeffler','skf india','carborundum',
                                      'greaves cotton','kirloskar','ingersoll',
                                      'ge vernova','hitachi energy','apar industries',
                                      'aia engineering','triveni turbine','jyoti cnc',
                                      'craftsman','bharat heavy','bharat bijlee',
                                      'kei industries']),
    ('Defence', ['hindustan aeronautics','hal ','garden reach','grse','mazagon dock',
                  'cochin shipyard','solar industries','paras defence','ideaforge',
                  'premier explosives','mtar tech','bharat dynamics']),
    ('Infrastructure & Construction', ['irb infrastructure','ashoka buildcon',
                                        'knr constructions','pnc infratech','rites',
                                        'ircon','nbcc','hg infra','dilip buildcon',
                                        'itd cementation','psp projects',
                                        'g r infraprojects','awfis']),
    ('Power & Utilities', ['ntpc','power grid','tata power','adani power','adani green',
                            'torrent power','cesc','nhpc','sjvn','inox wind','suzlon',
                            'sterling wilson','waaree','premier energies','jsw energy',
                            'clean max','ren ']),
    ('Automobiles', ['maruti suzuki','tata motors','mahindra & mahindra','bajaj auto',
                      'hero motocorp','tvs motor','eicher motors','force motors',
                      'ashok leyland','escorts kubota']),
    ('Auto Ancillaries', ['motherson','bosch limited','minda industries','uno minda',
                           'exide','amara raja','sundram fasteners','endurance',
                           'suprajit','lumax','fiem','gabriel','rane','subros',
                           'sona bl','tube investments','balkrishna','apollo tyres',
                           'zf commercial']),
    ('EV & New Mobility', ['olectra','ola electric','greaves electric','ather energy']),
    ('Pharma', ['sun pharmaceutical','dr reddy','cipla','divi','aurobindo','lupin',
                 'torrent pharma','alkem','ipca','abbott india','pfizer',
                 'glaxosmithkline','glenmark','zydus','natco','suven','laurus',
                 'granules','aarti pharma','solara','sequent','eris life',
                 'ajanta pharma','mankind pharma','neuland','sai life','cohance',
                 'jb chemicals','gland pharma']),
    ('Hospitals & Healthcare', ['apollo hospitals','fortis','max healthcare',
                                  'narayana','global health','medanta','aster dm',
                                  'rainbow children','healthium','poly medicure',
                                  'syngene','metropolis','dr lal','vijaya diagnostic',
                                  'thyrocare','krishna institute']),
    ('Metals & Mining', ['tata steel','jsw steel','sail','hindalco','vedanta',
                          'national aluminium','nalco','hindustan copper',
                          'hindustan zinc','coal india','nmdc','moil','electrosteel',
                          'shyam metalics','jindal steel','jindal stainless',
                          'ratnamani','mishra dhatu','apl apollo','lloyds metals']),
    ('Chemicals', ['pidilite','asian paints','berger paints','kansai nerolac',
                    'indigo paints','aarti industries','atul limited','srf limited',
                    'navin fluorine','deepak nitrite','clean science','galaxy surf',
                    'vinati organics','sudarshan chemical','fine organics','nocil',
                    'rossari','neogen chemicals','gujarat fluorochemicals',
                    'sumitomo chemical','acutaas']),
    ('Cement', ['ultratech cement','shree cement','ambuja cement','acc limited',
                 'dalmia bharat','jk cement','ramco cement','india cement',
                 'heidelberg','prism johnson','star cement','kajaria']),
    ('Plastics & Packaging', ['astral','supreme industries','finolex industries',
                               'prince pipes','apollo pipes','uflex','mold-tek',
                               'time technoplast','essel propack','huhtamaki']),
    ('Real Estate', ['dlf','godrej properties','prestige estates','oberoi realty',
                      'brigade enterprises','macrotech','lodha','puravankara',
                      'kolte patil','mahindra lifespace','sobha','phoenix mills',
                      'nexus select','aditya birla real estate']),
    ('Telecom', ['bharti airtel','reliance jio','vodafone idea','indus towers',
                  'sterlite tech','hfcl','tata communications','bharti hexacom']),
    ('Media & Entertainment', ['zee entertainment','sun tv','pvr inox','inox leisure',
                                 'tips music','saregama','balaji telefilms','nazara',
                                 'delta corp']),
    ('Oil & Gas', ['reliance industries','ongc','oil india','bpcl','hpcl',
                    'indian oil','ioc','castrol','gujarat gas','indraprastha gas',
                    'mahanagar gas','petronet lng','gujarat state petronet',
                    'hindustan petroleum','gail']),
    ('Agri & Fertilisers', ['coromandel','pi industries','rallis','upl limited',
                              'bayer crop','kaveri seed','dhanuka','chambal fert',
                              'gnfc','gsfc','deepak fertilizers','sumitomo chemical']),
    ('Logistics & Transport', ['container corporation','concor','gateway distriparks',
                                 'mahindra logistics','delhivery','blue dart','gati',
                                 'transport corporation','vrl logistics',
                                 'tvs supply chain','allcargo']),
    ('Aviation', ['interglobe aviation','indigo','spicejet','air india']),
    ('Shipping & Ports', ['adani ports','gujarat pipavav','shipping corporation',
                           'great eastern shipping','jsw infrastructure']),
    ('Hotels & Tourism', ['indian hotels','ihcl','lemon tree','chalet hotels',
                           'mahindra holidays','irctc','itc hotels']),
    ('Government Securities', ['gsec','g-sec','government bond','sovereign','sdl']),
    ('Treasury Bills', ['tbill','t-bill','treasury bill','182 day','91 day','364 day']),
    ('Corporate Bonds', ['ncd','debenture',' bond ','commercial paper']),
]

def tag_sector(name):
    lo = name.lower()
    if any(k in lo for k in ['tbill','t-bill','treasury bill','182 day','91 day','364 day','md ']):
        return 'Treasury Bills'
    if any(k in lo for k in ['gsec','g-sec','% ','mat-','sdl','state loan','state development']):
        return 'Government Securities'
    if any(k in lo for k in ['ncd','debenture','commercial paper']):
        return 'Corporate Bonds'
    for sector, keywords in SECTOR_RULES:
        for kw in keywords:
            if kw in lo:
                return sector
    # Fallback rules
    if any(k in lo for k in ['pharma','laboratories','lifescience','biotech']):
        return 'Pharma'
    if any(k in lo for k in ['hospital','healthcare','medical','clinic','diagnostic']):
        return 'Hospitals & Healthcare'
    if any(k in lo for k in ['cement','ceramics']):
        return 'Cement'
    if any(k in lo for k in ['steel','alumin','copper',' zinc','metal']):
        return 'Metals & Mining'
    if any(k in lo for k in ['power','energy','solar','wind','renewable']):
        return 'Power & Utilities'
    if any(k in lo for k in ['hotel','resort','hospitality']):
        return 'Hotels & Tourism'
    if any(k in lo for k in ['logistics','warehousing','freight']):
        return 'Logistics & Transport'
    if any(k in lo for k in ['textile','garment','fabric','yarn','spinning']):
        return 'Textiles & Apparel'
    if any(k in lo for k in ['chemical','agrochemical']):
        return 'Chemicals'
    if any(k in lo for k in ['defence','defense','ammunition','missile']):
        return 'Defence'
    if any(k in lo for k in ['real estate','realty','properties']):
        return 'Real Estate'
    if any(k in lo for k in ['software','technologies','technology',' systems ',' solutions ']):
        return 'IT Services'
    return 'Other'


# ── PARSE NEW EXCEL ───────────────────────────────────────────────────────
def parse_excel(filepath):
    """Parse a new month Excel file. Returns dict: instrument -> [(fund, weight)]"""
    print(f"  Parsing: {filepath}")
    df = pd.read_excel(filepath, header=None)

    # Detect structure: Row with "Name of Instrument" is the header row
    header_row = None
    for i, row in df.iterrows():
        if 'Name of Instrument' in str(row.values):
            header_row = i
            break

    if header_row is None:
        raise ValueError("Could not find 'Name of Instrument' row in Excel")

    fund_row_idx = header_row - 1
    month_row_idx = header_row
    data_start = header_row + 1

    fund_row = df.iloc[fund_row_idx]
    month_row = df.iloc[month_row_idx]

    # Build column -> (fund, month) mapping
    current_fund = None
    col_map = {}
    for col_idx in range(1, len(fund_row)):
        fval = str(fund_row.iloc[col_idx]).strip()
        mval = str(month_row.iloc[col_idx]).strip()
        if fval not in ('nan', ''):
            current_fund = fval
        if current_fund and mval not in ('nan', '', 'Name of Instrument'):
            col_map[col_idx] = (current_fund, mval)

    # Detect month from data
    months_found = list(set(v[1] for v in col_map.values()))
    print(f"  Funds: {len(set(v[0] for v in col_map.values()))}")
    print(f"  Months in file: {months_found}")

    # Extract records
    records = {}  # instrument -> month -> [(fund, weight)]
    data_rows = df.iloc[data_start:]

    for _, row in data_rows.iterrows():
        inst = str(row.iloc[0]).strip()
        if inst in ('nan', ''):
            continue
        for col_idx, (fund, month) in col_map.items():
            val = row.iloc[col_idx]
            if pd.isna(val) or str(val).strip() in ('', 'nan'):
                continue
            try:
                weight = float(str(val).replace('%', '').strip())
                if weight <= 0 or weight > MAX_SANE_WEIGHT:
                    continue
                if inst not in records:
                    records[inst] = {}
                if month not in records[inst]:
                    records[inst][month] = []
                records[inst][month].append([fund, round(weight, 4)])
            except (ValueError, TypeError):
                pass

    print(f"  Instruments parsed: {len(records)}")
    return records


# ── MERGE WITH EXISTING DATA ──────────────────────────────────────────────
def merge_data(existing, new_records):
    """Merge new month's data into existing compressed_data format."""
    merged = {k: list(v) for k, v in existing.items()}

    for inst, months_data in new_records.items():
        if inst not in merged:
            merged[inst] = []
        existing_months = set(e[0] for e in merged[inst])
        for month, fund_weights in months_data.items():
            if month in existing_months:
                print(f"    Skipping {inst} / {month} (already exists)")
                continue
            # Compute stats
            n = len(fund_weights)
            avg_w = sum(fw[1] for fw in fund_weights) / n if n else 0
            # Format: [month, holderCount, avgWeight, [[fund, weight], ...]]
            merged[inst].append([month, n, round(avg_w, 4), fund_weights])
            # Sort by month order
            merged[inst].sort(key=lambda e: MONTHS_ORDER.index(e[0]) if e[0] in MONTHS_ORDER else 999)

    return merged


# ── REBUILD FUND DATA ─────────────────────────────────────────────────────
def rebuild_fund_data(inst_data):
    """fund -> month -> [[inst, weight], ...]"""
    fund_data = {}
    for inst, monthly in inst_data.items():
        for entry in monthly:
            month = entry[0]
            for fw in entry[3]:
                fund = fw[0]
                weight = fw[1]
                if fund not in fund_data:
                    fund_data[fund] = {}
                if month not in fund_data[fund]:
                    fund_data[fund][month] = []
                fund_data[fund][month].append([inst, weight])
    for fund in fund_data:
        for month in fund_data[fund]:
            fund_data[fund][month].sort(key=lambda x: -x[1])
    return fund_data


# ── REBUILD SIGNALS ───────────────────────────────────────────────────────
def rebuild_signals(inst_data, all_months):
    signals = {}
    for i in range(1, len(all_months)):
        prev_m, cur_m = all_months[i-1], all_months[i]
        fresh, exits = [], []
        for inst, monthly in inst_data.items():
            prev_e = next((e for e in monthly if e[0]==prev_m), None)
            cur_e  = next((e for e in monthly if e[0]==cur_m),  None)
            pf = set(fw[0] for fw in prev_e[3]) if prev_e else set()
            cf = set(fw[0] for fw in cur_e[3])  if cur_e  else set()
            new_in  = cf - pf
            new_out = pf - cf
            if len(new_in) >= 2:
                avg_w = sum(fw[1] for fw in cur_e[3] if fw[0] in new_in) / len(new_in)
                fresh.append({'inst':inst,'newCount':len(new_in),
                              'newFunds':sorted(list(new_in)),
                              'avgNewWeight':round(avg_w,4),'totalHolders':len(cf)})
            if len(new_out) >= 2:
                avg_w = sum(fw[1] for fw in prev_e[3] if fw[0] in new_out) / len(new_out)
                exits.append({'inst':inst,'exitCount':len(new_out),
                              'exitFunds':sorted(list(new_out)),
                              'avgExitWeight':round(avg_w,4),'prevHolders':len(pf)})
        fresh.sort(key=lambda x: -x['newCount'])
        exits.sort(key=lambda x: -x['exitCount'])
        signals[cur_m] = {'freshBets':fresh[:80],'exitAlerts':exits[:80]}
    return signals


# ── REBUILD SECTOR ROTATION ───────────────────────────────────────────────
def rebuild_sector_rotation(inst_data, sector_map, all_months):
    exclude = {'Treasury Bills','Government Securities','Corporate Bonds','Other'}
    all_sectors = set()
    rotation = {}

    for month in all_months:
        all_funds = set()
        fund_sector_w = defaultdict(lambda: defaultdict(float))
        for inst, monthly in inst_data.items():
            sector = sector_map.get(inst, 'Other')
            if sector in exclude:
                continue
            entry = next((e for e in monthly if e[0]==month), None)
            if not entry:
                continue
            for fw in entry[3]:
                fund, w = fw[0], fw[1]
                if w > MAX_SANE_WEIGHT:
                    continue
                all_funds.add(fund)
                fund_sector_w[fund][sector] += w
        n = max(len(all_funds), 1)
        stats = {}
        for sector in set(s for fd in fund_sector_w.values() for s in fd):
            all_sectors.add(sector)
            weights = [fund_sector_w[f].get(sector,0) for f in all_funds]
            avg_w = sum(weights)/n
            n_holding = sum(1 for w in weights if w>0)
            stats[sector] = {'avgW':round(avg_w*100,3),'f':n_holding,'i':0}
        rotation[month] = stats

    equity_sectors = sorted([s for s in all_sectors if s not in exclude])
    return {'rotation':rotation,'sectors':equity_sectors}


# ── REBUILD FIRST MOVER ───────────────────────────────────────────────────
def rebuild_first_mover(inst_data, all_months):
    first_mover = {}
    for inst, monthly in inst_data.items():
        sorted_entries = sorted(monthly, key=lambda e: MONTHS_ORDER.index(e[0]) if e[0] in MONTHS_ORDER else 999)
        if not sorted_entries:
            continue
        first_e = sorted_entries[0]
        first_funds = [fw[0] for fw in first_e[3]]
        progression = []
        prev_funds = set(first_funds)
        for entry in sorted_entries:
            cur_funds = set(fw[0] for fw in entry[3])
            new_joiners = sorted(list(cur_funds - prev_funds))
            progression.append({'m':entry[0],'total':len(cur_funds),'new':new_joiners})
            prev_funds = cur_funds
        max_h = max(e['total'] for e in progression)
        if max_h >= 5 and len(progression) >= 2:
            first_mover[inst] = {
                'firstMonth': first_e[0],
                'firstFunds': first_funds,
                'progression': progression
            }
    return first_mover


# ── UPDATE SECTOR MAP ─────────────────────────────────────────────────────
def update_sector_map(inst_data, existing_map):
    updated = dict(existing_map)
    for inst in inst_data:
        if inst not in updated or updated[inst] == 'Other':
            updated[inst] = tag_sector(inst)
    return updated


# ── SAVE JSON ─────────────────────────────────────────────────────────────
def save_json(data, filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    sz = os.path.getsize(path)
    print(f"  ✓ {filename} ({sz/1024:.0f} KB)")


# ── GIT PUSH ─────────────────────────────────────────────────────────────
def git_push(new_month, data_dir):
    print("\n  Pushing to GitHub...")
    cmds = [
        ['git', '-C', data_dir, 'add', '.'],
        ['git', '-C', data_dir, 'commit', '-m', f'Data update: {new_month} — {datetime.now().strftime("%Y-%m-%d")}'],
        ['git', '-C', data_dir, 'push'],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ✗ Git error: {result.stderr}")
            return False
    print("  ✓ Pushed to GitHub successfully")
    return True


# ── MAIN ──────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: python update.py path/to/new_month.xlsx")
        sys.exit(1)

    excel_path = sys.argv[1]
    if not os.path.exists(excel_path):
        print(f"Error: File not found: {excel_path}")
        sys.exit(1)

    print("\n" + "="*55)
    print("  AMC Tracker — Monthly Update")
    print("="*55)

    # 1. Load existing data
    print("\n[1/7] Loading existing data...")
    with open(os.path.join(DATA_DIR, 'compressed_data.json')) as f:
        existing_inst = json.load(f)
    with open(os.path.join(DATA_DIR, 'sector_map.json')) as f:
        sector_map = json.load(f)
    with open(os.path.join(DATA_DIR, 'metadata.json')) as f:
        metadata = json.load(f)
    print(f"  Existing instruments: {len(existing_inst)}")

    # 2. Parse new Excel
    print("\n[2/7] Parsing new Excel...")
    new_records = parse_excel(excel_path)

    # 3. Detect new month
    new_months = list(set(m for inst_m in new_records.values() for m in inst_m.keys()))
    print(f"  New months detected: {new_months}")

    # 4. Merge
    print("\n[3/7] Merging data...")
    merged_inst = merge_data(existing_inst, new_records)
    print(f"  Total instruments after merge: {len(merged_inst)}")

    # 5. Update sector map
    print("\n[4/7] Updating sector map...")
    sector_map = update_sector_map(merged_inst, sector_map)

    # 6. Determine all months
    all_months = sorted(
        list(set(e[0] for monthly in merged_inst.values() for e in monthly)),
        key=lambda m: MONTHS_ORDER.index(m) if m in MONTHS_ORDER else 999
    )
    print(f"  All months: {all_months}")

    # 7. Rebuild all derived data
    print("\n[5/7] Rebuilding signals, sectors, first mover...")
    fund_data = rebuild_fund_data(merged_inst)
    signals = rebuild_signals(merged_inst, all_months)
    sector_rotation = rebuild_sector_rotation(merged_inst, sector_map, all_months)
    first_mover = rebuild_first_mover(merged_inst, all_months)

    # 8. Update metadata
    latest_month = all_months[-1]
    metadata['lastUpdated'] = datetime.now().strftime('%Y-%m-%d')
    metadata['latestMonth'] = latest_month
    metadata['months'] = all_months
    metadata['totalInstruments'] = len(merged_inst)
    metadata['totalFunds'] = len(set(fw[0] for monthly in merged_inst.values()
                                      for e in monthly for fw in e[3]))

    # 9. Save all files
    print("\n[6/7] Saving data files...")
    save_json(merged_inst, 'compressed_data.json')
    save_json(fund_data, 'fund_data.json')
    save_json(signals, 'signals.json')
    save_json(sector_rotation, 'sector_rotation.json')
    save_json(first_mover, 'first_mover.json')
    save_json(sector_map, 'sector_map.json')
    save_json(metadata, 'metadata.json')

    # 10. Git push
    print("\n[7/7] Pushing to GitHub...")
    git_push(latest_month, DATA_DIR)

    print("\n" + "="*55)
    print(f"  ✓ Update complete! {latest_month} is now live.")
    print(f"  Website updates within 60 seconds.")
    print("="*55 + "\n")


if __name__ == '__main__':
    main()
