# structure_dictionary.py

# Map citations/filenames to Hierarchy Weight (10 = Apex, 1 = Lower)
HIERARCHY_MAP = {
    # FEDERAL
    'HCA': {'jurisdiction': 'CTH', 'court': 'High Court', 'weight': 10, 'type': 'Case'},
    'FCAFC': {'jurisdiction': 'CTH', 'court': 'Federal Court (Full)', 'weight': 9, 'type': 'Case'},
    'FCA': {'jurisdiction': 'CTH', 'court': 'Federal Court', 'weight': 7, 'type': 'Case'},
    'FamCAFC': {'jurisdiction': 'CTH', 'court': 'Family Court (Appeal)', 'weight': 8, 'type': 'Case'},
    'AATA': {'jurisdiction': 'CTH', 'court': 'Admin Appeals Tribunal', 'weight': 4, 'type': 'Tribunal'},
    'ART': {'jurisdiction': 'CTH', 'court': 'Admin Review Tribunal', 'weight': 4, 'type': 'Tribunal'},

    # NSW
    'NSWCA': {'jurisdiction': 'NSW', 'court': 'Court of Appeal', 'weight': 8, 'type': 'Case'},
    'NSWCCA': {'jurisdiction': 'NSW', 'court': 'Court of Criminal Appeal', 'weight': 8, 'type': 'Case'},
    'NSWSC': {'jurisdiction': 'NSW', 'court': 'Supreme Court', 'weight': 6, 'type': 'Case'},
    'NSWDC': {'jurisdiction': 'NSW', 'court': 'District Court', 'weight': 4, 'type': 'Case'},
    'NSWLC': {'jurisdiction': 'NSW', 'court': 'Local Court', 'weight': 2, 'type': 'Case'},
    'NSWCAT': {'jurisdiction': 'NSW', 'court': 'NCAT', 'weight': 3, 'type': 'Tribunal'},

    # VIC
    'VSCA': {'jurisdiction': 'VIC', 'court': 'Court of Appeal', 'weight': 8, 'type': 'Case'},
    'VSC': {'jurisdiction': 'VIC', 'court': 'Supreme Court', 'weight': 6, 'type': 'Case'},
    'VCAT': {'jurisdiction': 'VIC', 'court': 'VCAT', 'weight': 3, 'type': 'Tribunal'},

    # QLD
    'QCA': {'jurisdiction': 'QLD', 'court': 'Court of Appeal', 'weight': 8, 'type': 'Case'},
    'QSC': {'jurisdiction': 'QLD', 'court': 'Supreme Court', 'weight': 6, 'type': 'Case'},
    'QCAT': {'jurisdiction': 'QLD', 'court': 'QCAT', 'weight': 3, 'type': 'Tribunal'},
}

# Map keywords to Legislative Status
LEGISLATION_STATUS_MAP = {
    'Bill': {'type': 'Bill', 'status': 'Proposed', 'weight': 0},
    'Explanatory Memorandum': {'type': 'EM', 'status': 'Interpretive', 'weight': 1},
    'Second Reading': {'type': 'Speech', 'status': 'Interpretive', 'weight': 1},
    'Repealed': {'type': 'Act', 'status': 'Obsolete', 'weight': 0},
    'As made': {'type': 'Act', 'status': 'Historical', 'weight': 5},
    'In force': {'type': 'Act', 'status': 'Current', 'weight': 10},
    'Regulation': {'type': 'Regulation', 'status': 'Current', 'weight': 8},
    'Rules': {'type': 'Rules', 'status': 'Current', 'weight': 7},
}

# classification_dictionary.py

CLASSIFICATION_MAP = {
    # --- 1. PUBLIC LAW ---
    # 1.1 CRIMINAL
    'Criminal_Violence': [
        'murder', 'manslaughter', 'grievous bodily harm', 'wounding', 'assault occasioning', 
        'apprehended violence order', 'domestic violence', 'kidnapping', 'common assault', 'abh', 'gbh'
    ],
    'Criminal_Sexual': [
        'sexual intercourse without consent', 'indecent assault', 'child abuse material', 
        'sexual act', 'grooming', 'historical offence', 'sexual assault'
    ],
    'Criminal_Drugs': [
        'misuse of drugs', 'deemed supply', 'commercial quantity', 'prohibited drug', 
        'cultivation', 'drug misuse and trafficking', 'hydroponic', 'border controlled drug'
    ],
    'Criminal_Property': [
        'larceny', 'robbery', 'armed robbery', 'break and enter', 'fraud', 'dishonesty', 
        'arson', 'malicious damage', 'theft'
    ],
    'Criminal_Traffic': [
        'prescribed concentration of alcohol', 'drink driving', 'drug driving', 
        'negligent driving causing death', 'dangerous driving', 'license disqualification'
    ],
    'Criminal_Procedure': [
        'bail application', 'sentencing principles', 'parole board', 'crime commission', 
        'proceeds of crime', 'confiscation', 'criminal procedure act', 'jury act', 'beyond reasonable doubt'
    ],
    'Criminal_General': [
        'crimes act', 'conviction', 'acquittal', 'verdict' # Catch-all
    ],

    # 1.2 ADMINISTRATIVE
    'Admin_Migration': [
        'migration act', 'protection visa', 'visa cancellation', 'section 501', 
        'refugee review tribunal', 'immigration assessment authority', 'minister for immigration', 
        'deportation', 'skilled migration', 'detention'
    ],
    'Admin_Social_Security': [
        'social security act', 'disability support pension', 'centrelink', 
        'administrative appeals tribunal', 'aat', 'ndis act', 'national disability insurance', 
        'robodebt', 'jobseeker'
    ],
    'Admin_Veterans': [
        'veterans entitlements', 'military rehabilitation', 'mrca', 'war widow pension', 'dva'
    ],
    'Admin_Information': [
        'freedom of information', 'gipa act', 'government information (public access)', 
        'privacy act', 'app', 'access to documents', 'exempt document', 'surveillance devices'
    ],
    'Admin_Disciplinary': [
        'professional misconduct', 'unsatisfactory professional conduct', 'health practitioner regulation', 
        'removed from the roll', 'civil and administrative tribunal', 'ncat', 'vcat', 'qcat', 'occupational division'
    ],

    # 1.3 CONSTITUTIONAL
    'Constitutional_Federal': [
        'section 51', 'heads of power', 'section 109', 'inconsistency', 'section 92', 
        'free trade', 'separation of powers', 'boilermakers', 'constitutional writ'
    ],
    'Constitutional_State': [
        'legislative power', 'kable doctrine', 'state courts', 'election dispute'
    ],

    # 1.4 TAXATION
    'Tax_Federal': [
        'income tax assessment act', 'commissioner of taxation', 'tax benefit', 'part iva', 
        'fringe benefits tax', 'capital gains tax', 'gst act', 'input tax credit', 
        'transfer pricing', 'tax ruling', 'assessable income', 'deductible gift recipient'
    ],
    'Tax_State': [
        'payroll tax', 'land tax management act', 'duties act', 'stamp duty', 
        'transfer duty', 'parking space levy', 'chief commissioner of state revenue'
    ],

    # --- 2. PRIVATE LAW ---
    # 2.1 TORTS
    'Tort_Negligence': [
        'civil liability act', 'duty of care', 'breach of duty', 'causation', 
        'contributory negligence', 'risk of harm', 'obvious risk', 'negligence', 'personal injury', 
        'nervous shock', 'occupiers liability'
    ],
    'Tort_Defamation': [
        'defamation act', 'imputation', 'concerns notice', 'serious harm', 
        'qualified privilege', 'defence of truth', 'honest opinion', 'libel', 'slander'
    ],
    'Tort_Medical': [
        'medical negligence', 'failure to warn', 'wrongful birth', 'wrongful life'
    ],
    'Tort_Institutional': [
        'vicarious liability', 'historic abuse', 'institutional abuse'
    ],
    'Tort_Intentional': [
        'trespass to person', 'battery', 'false imprisonment', 'malicious prosecution', 'trespass to land'
    ],
    'Tort_Nuisance': [
        'private nuisance', 'public nuisance', 'tree dispute'
    ],

    # 2.2 COMPENSATION
    'Comp_Workers': [
        'workers compensation act', 'work capacity decision', 'whole person impairment', 'wpi'
    ],
    'Comp_Motor_Accidents': [
        'motor accidents compensation', 'ctp', 'lifetime care and support', 'blameless accident'
    ],
    'Comp_Victims': [
        'victims support scheme', 'recognition payment'
    ],

    # 2.3 EQUITY
    'Equity_General': [
        'estoppel', 'fiduciary duty', 'unconscionable conduct', 'undue influence', 'subrogation', 'promissory estoppel'
    ],
    'Equity_Trusts': [
        'express trust', 'discretionary trust', 'family trust', 'constructive trust', 
        'resulting trust', 'breach of trust', 'trustee duty'
    ],

    # 2.4 SUCCESSION
    'Succession_Probate': [
        'probate', 'letters of administration', 'validity of will', 'testamentary capacity', 'informal will'
    ],
    'Succession_Family_Provision': [
        'family provision', 'succession act', 'adequate provision', 'contested estate'
    ],

    # --- 3. COMMERCIAL ---
    # 3.1 CORPORATIONS
    'Corp_Governance': [
        'directors duties', 'care and diligence', 'oppression suit', 'minority shareholder', 'derivative action'
    ],
    'Corp_Insolvency': [
        'corporations act', 'winding up', 'statutory demand', 'liquidator', 
        'administrator', 'insolvent', 'voluntary administration', 'deed of company arrangement', 
        'voidable transaction', 'unfair preference', 'insolvent trading'
    ],

    # 3.2 COMMERCIAL TRANSACTIONS
    'Comm_Contract': [
        'breach of contract', 'specific performance', 'termination of contract', 'repudiation'
    ],
    'Comm_Banking': [
        'loan agreement', 'guarantee', 'mortgage possession', 'banking code'
    ],
    'Comm_Consumer': [
        'australian consumer law', 'misleading or deceptive', 'unfair contract terms', 'consumer guarantee', 'defective goods'
    ],
    'Comm_Insurance': [
        'insurance contract', 'non-disclosure', 'indemnity dispute', 'business interruption'
    ],

    # 3.3 IP
    'IP_Copyright': [
        'copyright act', 'infringement of copyright', 'fair dealing', 'moral rights', 
        'cinematograph film', 'literary work', 'broadcast right'
    ],
    'IP_Patent_Trademark': [
        'patents act', 'trade marks act', 'inventive step', 'priority date', 
        'deceptively similar', 'passing off', 'patent opposition', 'rectification of register'
    ],

    # --- 4. PROPERTY ---
    # 4.1 REAL PROPERTY
    'Prop_Torrens': [
        'real property act', 'conveyancing act', 'caveat', 'indefeasibility', 
        'fraud exception', 'priority dispute', 'torrens title'
    ],
    'Prop_Leasing': [
        'commercial lease', 'retail leases act', 'relief against forfeiture'
    ],
    'Prop_Strata': [
        'strata schemes', 'owners corporation', 'by-laws', 'strata levy'
    ],
    'Prop_Neighbours': [
        'easement', 'covenant', 'encroachment', 'dividing fences', 'trees dispute'
    ],
    # 4.2 PLANNING
    'Env_Development': [
        'environmental planning', 'development application', 'merits review', 'zoning', 'modification application'
    ],
    'Env_Protection': [
        'pollution offence', 'waste dumping', 'contaminated land', 'biodiversity conservation'
    ],
    'Env_Compulsory_Acq': [
        'just terms compensation', 'land valuation', 'valuer-general', 'compulsory acquisition'
    ],
    'Native_Title': [
        'native title', 'indigenous land use agreement', 'ilua'
    ],

    # --- 5. FAMILY ---
    'Family_Parenting': [
        'parenting order', 'best interests of the child', 'relocation', 'recovery order', 
        'custody', 'live with', 'spend time with'
    ],
    'Family_Property': [
        'property settlement', 'spousal maintenance', 'superannuation splitting', 'asset division'
    ],
    'Family_Child_Protection': [
        'care order', 'removal of child', 'department of communities', 'childrens court'
    ],
    'Family_Violence': [
        'family violence', 'intervention order', 'safety prohibition', 'fvio'
    ],
    'Family_General': [
        'family law act', 'fcfcoa', 'family court', 'divorce' # Catch-all
    ],

    # --- 6. PROCEDURAL ---
    'Proc_Civil': [
        'uniform civil procedure', 'ucpr', 'statement of claim', 'security for costs', 
        'summary judgment', 'strike out', 'indemnity costs'
    ],
    'Proc_Evidence': [
        'evidence act', 'admissibility', 'hearsay', 'tendency', 'coincidence', 'legal professional privilege', 'public interest immunity'
    ],
    'Proc_Enforcement': [
        'garnishee order', 'writ of levy'
    ],

    # --- 7. INDUSTRIAL ---
    'Ind_Employment': [
        'fair work act', 'unfair dismissal', 'general protections', 'adverse action', 'restraint of trade', 'employment contract'
    ],
    'Ind_Industrial': [
        'enterprise agreement', 'modern award', 'industrial action', 'right of entry', 'union'
    ],
    'Ind_Safety': [
        'work health and safety', 'industrial manslaughter', 'safework', 'whs prosecution'
    ],

    # --- 8. SPECIALIZED ---
    'Spec_Maritime': ['admiralty', 'carriage of goods by sea'],
    'Spec_Aviation': ['carrier liability', 'montreal convention', 'civil aviation'],
    'Spec_Mental_Health': ['involuntary treatment', 'mental health tribunal', 'treatment order'],
    'Spec_Coronial': ['inquest', 'coroner', 'finding of death']
}

# Domain Mapping (Granular -> Broad)
DOMAIN_MAPPING = {
    'Family': ['Family_Parenting', 'Family_Property', 'Family_Child_Protection', 'Family_Violence', 'Family_General'],
    'Criminal': ['Criminal_Violence', 'Criminal_Sexual', 'Criminal_Drugs', 'Criminal_Property', 'Criminal_Traffic', 'Criminal_Procedure', 'Criminal_General'],
    'Administrative': ['Admin_Migration', 'Admin_Social_Security', 'Admin_Veterans', 'Admin_Information', 'Admin_Disciplinary'],
    'Constitutional': ['Constitutional_Federal', 'Constitutional_State'],
    'Tax': ['Tax_Federal', 'Tax_State'],
    'Torts': ['Tort_Negligence', 'Tort_Defamation', 'Tort_Medical', 'Tort_Institutional', 'Tort_Intentional', 'Tort_Nuisance', 'Comp_Workers', 'Comp_Motor_Accidents', 'Comp_Victims'],
    'Equity': ['Equity_General', 'Equity_Trusts', 'Succession_Probate', 'Succession_Family_Provision'],
    'Commercial': ['Corp_Governance', 'Corp_Insolvency', 'Comm_Contract', 'Comm_Banking', 'Comm_Consumer', 'Comm_Insurance', 'IP_Copyright', 'IP_Patent_Trademark'],
    'Property': ['Prop_Torrens', 'Prop_Leasing', 'Prop_Strata', 'Prop_Neighbours', 'Env_Development', 'Env_Protection', 'Env_Compulsory_Acq', 'Native_Title'],
    'Industrial': ['Ind_Employment', 'Ind_Industrial', 'Ind_Safety'],
    'Procedural': ['Proc_Civil', 'Proc_Evidence', 'Proc_Enforcement'],
    'Specialized': ['Spec_Maritime', 'Spec_Aviation', 'Spec_Mental_Health', 'Spec_Coronial']
}
