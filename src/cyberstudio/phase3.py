"""Phase 3 additive compliance and operations domain services.

Offline, organization-scoped, audited data entry. Nothing here certifies compliance,
authenticates the claimed human reviewer, or checks external vulnerability feeds.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any

from .phase2 import Phase2Service, _csv_data
from .service import NotFoundError, ValidationError, _required, _rows, uid, utc_now

P3_SCHEMA = """
CREATE TABLE IF NOT EXISTS control_evaluations (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
    framework_key TEXT NOT NULL, control_code TEXT NOT NULL,
    implementation TEXT NOT NULL CHECK(implementation IN ('not_assessed','planned','partial','implemented','not_applicable')),
    test_result TEXT NOT NULL CHECK(test_result IN ('not_tested','pass','partial','fail','not_applicable')),
    rationale TEXT NOT NULL, evaluator TEXT NOT NULL, evaluated_at TEXT NOT NULL,
    evidence_id TEXT, evidence_verified INTEGER NOT NULL DEFAULT 0 CHECK(evidence_verified IN (0,1)),
    FOREIGN KEY(framework_key, control_code) REFERENCES framework_controls(framework_key,code),
    FOREIGN KEY(evidence_id, organization_id) REFERENCES evidence_records(id,organization_id),
    UNIQUE(id,organization_id)
);
CREATE TABLE IF NOT EXISTS control_evaluation_current (
    organization_id TEXT NOT NULL, framework_key TEXT NOT NULL, control_code TEXT NOT NULL,
    evaluation_id TEXT NOT NULL, PRIMARY KEY(organization_id,framework_key,control_code),
    FOREIGN KEY(evaluation_id,organization_id) REFERENCES control_evaluations(id,organization_id)
);
CREATE TABLE IF NOT EXISTS vendors (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL, service_category TEXT NOT NULL DEFAULT '', criticality TEXT NOT NULL,
    data_access TEXT NOT NULL, baa_applicability TEXT NOT NULL,
    owner TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(id,organization_id), UNIQUE(organization_id,name),
    CHECK(criticality IN ('low','moderate','high','critical')),
    CHECK(data_access IN ('unknown','none','internal','confidential','regulated')),
    CHECK(baa_applicability IN ('unknown','yes','no','not_applicable')),
    CHECK(status IN ('active','inactive'))
);
CREATE TABLE IF NOT EXISTS vendor_import_annotations (
    vendor_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL,
    source_findings TEXT NOT NULL, source_status TEXT NOT NULL,
    source_criticality TEXT NOT NULL, source_baa TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    FOREIGN KEY(vendor_id,organization_id) REFERENCES vendors(id,organization_id)
);
CREATE TABLE IF NOT EXISTS vendor_reviews (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, vendor_id TEXT NOT NULL,
    reviewed_by TEXT NOT NULL, findings TEXT NOT NULL, risk_score INTEGER NOT NULL CHECK(risk_score BETWEEN 1 AND 25),
    review_date TEXT NOT NULL, next_review_date TEXT NOT NULL, decision TEXT NOT NULL
      CHECK(decision IN ('pending','needs_remediation','reviewed')),
    created_at TEXT NOT NULL,
    FOREIGN KEY(vendor_id,organization_id) REFERENCES vendors(id,organization_id)
);
CREATE TABLE IF NOT EXISTS vulnerabilities (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
    title TEXT NOT NULL, source TEXT NOT NULL, external_id TEXT NOT NULL DEFAULT '',
    asset_name TEXT NOT NULL DEFAULT '', cvss REAL,
    severity TEXT NOT NULL CHECK(severity IN ('unknown','low','medium','high','critical')),
    status TEXT NOT NULL CHECK(status IN ('open','in_progress','mitigated','accepted','false_positive')),
    identified_on TEXT NOT NULL, due_on TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    UNIQUE(id,organization_id), UNIQUE(organization_id,source,external_id),
    CHECK(cvss IS NULL OR (cvss>=0 AND cvss<=10))
);
CREATE TABLE IF NOT EXISTS vulnerability_history (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, vulnerability_id TEXT NOT NULL,
    old_status TEXT, new_status TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY(vulnerability_id,organization_id) REFERENCES vulnerabilities(id,organization_id)
);
CREATE TABLE IF NOT EXISTS imported_control_inventory (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
    title TEXT NOT NULL, source_control_id TEXT NOT NULL DEFAULT '', source_standard TEXT NOT NULL DEFAULT '',
    source_implementation TEXT NOT NULL DEFAULT '', source_evidence_url TEXT NOT NULL DEFAULT '',
    source_review_date TEXT NOT NULL DEFAULT '', verification TEXT NOT NULL DEFAULT 'unverified',
    imported_at TEXT NOT NULL, UNIQUE(organization_id,title)
);
CREATE TABLE IF NOT EXISTS security_policies (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
    title TEXT NOT NULL, version TEXT NOT NULL DEFAULT '', owner TEXT NOT NULL DEFAULT '',
    next_review_on TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'unverified'
      CHECK(status IN ('unverified','draft','in_review','approved','retired')),
    source_url TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
    UNIQUE(id,organization_id), UNIQUE(organization_id,title)
);
CREATE TABLE IF NOT EXISTS incident_records (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
    title TEXT NOT NULL, source_incident_id TEXT NOT NULL DEFAULT '',
    severity TEXT NOT NULL DEFAULT '', source_status TEXT NOT NULL DEFAULT '',
    detected_at TEXT NOT NULL DEFAULT '', resolved_at TEXT NOT NULL DEFAULT '',
    root_cause TEXT NOT NULL DEFAULT '', imported_unverified INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL, UNIQUE(id,organization_id), UNIQUE(organization_id,title)
);
CREATE TABLE IF NOT EXISTS notion_import_jobs_p3 (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
    source_type TEXT NOT NULL, filename TEXT NOT NULL, sha256 TEXT NOT NULL,
    imported_count INTEGER NOT NULL, created_at TEXT NOT NULL,
    UNIQUE(organization_id,source_type,sha256)
);
CREATE INDEX IF NOT EXISTS idx_eval_org ON control_evaluations(organization_id,framework_key,control_code);
CREATE INDEX IF NOT EXISTS idx_vendor_org ON vendors(organization_id,name);
CREATE INDEX IF NOT EXISTS idx_vendor_review_org ON vendor_reviews(organization_id,vendor_id);
CREATE INDEX IF NOT EXISTS idx_vuln_org ON vulnerabilities(organization_id,status,severity);
CREATE INDEX IF NOT EXISTS idx_policy_org ON security_policies(organization_id,title);
CREATE INDEX IF NOT EXISTS idx_incident_org ON incident_records(organization_id,title);
CREATE TRIGGER IF NOT EXISTS p3_evaluation_immutable BEFORE UPDATE ON control_evaluations BEGIN SELECT RAISE(ABORT,'control evaluations immutable'); END;
CREATE TRIGGER IF NOT EXISTS p3_evaluation_nodelete BEFORE DELETE ON control_evaluations BEGIN SELECT RAISE(ABORT,'control evaluations immutable'); END;
CREATE TRIGGER IF NOT EXISTS p3_vendor_review_immutable BEFORE UPDATE ON vendor_reviews BEGIN SELECT RAISE(ABORT,'vendor review history immutable'); END;
CREATE TRIGGER IF NOT EXISTS p3_vendor_review_nodelete BEFORE DELETE ON vendor_reviews BEGIN SELECT RAISE(ABORT,'vendor review history immutable'); END;
CREATE TRIGGER IF NOT EXISTS p3_vuln_history_immutable BEFORE UPDATE ON vulnerability_history BEGIN SELECT RAISE(ABORT,'vulnerability history immutable'); END;
CREATE TRIGGER IF NOT EXISTS p3_vuln_history_nodelete BEFORE DELETE ON vulnerability_history BEGIN SELECT RAISE(ABORT,'vulnerability history immutable'); END;
CREATE TRIGGER IF NOT EXISTS p3_import_immutable BEFORE UPDATE ON notion_import_jobs_p3 BEGIN SELECT RAISE(ABORT,'import jobs immutable'); END;
CREATE TRIGGER IF NOT EXISTS p3_import_nodelete BEFORE DELETE ON notion_import_jobs_p3 BEGIN SELECT RAISE(ABORT,'import jobs immutable'); END;
"""

IMPORT_TYPES = {
    'compliance_controls': ('Control Name', 'Control ID', 'Implementation Status'),
    'security_policies': ('Policy Name', 'Approval Status'),
    'vendor_assessments': ('Vendor Name', 'Assessment Status'),
    'incident_tracker': ('Incident Name', 'Status'),
}


def _valid_date(value: str, field: str, *, allow_empty: bool=True) -> str:
    value=(value or '').strip()
    if not value and allow_empty: return ''
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValidationError(f'{field} must use YYYY-MM-DD') from exc


def _limited(value: str, field: str, limit: int=500) -> str:
    if len(value)>limit:
        raise ValidationError(f'{field} is longer than {limit} characters')
    return value.strip()


def _source_date(value: str) -> str:
    """Notion may export timestamp strings; preserve only correctly parsable date components."""
    value=(value or '').strip()
    if not value: return ''
    # Example: 2026-10-10 or 2026-10-10T14:20:00.000Z or 2026-10-10 14:20.
    return _valid_date(value[:10], 'CSV date')


class Phase3Service(Phase2Service):
    def __init__(self,vault):
        if int(vault.db.execute('PRAGMA user_version').fetchone()[0])>3:
            raise ValidationError('Vault was created by a newer application version; upgrade the software')
        super().__init__(vault)
        if not any(r['name']=='expires_on' for r in self.db.execute('PRAGMA table_info(evidence_records)')):
            self.db.execute("ALTER TABLE evidence_records ADD COLUMN expires_on TEXT NOT NULL DEFAULT ''")
        self.db.executescript(P3_SCHEMA)
        with self.vault.transaction() as conn:
            conn.execute('PRAGMA user_version=3')

    # Evidence expiry is a derived effective state, not silent modification of reviewer assertions.
    def set_evidence_expiration(self,org: str,eid: str,expires_on: str) -> None:
        self._org(org)
        if not self.db.execute('SELECT 1 FROM evidence_records WHERE id=? AND organization_id=?',(eid,org)).fetchone():
            raise NotFoundError('Evidence not found in this organization')
        expires_on=_valid_date(expires_on,'Evidence expiration')
        with self.vault.transaction() as conn:
            conn.execute('UPDATE evidence_records SET expires_on=? WHERE id=? AND organization_id=?',(expires_on,eid,org))
            self._audit(conn,org,'evidence',eid,'expiration_set',{'expires_on':expires_on})

    def evidence(self,org: str) -> list[dict[str,Any]]:
        data=super().evidence(org)
        dates={r['id']:r['expires_on'] for r in self.db.execute('SELECT id,expires_on FROM evidence_records WHERE organization_id=?',(org,))}
        for e in data:
            e['expires_on']=dates[e['id']]
            e['effective_status']='expired' if e['expires_on'] and e['expires_on']<date.today().isoformat() else e['review_status']
        return data

    def add_evidence(self,org: str,title: str,filename: str,data: bytes,
                     mime_type: str='application/octet-stream',expires_on: str='') -> str:
        expires_on=_valid_date(expires_on,'Evidence expiration')
        eid=super().add_evidence(org,title,filename,data,mime_type)
        if expires_on:
            self.set_evidence_expiration(org,eid,expires_on)
        return eid

    def record_risk_decision(self,org: str,risk: str,decision: str,approver: str,rationale: str,
                             expires_on: str='',attested: bool=False,*,operator_passphrase: str|None=None) -> str:
        # Re-authenticate local vault operator for all acceptance decisions.
        # This does NOT verify the identity/authorization of the named approver.
        if not operator_passphrase or not self.vault.verify_passphrase(operator_passphrase):
            raise ValidationError('Current vault passphrase re-entry required for acceptance decisions')
        decision_id=super().record_risk_decision(org,risk,decision,approver,rationale,expires_on,attested)
        with self.vault.transaction() as conn:
            self._audit(conn,org,'risk',risk,'vault_operator_reauthenticated',
                        {'decision_id':decision_id,'named_approver_unverified':True})
        return decision_id

    def _evidence_fresh_verified(self,org: str,eid: str) -> bool:
        row=self.db.execute('SELECT review_status,expires_on FROM evidence_records WHERE id=? AND organization_id=?',(eid,org)).fetchone()
        if row is None: raise NotFoundError('Evidence is not in selected organization')
        return row['review_status']=='verified' and (not row['expires_on'] or row['expires_on']>=date.today().isoformat())

    def evaluate_control(self,org: str,framework_key: str,control_code: str,implementation: str,
                         test_result: str,evaluator: str,rationale: str,evidence_id: str|None=None) -> str:
        self._org(org)
        if not self.db.execute('SELECT 1 FROM framework_controls WHERE framework_key=? AND code=?',(framework_key,control_code)).fetchone():
            raise ValidationError('Unknown framework identifier or control')
        if implementation not in {'not_assessed','planned','partial','implemented','not_applicable'}:
            raise ValidationError('Unsupported implementation status')
        if test_result not in {'not_tested','pass','partial','fail','not_applicable'}:
            raise ValidationError('Unsupported test result')
        if implementation=='not_applicable' and test_result!='not_applicable':
            raise ValidationError('Not applicable implementation must have not applicable test')
        if test_result=='pass' and implementation!='implemented':
            raise ValidationError('Passing a control requires implemented status')
        evaluator=_required(evaluator,'Evaluator',200)
        rationale=_required(rationale,'Testing rationale',3000)
        verified=self._evidence_fresh_verified(org,evidence_id) if evidence_id else False
        stamp=utc_now(); cid=uid()
        with self.vault.transaction() as conn:
            conn.execute('INSERT INTO control_evaluations VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (cid,org,framework_key,control_code,implementation,test_result,rationale,evaluator,stamp,evidence_id,int(verified)))
            conn.execute('INSERT INTO control_evaluation_current VALUES(?,?,?,?) ON CONFLICT(organization_id,framework_key,control_code) DO UPDATE SET evaluation_id=excluded.evaluation_id',
                (org,framework_key,control_code,cid))
            self._audit(conn,org,'control',cid,'evaluated',{'framework_key':framework_key,'control_code':control_code,'test_result':test_result,'evidence_eligible_at_review':verified})
        return cid

    def control_evaluations(self,org: str) -> list[dict[str,Any]]:
        self._org(org)
        rows=_rows(self.db.execute('''SELECT e.*,f.title AS control_title
           FROM control_evaluation_current c JOIN control_evaluations e ON e.id=c.evaluation_id
           JOIN framework_controls f ON f.framework_key=e.framework_key AND f.code=e.control_code
           WHERE c.organization_id=? ORDER BY e.framework_key,e.control_code''',(org,)))
        for r in rows:
            r['evidence_currently_eligible']=bool(r['evidence_id'] and self._evidence_fresh_verified(org,r['evidence_id']))
            r['verified_pass']=bool(r['test_result']=='pass' and r['implementation']=='implemented'
                and r['evidence_currently_eligible'])
        return rows

    def create_vendor(self,org: str,name: str,service_category: str='',criticality: str='moderate',
                      data_access: str='unknown',baa_applicability: str='unknown',owner: str='') -> str:
        self._org(org);name=_required(name,'Vendor name')
        if criticality not in {'low','moderate','high','critical'} or data_access not in {'unknown','none','internal','confidential','regulated'} or baa_applicability not in {'unknown','yes','no','not_applicable'}:
            raise ValidationError('Invalid vendor classification')
        service_category=_limited(service_category,'Service category',200);owner=_limited(owner,'Vendor owner',200)
        vendor=uid();stamp=utc_now()
        try:
            with self.vault.transaction() as conn:
                conn.execute('INSERT INTO vendors VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                    (vendor,org,name,service_category,criticality,data_access,baa_applicability,owner,'active',stamp,stamp))
                self._audit(conn,org,'vendor',vendor,'create',{'name':name})
        except sqlite3.IntegrityError as exc:
            raise ValidationError('Vendor already exists in this organization') from exc
        return vendor

    def vendors(self,org: str) -> list[dict[str,Any]]:
        self._org(org)
        rows=_rows(self.db.execute('SELECT * FROM vendors WHERE organization_id=? ORDER BY name',(org,)))
        for r in rows:
            review=self.db.execute('SELECT * FROM vendor_reviews WHERE organization_id=? AND vendor_id=? ORDER BY rowid DESC LIMIT 1',(org,r['id'])).fetchone()
            r['last_review']=review['review_date'] if review else ''
            r['next_review']=review['next_review_date'] if review else ''
            r['review_state']=('missing' if not review else 'overdue' if review['next_review_date']<date.today().isoformat() else review['decision'])
            r['risk_score']=review['risk_score'] if review else None
        return rows

    def record_vendor_review(self,org: str,vendor: str,reviewer: str,findings: str,
                             likelihood: int,impact: int,next_review_date: str,decision: str='pending') -> str:
        self._org(org)
        if not self.db.execute('SELECT 1 FROM vendors WHERE id=? AND organization_id=?',(vendor,org)).fetchone():
            raise NotFoundError('Vendor not found in this organization')
        reviewer=_required(reviewer,'Reviewer',200);findings=_required(findings,'Findings',5000)
        if decision not in {'pending','needs_remediation','reviewed'}:raise ValidationError('Invalid vendor review decision')
        next_review_date=_valid_date(next_review_date,'Next vendor review',allow_empty=False)
        if next_review_date<=date.today().isoformat():raise ValidationError('Next review date must be in future')
        score,_=self.score(likelihood,impact)
        stamp=utc_now();rid=uid()
        with self.vault.transaction() as conn:
            conn.execute('INSERT INTO vendor_reviews VALUES(?,?,?,?,?,?,?,?,?,?)',
                (rid,org,vendor,reviewer,findings,score,date.today().isoformat(),next_review_date,decision,stamp))
            self._audit(conn,org,'vendor',vendor,'review',{'score':score,'review_id':rid})
        return rid

    def imported_vendor_annotations(self,org: str) -> list[dict[str,Any]]:
        self._org(org)
        return _rows(self.db.execute('SELECT a.*,v.name AS vendor_name FROM vendor_import_annotations a JOIN vendors v '
            'ON v.id=a.vendor_id AND v.organization_id=a.organization_id WHERE a.organization_id=?',(org,)))

    def vendor_reviews(self,org: str,vendor: str) -> list[dict[str,Any]]:
        self._org(org)
        if not self.db.execute('SELECT 1 FROM vendors WHERE id=? AND organization_id=?',(vendor,org)).fetchone():raise NotFoundError('Vendor not found')
        return _rows(self.db.execute('SELECT * FROM vendor_reviews WHERE organization_id=? AND vendor_id=? ORDER BY rowid DESC',(org,vendor)))

    def add_vulnerability(self,org: str,title: str,source: str,external_id: str='',severity: str='unknown',
                          cvss: float|None=None,asset_name: str='',due_on: str='',notes: str='') -> str:
        self._org(org);title=_required(title,'Vulnerability title');source=_required(source,'Source',200)
        external_id=_limited(external_id,'External ID',200);asset_name=_limited(asset_name,'Asset name',200)
        notes=_limited(notes,'Notes',3000);due_on=_valid_date(due_on,'Remediation due date')
        if severity not in {'unknown','low','medium','high','critical'}:raise ValidationError('Invalid severity')
        if cvss is not None and (isinstance(cvss,bool) or not isinstance(cvss,(float,int)) or not 0<=cvss<=10):
            raise ValidationError('CVSS must be a number from 0 to 10')
        # Blank external identifiers are assigned unique opaque placeholders in storage.
        stored_external_id=external_id or 'local-'+uid()
        rid=uid();stamp=utc_now()
        try:
            with self.vault.transaction() as conn:
                conn.execute('INSERT INTO vulnerabilities VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (rid,org,title,source,stored_external_id,asset_name,cvss,severity,'open',date.today().isoformat(),due_on,notes,stamp,stamp))
                self._audit(conn,org,'vulnerability',rid,'create',{'severity':severity,'source':source})
        except sqlite3.IntegrityError as exc:
            raise ValidationError('Duplicate vulnerability source and external identifier') from exc
        return rid

    def vulnerabilities(self,org: str) -> list[dict[str,Any]]:
        self._org(org)
        rows=_rows(self.db.execute('SELECT * FROM vulnerabilities WHERE organization_id=? ORDER BY CASE severity WHEN "critical" THEN 0 WHEN "high" THEN 1 WHEN "medium" THEN 2 ELSE 3 END, title',(org,)))
        for r in rows:
            r['overdue']=bool(r['due_on'] and r['due_on']<date.today().isoformat() and r['status'] not in ('mitigated','false_positive'))
        return rows

    def update_vulnerability(self,org: str,vid: str,status: str,actor: str,reason: str) -> None:
        self._org(org)
        row=self.db.execute('SELECT status FROM vulnerabilities WHERE id=? AND organization_id=?',(vid,org)).fetchone()
        if not row: raise NotFoundError('Vulnerability not found in this organization')
        if status not in {'open','in_progress','mitigated','accepted','false_positive'}:raise ValidationError('Invalid vulnerability status')
        actor=_required(actor,'Reviewer',200);reason=_required(reason,'Status change rationale',3000)
        if status==row['status']:return
        with self.vault.transaction() as conn:
            conn.execute('UPDATE vulnerabilities SET status=?,updated_at=? WHERE id=? AND organization_id=?',(status,utc_now(),vid,org))
            conn.execute('INSERT INTO vulnerability_history VALUES(?,?,?,?,?,?,?,?)',
                (uid(),org,vid,row['status'],status,actor,reason,utc_now()))
            self._audit(conn,org,'vulnerability',vid,'status_change',{'from':row['status'],'to':status})

    def executive_metrics(self,org: str) -> dict[str,Any]:
        self._org(org)
        risks=self.list_risks(org);tasks=self.list_tasks(org);controls=self.control_evaluations(org)
        evid=self.evidence(org);vendors=self.vendors(org);vulns=self.vulnerabilities(org)
        today=date.today().isoformat()
        return {
            'risks_total':len(risks),'high_inherent_open':sum(r['score']>=10 and r['status']!='closed' for r in risks),
            'high_residual_open':sum(r['residual_score'] is not None and r['residual_score']>=10 and r['status']!='closed' for r in risks),
            'acceptances_active':sum(r['acceptance_state']=='active' for r in risks),
            'acceptances_expired':sum(r['acceptance_state']=='expired' for r in risks),
            'controls_evaluated':len(controls),'controls_test_pass':sum(c['test_result']=='pass' for c in controls),
            'controls_evidence_supported':sum(c['verified_pass'] for c in controls),
            'evidence_expired':sum(e['effective_status']=='expired' for e in evid),
            'evidence_unverified':sum(e['effective_status']!='verified' for e in evid),
            'vendor_reviews_overdue':sum(v['review_state'] in ('overdue','missing') for v in vendors),
            'vulnerabilities_high_open':sum(v['severity'] in ('high','critical') and v['status'] in ('open','in_progress') for v in vulns),
            'vulnerabilities_overdue':sum(v['overdue'] for v in vulns),
            'remediation_overdue':sum(bool(t['due_date']) and t['due_date']<today and t['status']!='done' for t in tasks),
            'as_of':today,
        }

    # Import creates *unverified records*; no identities/approvals/control assertions are silently accepted.
    def _parse_import_row(self,kind: str,row: dict[str,str],line: int,org_name: str) -> dict[str,Any]:
        if (row.get('Client') or '').strip() and row['Client'].strip().casefold()!=org_name.casefold():
            raise ValidationError('Client does not match selected organization')
        fields=IMPORT_TYPES[kind]
        title=_required(row.get(fields[0]) or '',fields[0])
        out={'source_row':line,'title':title}
        if kind=='compliance_controls':
            out['control_id']=_limited(row.get('Control ID') or '', 'Control ID',100)
            out['source_implementation']=_limited(row.get('Implementation Status') or '','Implementation Status',100)
            out['standard']=_limited(row.get('Standard') or '','Standard',200)
            out['source_url']=_limited(row.get('Evidence Artifact URL') or '','Evidence Artifact URL',1000)
            out['review_date']=_source_date(row.get('Review Date') or '')
        elif kind=='security_policies':
            out['version']=_limited(row.get('Version') or '','Version',80)
            out['owner']=_limited(row.get('Policy Owner') or '','Policy Owner',200)
            out['source_status']=_limited(row.get('Approval Status') or '','Approval Status',100)
            out['next_review_on']=_source_date(row.get('Next Review Date') or '')
            out['source_url']=_limited(row.get('Document Link') or '','Document Link',1000)
        elif kind=='vendor_assessments':
            out['category']=_limited(row.get('Service Category') or '', 'Service Category',200)
            out['findings']=_limited(row.get('Assessment Findings') or '', 'Assessment Findings',2000)
            out['source_status']=_limited(row.get('Assessment Status') or '', 'Assessment Status',100)
            out['source_criticality']=_limited(row.get('Criticality Tier') or '', 'Criticality Tier',100)
            out['source_baa']=_limited(row.get('BAA Applicability') or '', 'BAA Applicability',100)
        elif kind=='incident_tracker':
            out['source_incident_id']=_limited(row.get('Incident ID') or '', 'Incident ID',100)
            out['severity']=_limited(row.get('Severity') or '', 'Severity',100)
            out['source_status']=_limited(row.get('Status') or '', 'Status',100)
            out['detected_at']=_limited(row.get('Detected At') or '', 'Detected At',100)
            out['resolved_at']=_limited(row.get('Resolved At') or '', 'Resolved At',100)
            out['root_cause']=_limited(row.get('Root Cause') or '', 'Root Cause',2000)
        return out

    def preview_notion_module(self,org: str,payload: bytes,kind: str) -> dict[str,Any]:
        self._org(org)
        if kind not in IMPORT_TYPES:raise ValidationError('Unsupported Notion database type')
        rows,headers=_csv_data(payload)
        if not set(IMPORT_TYPES[kind]).issubset(headers):
            raise ValidationError(f'Unsupported {kind} CSV columns; expected {IMPORT_TYPES[kind]}')
        existing_table={'compliance_controls':'imported_control_inventory','security_policies':'security_policies',
                        'vendor_assessments':'vendors','incident_tracker':'incident_records'}[kind]
        keycol='title' if kind!='vendor_assessments' else 'name'
        existing={r[0].casefold() for r in self.db.execute(f'SELECT {keycol} FROM {existing_table} WHERE organization_id=?',(org,))}
        seen=set();good=[];preview=[];org_name=self.organization(org)['name']
        for line,row in enumerate(rows,2):
            try:
                normalized=self._parse_import_row(kind,row,line,org_name)
                key=normalized['title'].casefold()
                if key in seen or key in existing:raise ValidationError('Duplicate name in CSV or selected organization')
                seen.add(key);good.append(normalized)
                preview.append({'source_row':line,'title':normalized['title'],'status':'ready','message':'Source assertions unverified'})
            except ValidationError as exc:
                preview.append({'source_row':line,'title':str(row.get(IMPORT_TYPES[kind][0]) or '')[:100],
                                'status':'skip','message':str(exc)})
        digest=sha256(payload).hexdigest()
        imported=bool(self.db.execute('SELECT 1 FROM notion_import_jobs_p3 WHERE organization_id=? AND source_type=? AND sha256=?',(org,kind,digest)).fetchone())
        return {'source_type':kind,'count':len(rows),'ready':len(good),'skipped':len(rows)-len(good),
                'previously_imported':imported,'sha256':digest,'preview':preview,'normalized':good}

    def import_notion_module(self,org: str,payload: bytes,kind: str,filename: str,*,confirmed: bool=False) -> dict[str,Any]:
        if not confirmed:raise ValidationError('Explicit user import confirmation required')
        summary=self.preview_notion_module(org,payload,kind)
        if summary['previously_imported'] or summary['skipped'] or not summary['ready']:
            raise ValidationError('Import blocked: duplicate file, invalid entries, or no records; nothing was changed')
        filename=_required(Path(filename).name,'Import filename',255)
        stamp=utc_now();job=uid()
        with self.vault.transaction() as conn:
            conn.execute('INSERT INTO notion_import_jobs_p3 VALUES(?,?,?,?,?,?,?)',
                         (job,org,kind,filename,summary['sha256'],summary['ready'],stamp))
            for row in summary['normalized']:
                rid=uid()
                if kind=='compliance_controls':
                    conn.execute('INSERT INTO imported_control_inventory VALUES(?,?,?,?,?,?,?,?,?,?)',
                        (rid,org,row['title'],row['control_id'],row['standard'],row['source_implementation'],row['source_url'],row['review_date'],'unverified',stamp))
                elif kind=='security_policies':
                    conn.execute('INSERT INTO security_policies VALUES(?,?,?,?,?,?,?,?,?)',
                        (rid,org,row['title'],row['version'],row['owner'],row['next_review_on'],'unverified',row['source_url'],stamp))
                elif kind=='vendor_assessments':
                    conn.execute('INSERT INTO vendors VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                        (rid,org,row['title'],row['category'],'moderate','unknown','unknown','','active',stamp,stamp))
                    conn.execute('INSERT INTO vendor_import_annotations VALUES(?,?,?,?,?,?,?)',
                        (rid,org,row['findings'],row['source_status'],row['source_criticality'],row['source_baa'],stamp))
                else:
                    conn.execute('INSERT INTO incident_records VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                        (rid,org,row['title'],row['source_incident_id'],row['severity'],row['source_status'],row['detected_at'],row['resolved_at'],row['root_cause'],1,stamp))
            self._audit(conn,org,'notion_import',job,'completed',{'source_type':kind,'count':summary['ready'],'source_assertions_verified':False})
        return {'job_id':job,'source_type':kind,'imported':summary['ready'],'verification':'unverified'}

    def imported_control_inventory(self,org: str) -> list[dict[str,Any]]:
        self._org(org)
        return _rows(self.db.execute('SELECT * FROM imported_control_inventory WHERE organization_id=? ORDER BY title',(org,)))

    def policies(self,org: str) -> list[dict[str,Any]]:
        self._org(org)
        return _rows(self.db.execute('SELECT * FROM security_policies WHERE organization_id=? ORDER BY title',(org,)))

    def incidents(self,org: str) -> list[dict[str,Any]]:
        self._org(org)
        return _rows(self.db.execute('SELECT * FROM incident_records WHERE organization_id=? ORDER BY title',(org,)))

    def import_history_p3(self,org: str) -> list[dict[str,Any]]:
        self._org(org)
        return _rows(self.db.execute('SELECT * FROM notion_import_jobs_p3 WHERE organization_id=? ORDER BY created_at',(org,)))
