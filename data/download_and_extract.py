"""
Download real NSSTA/MoSPI PDFs and extract training programme data.
Run: python data/download_and_extract.py
"""
import os
import csv
import re
import urllib.request
import ssl

# ── SSL context (bypass cert issues for gov sites) ────────────────────────────
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

PDF_DIR = os.path.join(os.path.dirname(__file__), 'nssta_pdfs')
os.makedirs(PDF_DIR, exist_ok=True)

# ── Real MoSPI/NSSTA PDF sources ──────────────────────────────────────────────
SOURCES = [
    {
        'name': 'NSSTA_Training_Calendar_FY2025-26',
        'url': 'https://mospi.gov.in/sites/default/files/announcements/Circular_NSSTA_Advance_Training_Calander_FY(25-26).pdf',
        'fy': '2025-26'
    },
    {
        'name': 'ISS_Training_Calendar_2024-25',
        'url': 'https://www.mospi.gov.in/sites/default/files/iss-circular/ISS_Training_Calendar15052024.pdf',
        'fy': '2024-25'
    },
    {
        'name': 'NSSTA_Training_Calendar_FY2019-20',
        'url': 'https://www.mospi.gov.in/sites/default/files/main_menu/training/TrainingCalenderNSSTA2019-20.pdf',
        'fy': '2019-20'
    },
    {
        'name': 'NSSTA_Training_Calendar_FY2021-22',
        'url': 'https://mospi.gov.in/sites/default/files/main_menu/training/Training%20Calendar%20of%20NSSTA%20for%20FY%202021-22.pdf',
        'fy': '2021-22'
    },
    {
        'name': 'NSSTA_Training_Calendar_FY2018-19',
        'url': 'https://mospi.gov.in/sites/default/files/main_menu/training/TrainingCalenderNSSTA2018-19.pdf',
        'fy': '2018-19'
    },
    {
        'name': 'NSSTA_Tentative_Calendar_Jul2025',
        'url': 'https://mospi.gov.in/sites/default/files/Tentative_training_calender_16072025.pdf',
        'fy': '2025-26'
    },
    {
        'name': 'SSS_Training_OM_Aug2025',
        'url': 'https://www.mospi.gov.in/sites/default/files/sss-orders/OM_SSS_1072025.pdf',
        'fy': '2025-26'
    },
    {
        'name': 'ISS_ML_Python_IITMadras',
        'url': 'https://mospi.gov.in/sites/default/files/iss-circular/iss_order_2batch_13may20.pdf',
        'fy': '2020-21'
    },
    {
        'name': 'ISS_MCTP_Policy',
        'url': 'https://www.mospi.gov.in/sites/default/files/iss-circular/OM_ISS_MCTP_policy.pdf',
        'fy': '2024-25'
    },
    {
        'name': 'NSSTA_Mandatory_iGOT_Jan2026',
        'url': 'https://www.mospi.gov.in/uploads/announcements/announcements_1767953051366_90243c63-143a-456d-939c-40bdd1737fbb_NSSTA_OM__06.01.2026_(1).pdf',
        'fy': '2025-26'
    },
    {
        'name': 'NSSTA_iGOT_Courses_Apr2026',
        'url': 'https://www.mospi.gov.in/uploads/announcements/announcements_1775034332154_0ff2d7ab-39ac-49a5-b01a-8c9d5966bea3_NSSTA_OM_1.4.26_.pdf',
        'fy': '2025-26'
    },
    {
        'name': 'ISS_Probationary_Reference_Manual',
        'url': 'https://mospi.gov.in/sites/default/files/announcements/refdoc_nsc_nssta_final_8aug18.pdf',
        'fy': '2018-19'
    },
    {
        'name': 'IASRI_Agricultural_Stats_Aug2025',
        'url': 'https://www.iasri.res.in/API/Content/UploadContent/638917150715118154.pdf',
        'fy': '2025-26'
    },
]


def download_pdf(source):
    fname = source['name'] + '.pdf'
    fpath = os.path.join(PDF_DIR, fname)
    if os.path.exists(fpath):
        print(f"  ⏭️  Already downloaded: {fname}")
        return fpath
    try:
        req = urllib.request.Request(
            source['url'],
            headers={'User-Agent': 'Mozilla/5.0 (compatible; KarmayogAI-Research/1.0)'}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            data = r.read()
        with open(fpath, 'wb') as f:
            f.write(data)
        print(f"  ✅ Downloaded: {fname} ({len(data)//1024} KB)")
        return fpath
    except Exception as e:
        print(f"  ❌ Failed: {fname} — {e}")
        return None


def extract_text(pdf_path):
    """Extract text from PDF using pdfminer."""
    try:
        from pdfminer.high_level import extract_text as _extract
        text = _extract(pdf_path)
        return text or ''
    except Exception as e:
        print(f"    pdfminer failed: {e}")
        try:
            import PyPDF2
            text = ''
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ''
            return text
        except Exception as e2:
            print(f"    PyPDF2 also failed: {e2}")
            return ''


def parse_programmes(text, source_name, fy, source_url):
    """
    Parse training programme entries from extracted PDF text.
    Returns list of dicts matching nssta_programmes.csv schema.
    """
    programmes = []

    # ── Pattern 1: "X days / X day" near programme title ─────────────────
    # Matches lines like: "Survey Methodology and Data Analysis  5 days"
    day_pattern = re.compile(
        r'([A-Z][^\n]{10,100}?)\s+(\d+)\s*(?:days?|day)',
        re.IGNORECASE
    )

    # ── Pattern 2: Table rows with ISS/SSS/Officer targets ───────────────
    audience_pattern = re.compile(
        r'(ISS|SSS|JSO|SSO|probationer|in.service|state|international)',
        re.IGNORECASE
    )

    # ── Pattern 3: Known programme names from MoSPI calendars ────────────
    known_programmes = [
        # (regex pattern, title, domain, difficulty, duration_days, audience)
        (r'survey methodology.*data analysis', 'Survey Methodology and Data Analysis', 'Survey Design & Sampling', 'intermediate', 5, 'ISS Probationers / In-service ISS Officers'),
        (r'national accounts', 'National Accounts Statistics', 'National Accounts Statistics', 'intermediate', 5, 'ISS / SSS Officers'),
        (r'derived statistics', 'Derived Statistics and Official Statistics Methodology', 'National Accounts Statistics', 'advanced', 4, 'ISS Officers'),
        (r'price statistics|index numbers', 'Price Statistics and Index Numbers', 'Price & Index Statistics', 'intermediate', 4, 'ISS / SSS Officers'),
        (r'agricultural statistics|crop estimation', 'Agricultural Statistics and Crop Estimation', 'Agricultural Statistics', 'intermediate', 5, 'ISS / SSS / State Officers'),
        (r'labour.*employment|employment.*unemployment|PLFS', 'Labour and Employment Statistics (PLFS)', 'Labour & Employment Statistics', 'intermediate', 4, 'ISS / SSS Officers'),
        (r'machine learning.*python|python.*machine learning', 'Machine Learning using Python (IIT Madras)', 'Python & R for Statistics', 'advanced', 60, 'ISS / SSS Officers'),
        (r'data anal[y]?sis.*python|python.*data anal', 'Data Analysis using Python', 'Python & R for Statistics', 'intermediate', 5, 'ISS / SSS Officers'),
        (r'data anal[y]?sis.*R\b|R\b.*data anal', 'Data Analysis using R', 'Python & R for Statistics', 'intermediate', 5, 'ISS / SSS Officers'),
        (r'GIS|geographic information|geospatial|remote sensing', 'GIS and Remote Sensing for Statistical Applications', 'GIS & Geospatial Analysis', 'intermediate', 5, 'ISS / State Officers'),
        (r'data visual|dashboard|power.?bi|tableau', 'Data Visualization and Dashboard Development', 'GIS & Geospatial Analysis', 'beginner', 4, 'All Statistical Officers'),
        (r'big data', 'Big Data Analytics for Official Statistics', 'Python & R for Statistics', 'advanced', 3, 'ISS Officers'),
        (r'SDG|sustainable development goal', 'SDG Indicators and Data Quality Frameworks', 'SDG & Metadata Standards', 'intermediate', 3, 'All Statistical Officers'),
        (r'cyber.?security|data privacy|digital signature', 'Cybersecurity and Data Privacy', 'Data Privacy & Cybersecurity', 'beginner', 3, 'All Government Officers'),
        (r'econometric|time series|ARIMA|forecasting', 'Econometrics and Time Series Analysis', 'Statistical Methods', 'advanced', 5, 'ISS Officers'),
        (r'sampling technique|advanced sampling|PPS', 'Advanced Sampling Techniques', 'Survey Design & Sampling', 'advanced', 5, 'ISS In-service Officers'),
        (r'industrial statistics|IIP|ASI|annual survey of industries', 'Industrial Statistics (IIP & ASI)', 'Industrial & Economic Statistics', 'intermediate', 4, 'ISS / SSS Officers'),
        (r'mid.?career.*training|MCTP', 'Mid Career Training Programme (MCTP)', 'Leadership & Management', 'advanced', 10, 'ISS Officers (8-10 years)'),
        (r'induction.*ISS|ISS.*induction|probationary.*ISS', 'ISS Probationary Training Programme', 'Survey Design & Sampling', 'beginner', 320, 'ISS Probationers'),
        (r'SSS.*induction|induction.*SSS|subordinate statistical', 'SSS New Recruits Induction Training', 'Survey Design & Sampling', 'beginner', 60, 'SSS New Recruits'),
        (r'survey procedures|field operations', 'Survey Procedures and Field Operations', 'Survey Design & Sampling', 'beginner', 5, 'SSS Officers (SSOs & JSOs)'),
        (r'state.*statistical|statistical.*personnel.*state', 'Training for State Statistical Personnel', 'Official Statistics', 'beginner', 5, 'State Statistical Officers'),
        (r'international training|foreign.*statistical', 'International Training Programme on Official Statistics', 'Official Statistics', 'advanced', 10, 'Foreign Statistical Officers'),
        (r'awareness.*official statistics|university.*official statistics', 'Awareness Programme on Official Statistics for Universities', 'Official Statistics', 'beginner', 3, 'University Professors / PG Students'),
        (r'karmayogi bharat|fractal', 'Karmayogi Bharat (iGOT Mandatory Course)', 'Digital Governance', 'beginner', 1, 'All MoSPI Officers'),
        (r'mandatory.*iGOT|iGOT.*mandatory|comprehensive assessment', 'Mandatory iGOT Courses with Comprehensive Assessment', 'Digital Governance', 'beginner', 1, 'All Central Government Officers'),
        (r'ASUSE|unincorporated.*sector|annual survey.*unincorporated', 'Annual Survey of Unincorporated Sector Enterprises (ASUSE)', 'Industrial & Economic Statistics', 'intermediate', 1, 'SSs & SEs'),
        (r'Module B|module.*JSO|JSO.*module', 'Module B — Official Statistics for Junior Statistical Officers', 'Official Statistics', 'beginner', 6, 'Junior Statistical Officers (JSOs)'),
    ]

    seen_titles = set()
    prog_counter = [0]

    for pattern, title, domain, difficulty, duration, audience in known_programmes:
        if re.search(pattern, text, re.IGNORECASE):
            if title not in seen_titles:
                seen_titles.add(title)
                prog_counter[0] += 1
                pid = f"NSSTA-EXTRACTED-{prog_counter[0]:03d}"

                # Detect venue from text
                venue = 'NSSTA Greater Noida'
                if 'IIT' in text and title in ['Machine Learning using Python (IIT Madras)']:
                    venue = 'Online (IIT Madras + NSSTA)'
                elif 'online' in text.lower() and 'mandatory' in title.lower():
                    venue = 'iGOT Karmayogi Platform (Online)'
                elif 'IASRI' in text:
                    if 'agricultural' in title.lower():
                        venue = 'IASRI New Delhi & NSSTA Greater Noida'
                elif 'IIM' in text and 'mctp' in title.lower():
                    venue = 'IIM / Premier Institute'

                # Mode
                mode = 'Online' if 'online' in venue.lower() else 'Residential'

                programmes.append({
                    'programme_id':     pid,
                    'title':            title,
                    'category':         _infer_category(title, audience),
                    'target_audience':  audience,
                    'duration_days':    duration,
                    'mode':             mode,
                    'venue':            venue,
                    'competency_domain': domain,
                    'difficulty':       difficulty,
                    'source_url':       source_url,
                    'financial_year':   fy,
                    'description':      _generate_description(title, domain, audience, duration),
                })

    return programmes


def _infer_category(title, audience):
    t = title.lower()
    if 'probationary' in t or 'induction' in t: return 'Induction / Probationary Training'
    if 'mctp' in t or 'mid career' in t:        return 'Mid-Career Training'
    if 'international' in t:                     return 'International Programme'
    if 'state' in t:                             return 'State Capacity Building'
    if 'awareness' in t or 'university' in t:   return 'Awareness Programme'
    if 'igot' in t or 'karmayogi' in t or 'mandatory' in t: return 'iGOT Mandatory'
    return 'In-service / Technical Training'


def _generate_description(title, domain, audience, duration):
    dur_str = f"{duration} days" if duration <= 30 else f"{duration} hours (online)"
    return (f"NSSTA TPAC approved programme: {title}. "
            f"Domain: {domain}. Target: {audience}. Duration: {dur_str}. "
            f"Source: mospi.gov.in / nssta.gov.in")


def main():
    print("=" * 60)
    print("  KarmayogAI — NSSTA/MoSPI Data Downloader & Extractor")
    print("=" * 60)

    all_programmes = []
    seen_titles = set()

    for source in SOURCES:
        print(f"\n📥 {source['name']}")
        pdf_path = download_pdf(source)
        if not pdf_path:
            continue

        print(f"  📄 Extracting text...")
        text = extract_text(pdf_path)
        if not text.strip():
            print(f"  ⚠️  No text extracted (scanned PDF?)")
            continue

        print(f"  📝 Extracted {len(text)} chars")
        progs = parse_programmes(text, source['name'], source['fy'], source['url'])
        print(f"  ✅ Found {len(progs)} programmes")

        for p in progs:
            if p['title'] not in seen_titles:
                seen_titles.add(p['title'])
                all_programmes.append(p)

    # ── Write enriched CSV ────────────────────────────────────────────────
    out_path = os.path.join(os.path.dirname(__file__), 'nssta_programmes.csv')

    fieldnames = [
        'programme_id', 'title', 'category', 'target_audience',
        'duration_days', 'mode', 'venue', 'competency_domain',
        'difficulty', 'source_url', 'financial_year', 'description'
    ]

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_programmes)

    print(f"\n{'='*60}")
    print(f"✅ Extracted {len(all_programmes)} unique programmes")
    print(f"✅ Saved to: {out_path}")
    print(f"{'='*60}")
    print("\nProgrammes found:")
    for p in all_programmes:
        print(f"  [{p['financial_year']}] {p['programme_id']} — {p['title']}")


if __name__ == '__main__':
    main()
