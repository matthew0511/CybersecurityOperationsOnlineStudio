"""PySide6 desktop UI for Phase 3.

Run `python -m cyberstudio`. UI requires optional graphical runtime PySide6,
not available in all headless test environments.
"""
from __future__ import annotations

import sys
from pathlib import Path

from platformdirs import user_data_dir
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QSpinBox, QTableWidget, QCheckBox,
    QTableWidgetItem, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from .reports_phase3 import export_executive_pdf as export_pdf, export_executive_xlsx as export_xlsx
from .enterprise import EnterpriseGovernanceService as StudioService
from .governance_reports import board_packet
from .vault import Vault, VaultError

APP_TITLE = "Cyber Security Operations Online Studio — Preview 0.3"
THEME = """
QWidget { background:#101b2a; color:#e9f0f9; font-family:'Segoe UI'; font-size:12px; }
QMainWindow, QDialog { background:#101b2a; }
QLabel#headline { font-size:22px; font-weight:700; color:#ffffff; }
QLabel#muted { color:#a6b6ca; }
QPushButton { background:#2477b9; color:#fff; border:0; padding:9px 13px; border-radius:6px; font-weight:600; }
QPushButton:hover { background:#3292d8; }
QLineEdit, QTextEdit, QComboBox, QSpinBox, QTableWidget {
    background:#172638; color:#f2f5fa; border:1px solid #38516c; border-radius:5px;
    padding:5px; selection-background-color:#2776b4; }
QTabWidget::pane { border:1px solid #33475d; }
QTabBar::tab { background:#1c3045; padding:11px; margin-right:2px; }
QTabBar::tab:selected { background:#2875ad; }
QHeaderView::section { background:#263e55; color:#fff; padding:7px; border:0; }
QTableWidget { gridline-color:#31465c; }
QGroupBox { border:1px solid #32485e; margin-top:8px; padding:12px; border-radius:6px; }
"""


def table(headers: list[str]) -> QTableWidget:
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    widget.setAlternatingRowColors(True)
    return widget


def item(value: object, ident: str | None = None) -> QTableWidgetItem:
    cell = QTableWidgetItem("" if value is None else str(value))
    if ident:
        cell.setData(Qt.ItemDataRole.UserRole, ident)
    return cell


class MainWindow(QMainWindow):
    def __init__(self, vault: Vault):
        super().__init__()
        self.vault = vault
        self.service = StudioService(vault)
        self.setWindowTitle(APP_TITLE)
        self.resize(1240, 795)
        self.assessment_id: str | None = None
        self.org_selector = QComboBox()
        self.org_selector.currentIndexChanged.connect(self.organization_changed)
        self.build_ui()
        self.load_organizations()

    def org(self) -> str | None:
        return self.org_selector.currentData()

    def message(self, title: str, message: str, *, error: bool = False) -> None:
        (QMessageBox.critical if error else QMessageBox.information)(self, title, message)

    def protect(self, callback):
        try:
            callback()
        except Exception as exc:
            self.message("Operation could not be completed", str(exc), error=True)

    def build_ui(self) -> None:
        outer = QWidget()
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(22, 18, 22, 18)
        header = QHBoxLayout()
        name = QLabel("Cyber Security Operations Online Studio")
        name.setObjectName("headline")
        header.addWidget(name)
        header.addStretch(1)
        header.addWidget(QLabel("Organization:"))
        self.org_selector.setMinimumWidth(230)
        header.addWidget(self.org_selector)
        add = QPushButton("+ Organization")
        add.clicked.connect(lambda: self.protect(self.add_organization))
        header.addWidget(add)
        layout.addLayout(header)
        notice = QLabel("PHASE 3 PREVIEW • Offline • Manual records and reviewer statements do NOT establish compliance")
        notice.setObjectName("muted")
        layout.addWidget(notice)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.build_dashboard()
        self.build_assessments()
        self.build_questions()
        self.build_risks()
        self.build_remediation()
        self.build_reports()
        self.build_frameworks()
        self.build_templates()
        self.build_evidence()
        self.build_notion_import()
        self.build_controls()
        self.build_vendors()
        self.build_vulnerabilities()
        self.build_operations_inventory()
        self.build_settings()
        self.build_vciso()
        self.build_governance()
        self.build_enterprise_governance()
        self.setCentralWidget(outer)
        self.statusBar().showMessage("Local encrypted vault is unlocked. Save/close to lock.")

    def build_dashboard(self) -> None:
        box = QWidget()
        v = QVBoxLayout(box)
        v.addWidget(QLabel("Portfolio snapshot for selected organization"))
        self.dash_label = QLabel("Create or select an organization to get started.")
        self.dash_label.setObjectName("headline")
        v.addWidget(self.dash_label)
        v.addWidget(QLabel("Start an assessment, document risks, assign remediation actions, then export a snapshot."))
        v.addStretch()
        self.tabs.addTab(box, "Dashboard")

    def build_assessments(self) -> None:
        box = QWidget()
        v = QVBoxLayout(box)
        row = QHBoxLayout()
        self.new_assessment_name = QLineEdit()
        self.new_assessment_name.setPlaceholderText("Assessment title")
        self.new_assessment_name.setMaxLength(250)
        row.addWidget(self.new_assessment_name)
        self.new_scope = QLineEdit()
        self.new_scope.setPlaceholderText("Scope (optional)")
        row.addWidget(self.new_scope)
        action = QPushButton("Create assessment")
        action.clicked.connect(lambda: self.protect(self.add_assessment))
        row.addWidget(action)
        v.addLayout(row)
        pick = QHBoxLayout()
        pick.addWidget(QLabel("Question set:"))
        self.new_assessment_template = QComboBox()
        self.new_assessment_template.addItem("Original Phase 1 example questions", None)
        pick.addWidget(self.new_assessment_template)
        v.addLayout(pick)
        self.assessment_table = table(["Assessment", "Status", "Framework", "Scope", "Created"])
        self.assessment_table.itemDoubleClicked.connect(lambda _i: self.select_assessment())
        v.addWidget(self.assessment_table)
        open_button = QPushButton("Open selected questionnaire")
        open_button.clicked.connect(lambda: self.protect(self.select_assessment))
        v.addWidget(open_button)
        self.tabs.addTab(box, "Assessments")

    def build_questions(self) -> None:
        box = QWidget()
        v = QVBoxLayout(box)
        self.question_title = QLabel("Select an assessment first")
        v.addWidget(self.question_title)
        self.questions_table = QTableWidget(0, 4)
        self.questions_table.setHorizontalHeaderLabels(["Code / domain", "Question", "Answer", "Rationale / evidence summary"])
        self.questions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.questions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.questions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.questions_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        v.addWidget(self.questions_table)
        save = QPushButton("Save questionnaire answers")
        save.clicked.connect(lambda: self.protect(self.save_answers))
        v.addWidget(save)
        mappings=QPushButton("View suggested control mappings")
        mappings.clicked.connect(lambda: self.protect(self.show_assessment_mappings))
        v.addWidget(mappings)
        self.tabs.addTab(box, "Questionnaire")

    def build_risks(self) -> None:
        box = QWidget()
        v = QVBoxLayout(box)
        top = QHBoxLayout()
        top.addWidget(QLabel("Risk register • Inherent score = likelihood × impact (1–25)"))
        top.addStretch()
        add = QPushButton("+ Add risk")
        add.clicked.connect(lambda: self.protect(self.add_risk))
        top.addWidget(add)
        v.addLayout(top)
        self.risk_table = table(["Risk", "Likelihood", "Impact", "Inherent", "Band", "Residual", "Acceptance", "Status", "Rationale"])
        v.addWidget(self.risk_table)
        actions = QHBoxLayout()
        residual = QPushButton("Set residual rating")
        residual.clicked.connect(lambda: self.protect(self.set_residual))
        actions.addWidget(residual)
        acceptance = QPushButton("Record acceptance decision")
        acceptance.clicked.connect(lambda: self.protect(self.record_acceptance))
        actions.addWidget(acceptance)
        v.addLayout(actions)
        self.tabs.addTab(box, "Risks")

    def build_remediation(self) -> None:
        box = QWidget()
        v = QVBoxLayout(box)
        actions = QHBoxLayout()
        actions.addWidget(QLabel("Remediation actions associated with documented risks"))
        actions.addStretch()
        add = QPushButton("+ Add action")
        add.clicked.connect(lambda: self.protect(self.add_task))
        actions.addWidget(add)
        status = QPushButton("Update selected status")
        status.clicked.connect(lambda: self.protect(self.change_task_status))
        actions.addWidget(status)
        v.addLayout(actions)
        self.task_table = table(["Action", "Owner", "Due", "Priority", "Status", "Risk ID"])
        v.addWidget(self.task_table)
        self.tabs.addTab(box, "Remediation")

    def build_reports(self) -> None:
        box = QWidget()
        v = QVBoxLayout(box)
        v.addWidget(QLabel("Executive operations snapshot for the selected organization, including Phase 3 registers."))
        pdf = QPushButton("Export executive PDF snapshot")
        pdf.clicked.connect(lambda: self.protect(lambda: self.export("pdf")))
        v.addWidget(pdf)
        xlsx = QPushButton("Export Excel workbook")
        xlsx.clicked.connect(lambda: self.protect(lambda: self.export("xlsx")))
        v.addWidget(xlsx)
        v.addWidget(QLabel("Reports are locally created and are not compliance certifications."))
        v.addStretch()
        self.tabs.addTab(box, "Reports")

    def build_frameworks(self) -> None:
        box=QWidget(); v=QVBoxLayout(box)
        v.addWidget(QLabel("Reference catalogs: NIST CSF 2.0 categories and CIS Controls 8.1 headings. Not the full standard."))
        choose=QHBoxLayout(); self.catalog_choice=QComboBox()
        self.catalog_choice.addItem("NIST Cybersecurity Framework 2.0", "NIST-CSF-2.0")
        self.catalog_choice.addItem("CIS Critical Security Controls 8.1", "CIS-CONTROLS-8.1")
        self.catalog_choice.currentIndexChanged.connect(lambda _x:self.protect(self.refresh_catalog))
        choose.addWidget(self.catalog_choice); v.addLayout(choose)
        self.catalog_table=table(["Identifier", "Title", "Domain"])
        v.addWidget(self.catalog_table)
        self.tabs.addTab(box,"Frameworks")

    def build_templates(self) -> None:
        box=QWidget(); v=QVBoxLayout(box)
        v.addWidget(QLabel("Custom question banks are scoped to the selected organization. Assessment snapshots do not change when a template changes."))
        actions=QHBoxLayout()
        for caption,func in [("New template",self.new_template),("Add question",self.new_template_question),
                             ("Seed original starter",self.seed_starter)]:
            b=QPushButton(caption);b.clicked.connect(lambda _x=False,f=func:self.protect(f));actions.addWidget(b)
        v.addLayout(actions)
        self.template_table=table(["Template", "Version", "Description", "Created"])
        self.template_table.itemSelectionChanged.connect(lambda:self.protect(self.load_template_questions))
        self.template_questions_table=table(["Question code", "Domain", "Question"])
        v.addWidget(self.template_table);v.addWidget(QLabel("Questions in selected template:"));v.addWidget(self.template_questions_table)
        self.tabs.addTab(box,"Templates")

    def build_evidence(self) -> None:
        box=QWidget();v=QVBoxLayout(box)
        v.addWidget(QLabel("Evidence files (up to 5 MiB) are stored in the encrypted vault. Review status is a manual assertion."))
        actions=QHBoxLayout()
        for caption,func in [("Add evidence file",self.add_evidence_file),("Link selected",self.link_selected_evidence),
                             ("Review selected",self.review_selected_evidence),("Save selected file",self.save_evidence_file),("Set expiration",self.expire_evidence)]:
            b=QPushButton(caption);b.clicked.connect(lambda _x=False,f=func:self.protect(f));actions.addWidget(b)
        v.addLayout(actions)
        self.evidence_table=table(["Title","Filename","SHA-256","Size","Effective status","Reviewer","Expires on"])
        v.addWidget(self.evidence_table);self.tabs.addTab(box,"Evidence")

    def build_notion_import(self) -> None:
        box=QWidget();v=QVBoxLayout(box)
        v.addWidget(QLabel("Import Notion CSVs locally. All source claims are unverified; no implicit approvals."))
        self.import_kind=QComboBox()
        for title,key in [("Risk Register", "risk_register"),("Compliance Tracker", "compliance_controls"),
                          ("Security Policies", "security_policies"),("Vendor Assessments", "vendor_assessments"),
                          ("Incident Response Tracker", "incident_tracker")]:
            self.import_kind.addItem(title,key)
        v.addWidget(self.import_kind)
        v.addWidget(QLabel("Import recalculates scores; source statuses and approval fields are NOT considered approvals."))
        choose=QPushButton("Preview and import selected Notion CSV")
        choose.clicked.connect(lambda:self.protect(self.import_notion))
        v.addWidget(choose)
        self.import_log=QTextEdit();self.import_log.setReadOnly(True)
        v.addWidget(self.import_log)
        self.tabs.addTab(box,"Notion Import")

    def refresh_phase2(self) -> None:
        self.refresh_catalog()
        org=self.org()
        self.new_assessment_template.blockSignals(True)
        self.new_assessment_template.clear()
        self.new_assessment_template.addItem("Original Phase 1 example questions",None)
        if org:
            templates=self.service.list_templates(org)
            self.fill(self.template_table,templates,["name","version","description","created_at"])
            for rec in templates:
                self.new_assessment_template.addItem(rec['name']+" (v"+str(rec['version'])+")",rec['id'])
            evid=self.service.evidence(org)
            self.fill(self.evidence_table,evid,["title","filename","sha256","size","effective_status","reviewed_by","expires_on"])
            history=self.service.import_history(org)
            additional=self.service.import_history_p3(org)
            self.import_log.setPlainText("\n".join(
                [f"{h['created_at']} | {h['filename']} | {h['imported_count']} risks imported" for h in history]
                +[f"{h['created_at']} | {h['filename']} | {h['imported_count']} {h['source_type']} records imported" for h in additional]))
        else:
            self.template_questions_table.setRowCount(0)
            self.import_log.clear()
        self.new_assessment_template.blockSignals(False)

    def refresh_catalog(self) -> None:
        if not hasattr(self,"catalog_table"):
            return
        controls=self.service.framework_controls(self.catalog_choice.currentData())
        self.catalog_table.setRowCount(len(controls))
        for r,c in enumerate(controls):
            for j,k in enumerate(("code","title","domain")):
                self.catalog_table.setItem(r,j,item(c[k]))

    def selected_id(self, widget: QTableWidget) -> str:
        row=widget.currentRow()
        if row<0 or widget.item(row,0) is None:
            raise ValueError("Select a record in the relevant table first")
        return widget.item(row,0).data(Qt.ItemDataRole.UserRole)

    def new_template(self) -> None:
        org=self.require_org()
        name,ok=QInputDialog.getText(self,"New template","Template name")
        if ok:
            self.service.create_template(org,name)
            self.refresh_all()

    def seed_starter(self) -> None:
        org=self.require_org()
        self.service.create_starter_template(org)
        self.refresh_all()

    def load_template_questions(self) -> None:
        org=self.org()
        self.template_questions_table.setRowCount(0)
        if not org or self.template_table.currentRow()<0:
            return
        questions=self.service.template_questions(org,self.selected_id(self.template_table))
        self.fill(self.template_questions_table,questions,["code","domain","prompt"])

    def new_template_question(self) -> None:
        org=self.require_org();tid=self.selected_id(self.template_table)
        dialog=QDialog(self);dialog.setWindowTitle("Add custom question");f=QFormLayout(dialog)
        code=QLineEdit();prompt=QLineEdit();domain=QLineEdit("Govern")
        mapping=QComboBox();mapping.addItem("No suggested mapping",None)
        for framework in self.service.framework_catalogs():
            for ctrl in self.service.framework_controls(framework['key']):
                mapping.addItem(f"{framework['key']} / {ctrl['code']} • {ctrl['title']}",(framework['key'],ctrl['code']))
        f.addRow("Code",code);f.addRow("Question",prompt);f.addRow("Domain",domain);f.addRow("Optional topic mapping",mapping)
        b=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        b.accepted.connect(dialog.accept);b.rejected.connect(dialog.reject);f.addRow(b)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.service.add_template_question(org,tid,code.text(),prompt.text(),domain.text(),mapping.currentData())
            self.refresh_all()

    def show_assessment_mappings(self) -> None:
        org=self.require_org()
        if not self.assessment_id:
            raise ValueError("Select an assessment first")
        mappings=self.service.assessment_mappings(org,self.assessment_id)
        if not mappings:
            self.message("Framework mappings","No mappings for this assessment. Older Phase 1 questionnaires have no official mapping.")
            return
        msg="\n".join(f"{m['question_code']} → {m['framework_key']} / {m['control_code']}" for m in mappings)
        self.message("Suggested, topic-only framework mappings",msg+"\n\nMappings do not prove the control is implemented.")

    def selected_risk(self) -> str:
        self.require_org()
        return self.selected_id(self.risk_table)

    def set_residual(self) -> None:
        org=self.require_org();rid=self.selected_risk()
        dialog=QDialog(self);dialog.setWindowTitle("Residual risk assessment");f=QFormLayout(dialog)
        likelihood=QSpinBox();likelihood.setRange(1,5)
        impact=QSpinBox();impact.setRange(1,5)
        rationale=QLineEdit();rationale.setPlaceholderText("Controls considered and justification")
        f.addRow("Residual likelihood",likelihood);f.addRow("Residual impact",impact);f.addRow("Rationale",rationale)
        b=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        b.accepted.connect(dialog.accept);b.rejected.connect(dialog.reject);f.addRow(b)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            score=self.service.set_residual_risk(org,rid,likelihood.value(),impact.value(),rationale.text())
            self.message("Residual recorded",f"Residual score: {score}. Prior risk acceptance is no longer active until explicitly re-approved.")
            self.refresh_all()

    def record_acceptance(self) -> None:
        org=self.require_org();rid=self.selected_risk()
        dialog=QDialog(self);dialog.setWindowTitle("Risk acceptance decision");f=QFormLayout(dialog)
        decision=QComboBox();decision.addItems(["approved","rejected","revoked"])
        approver=QLineEdit();rationale=QLineEdit();expiry=QLineEdit()
        expiry.setPlaceholderText("YYYY-MM-DD — required for approval")
        verify=QCheckBox("I am recording a documented decision from the named authority (not independent verification)")
        current_password=QLineEdit();current_password.setEchoMode(QLineEdit.EchoMode.Password)
        current_password.setPlaceholderText('Re-enter vault passphrase; does not verify named approver')
        f.addRow("Decision",decision);f.addRow("Named approving authority",approver);f.addRow("Rationale",rationale)
        f.addRow("Expiration",expiry);f.addRow(verify);f.addRow("Vault owner confirmation",current_password)
        b=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        b.accepted.connect(dialog.accept);b.rejected.connect(dialog.reject);f.addRow(b)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.service.record_risk_decision(org,rid,decision.currentText(),approver.text(),rationale.text(),expiry.text(),attested=verify.isChecked(),operator_passphrase=current_password.text())
            self.refresh_all()

    def add_evidence_file(self) -> None:
        org=self.require_org()
        path,_=QFileDialog.getOpenFileName(self,"Choose evidence file")
        if not path:
            return
        size=Path(path).stat().st_size
        if size>5*1024*1024:
            raise ValueError("Evidence upload limit is 5 MiB")
        title,ok=QInputDialog.getText(self,"Evidence title","Evidence title",text=Path(path).name)
        if ok:
            self.service.add_evidence(org,title,Path(path).name,Path(path).read_bytes())
            self.refresh_all()

    def save_evidence_file(self) -> None:
        org=self.require_org()
        eid=self.selected_id(self.evidence_table)
        row=next(x for x in self.service.evidence(org) if x['id']==eid)
        destination,_=QFileDialog.getSaveFileName(self,"Export evidence (unencrypted)",row['filename'])
        if not destination:return
        if QMessageBox.question(self,"Export unencrypted evidence",
                                "The exported file will NOT be encrypted by the application. Continue?")!=QMessageBox.StandardButton.Yes:
            return
        Path(destination).write_bytes(self.service.evidence_bytes(org,eid))
        self.message("File saved","Exported an unencrypted copy. Protect it according to your organization's data handling policy.")

    def link_selected_evidence(self) -> None:
        org=self.require_org();eid=self.selected_id(self.evidence_table)
        targets=[("risk",r['id'],r['title']) for r in self.service.list_risks(org)]
        targets += [("assessment",r['id'],r['title']) for r in self.service.list_assessments(org)]
        if not targets:
            raise ValueError("Create an assessment or risk before linking evidence")
        options=[f"{a.upper()}: {c} [{b[:8]}]" for a,b,c in targets]
        selection,ok=QInputDialog.getItem(self,"Attach evidence","Target record",options,0,False)
        if ok:
            typ,ident,_=targets[options.index(selection)]
            self.service.link_evidence(org,eid,typ,ident)
            self.message("Evidence linked","Evidence link saved to encrypted vault")

    def review_selected_evidence(self) -> None:
        org=self.require_org();eid=self.selected_id(self.evidence_table)
        status,ok=QInputDialog.getItem(self,"Review evidence","Review status",["pending","verified","rejected"],0,False)
        if not ok:return
        reviewer,ok=QInputDialog.getText(self,"Reviewer","Reviewer name")
        if not ok:return
        note,ok=QInputDialog.getText(self,"Review rationale","Review note")
        if not ok:return
        self.service.review_evidence(org,eid,status,reviewer,note)
        self.refresh_all()

    def import_notion(self) -> None:
        org=self.require_org()
        filename,_=QFileDialog.getOpenFileName(self,"Select exported Notion Risk Register CSV","","CSV files (*.csv)")
        if not filename:return
        if Path(filename).stat().st_size>4*1024*1024:
            raise ValueError("CSV must be under 4 MiB")
        data=Path(filename).read_bytes()
        kind=self.import_kind.currentData()
        preview=(self.service.preview_notion_csv(org,data) if kind=="risk_register"
                 else self.service.preview_notion_module(org,data,kind))
        examples="\n".join(f"Line {r['source_row']}: {r['status']} | {r['title']} | {r['message']}" for r in preview['preview'][:25])
        self.import_log.setPlainText(f"Ready: {preview['ready']} | Skipped: {preview['skipped']} | Already imported: {preview['previously_imported']}\n"+examples)
        if preview['skipped'] or preview['previously_imported'] or not preview['ready']:
            self.message("Review issues","Import stopped. Review the preview and resolve invalid records before trying again.",error=True)
            return
        question=f"Import {preview['ready']} {kind.replace('_',' ')} records into {self.service.organization(org)['name']}?\nNo source approval/evidence claims will be automatically trusted."
        if QMessageBox.question(self,"Confirm import",question)==QMessageBox.StandardButton.Yes:
            result=(self.service.import_notion_csv(org,data,Path(filename).name,confirmed=True) if kind=="risk_register"
                    else self.service.import_notion_module(org,data,kind,Path(filename).name,confirmed=True))
            self.refresh_all()
            self.message("Import successful",f"Imported {result['imported']} source records. Original CSV was not changed.")

    def build_controls(self) -> None:
        box=QWidget(); v=QVBoxLayout(box)
        v.addWidget(QLabel('Control testing is operator-reported. A passing result is NOT certification or third-party verification.'))
        action=QPushButton('Record control evaluation')
        action.clicked.connect(lambda: self.protect(self.add_control_review));v.addWidget(action)
        self.control_table=table(['Framework','Control','Title','Implementation','Test result','Verified evidence supports pass','Evaluator'])
        v.addWidget(self.control_table);self.tabs.addTab(box,'Controls')

    def build_vendors(self) -> None:
        box=QWidget();v=QVBoxLayout(box)
        actions=QHBoxLayout()
        for title,handler in [('Create vendor',self.add_vendor),('Record vendor review',self.add_vendor_review)]:
            b=QPushButton(title);b.clicked.connect(lambda _x=False,h=handler:self.protect(h));actions.addWidget(b)
        v.addLayout(actions)
        self.vendor_table=table(['Vendor','Criticality','Data access','BAA applicability','Review state','Risk score','Next review'])
        v.addWidget(self.vendor_table);self.tabs.addTab(box,'Vendors')

    def build_vulnerabilities(self) -> None:
        box=QWidget();v=QVBoxLayout(box)
        actions=QHBoxLayout()
        for title,handler in [('Add finding',self.add_vulnerability),('Change status',self.change_vulnerability_status)]:
            b=QPushButton(title);b.clicked.connect(lambda _x=False,h=handler:self.protect(h));actions.addWidget(b)
        v.addLayout(actions)
        self.vulnerability_table=table(['Title','Severity','CVSS','Status','Source','Asset','Due','Overdue'])
        v.addWidget(self.vulnerability_table);self.tabs.addTab(box,'Vulnerabilities')

    def build_operations_inventory(self) -> None:
        box=QWidget();v=QVBoxLayout(box)
        v.addWidget(QLabel('Imported control, policy and incident inventories; source assertions remain unverified.'))
        self.inventory_summary=QLabel('Select an organization')
        v.addWidget(self.inventory_summary)
        self.inventory_table=table(['Record','Type','Source status / notes'])
        v.addWidget(self.inventory_table);self.tabs.addTab(box,'Imported Inventory')

    def refresh_phase3(self) -> None:
        org=self.org()
        widgets=(self.control_table,self.vendor_table,self.vulnerability_table,self.inventory_table)
        for widget in widgets:widget.setRowCount(0)
        if not org:
            self.inventory_summary.setText('Select an organization')
            return
        self.fill(self.control_table,self.service.control_evaluations(org),
                  ['framework_key','control_code','control_title','implementation','test_result','verified_pass','evaluator'])
        self.fill(self.vendor_table,self.service.vendors(org),
                  ['name','criticality','data_access','baa_applicability','review_state','risk_score','next_review'])
        self.fill(self.vulnerability_table,self.service.vulnerabilities(org),
                  ['title','severity','cvss','status','source','asset_name','due_on','overdue'])
        controls=self.service.imported_control_inventory(org)
        policies=self.service.policies(org)
        incidents=self.service.incidents(org)
        merged=([{'id':r['id'],'title':r['title'],'type':'Control','note':r['source_implementation']} for r in controls]
                +[{'id':r['id'],'title':r['title'],'type':'Policy','note':r['status']} for r in policies]
                +[{'id':r['id'],'title':r['title'],'type':'Incident','note':r['source_status']} for r in incidents])
        self.fill(self.inventory_table,merged,['title','type','note'])
        self.inventory_summary.setText(f'{len(controls)} imported controls • {len(policies)} policies • {len(incidents)} incident records')

    def _ask_text(self,caption: str,label: str) -> str | None:
        value,ok=QInputDialog.getText(self,caption,label)
        return value if ok else None

    def _ask_choice(self,caption: str,label: str,choices: list[str]) -> str | None:
        value,ok=QInputDialog.getItem(self,caption,label,choices,0,False)
        return value if ok else None

    def _selected(self,widget: QTableWidget) -> str:
        return self.selected_id(widget)

    def add_control_review(self) -> None:
        org=self.require_org()
        framework=self._ask_choice('Framework','Reference set:',list(['NIST-CSF-2.0','CIS-CONTROLS-8.1']))
        if framework is None:return
        available=self.service.framework_controls(framework)
        code=self._ask_choice('Control','Select control identifier:',[r['code'] for r in available])
        if code is None:return
        implementation=self._ask_choice('Implementation','Implementation status:',
            ['not_assessed','planned','partial','implemented','not_applicable'])
        if implementation is None:return
        results=['not_applicable'] if implementation=='not_applicable' else ['not_tested','pass','partial','fail']
        test=self._ask_choice('Testing','Test result:',results)
        if test is None:return
        reviewer=self._ask_text('Evaluator','Evaluator name (operator-attested):')
        if reviewer is None:return
        rationale=self._ask_text('Rationale','Testing description and basis:')
        if rationale is None:return
        evidence=[x for x in self.service.evidence(org)]
        options=['None']+[f"{r['title']} ({r['id']})" for r in evidence]
        selected=self._ask_choice('Evidence','Linked evidence artifact:',options)
        if selected is None:return
        eid=None if selected=='None' else selected.rsplit('(',1)[-1].rstrip(')')
        self.service.evaluate_control(org,framework,code,implementation,test,reviewer,rationale,eid)
        self.refresh_all()

    def add_vendor(self) -> None:
        org=self.require_org()
        name=self._ask_text('New vendor','Vendor name:')
        if name is None:return
        category=self._ask_text('Service','Service category:')
        if category is None:return
        criticality=self._ask_choice('Criticality','Classification:', ['low','moderate','high','critical'])
        if criticality is None:return
        access=self._ask_choice('Data access','Data access:', ['unknown','none','internal','confidential','regulated'])
        if access is None:return
        baa=self._ask_choice('BAA applicability','BAA required?', ['unknown','yes','no','not_applicable'])
        if baa is None:return
        self.service.create_vendor(org,name,category,criticality,access,baa)
        self.refresh_all()

    def add_vendor_review(self) -> None:
        org=self.require_org();vid=self._selected(self.vendor_table)
        reviewer=self._ask_text('Vendor review','Reviewer:')
        if reviewer is None:return
        findings=self._ask_text('Findings','Assessment findings and limitations:')
        if findings is None:return
        likelihood,ok=QInputDialog.getInt(self,'Vendor risk','Likelihood (1–5)',3,1,5)
        if not ok:return
        impact,ok=QInputDialog.getInt(self,'Vendor risk','Impact (1–5)',3,1,5)
        if not ok:return
        due=self._ask_text('Next review','Next review date YYYY-MM-DD:')
        if due is None:return
        decision=self._ask_choice('Review result','Review disposition:', ['pending','needs_remediation','reviewed'])
        if decision is None:return
        self.service.record_vendor_review(org,vid,reviewer,findings,likelihood,impact,due,decision)
        self.refresh_all()

    def add_vulnerability(self) -> None:
        org=self.require_org()
        title=self._ask_text('Finding','Vulnerability title:')
        if title is None:return
        source=self._ask_text('Source','Source (manual, scan tool, etc.):')
        if source is None:return
        external=self._ask_text('Tracking','External ID/CVE (optional):')
        if external is None:return
        sev=self._ask_choice('Severity','Severity:', ['unknown','low','medium','high','critical'])
        if sev is None:return
        asset=self._ask_text('Asset','Affected asset name (optional):')
        if asset is None:return
        due=self._ask_text('Due date','Due date YYYY-MM-DD (optional):')
        if due is None:return
        self.service.add_vulnerability(org,title,source,external,sev,asset_name=asset,due_on=due)
        self.refresh_all()

    def change_vulnerability_status(self) -> None:
        org=self.require_org();vid=self._selected(self.vulnerability_table)
        status=self._ask_choice('Vulnerability status','New state:',
            ['open','in_progress','mitigated','accepted','false_positive'])
        if status is None:return
        actor=self._ask_text('Reviewer','Person recording status:')
        if actor is None:return
        reason=self._ask_text('Rationale','Why is the status changing?')
        if reason is None:return
        self.service.update_vulnerability(org,vid,status,actor,reason)
        self.refresh_all()

    def expire_evidence(self) -> None:
        org=self.require_org();eid=self._selected(self.evidence_table)
        expiry=self._ask_text('Evidence expiration','Expires on YYYY-MM-DD (blank clears):')
        if expiry is None:return
        self.service.set_evidence_expiration(org,eid,expiry)
        self.refresh_all()

    def build_settings(self) -> None:
        box = QWidget()
        v = QVBoxLayout(box)
        v.addWidget(QLabel("Vault and recovery"))
        v.addWidget(QLabel("Keep the passphrase somewhere safe. There is no password reset service."))
        back = QPushButton("Create encrypted backup (.csvault)")
        back.clicked.connect(lambda: self.protect(self.backup))
        v.addWidget(back)
        v.addWidget(QLabel("A backup is a copy of the encrypted vault, not a plaintext export."))
        v.addWidget(QLabel("Sensitive data still requires endpoint protection and secure handling of exported reports."))
        v.addStretch()
        self.tabs.addTab(box, "Settings")

    def load_organizations(self) -> None:
        selected = self.org()
        self.org_selector.blockSignals(True)
        self.org_selector.clear()
        for rec in self.service.list_organizations():
            self.org_selector.addItem(rec["name"], rec["id"])
        idx = self.org_selector.findData(selected)
        if idx >= 0:
            self.org_selector.setCurrentIndex(idx)
        self.org_selector.blockSignals(False)
        self.refresh_all()

    def build_vciso(self) -> None:
        pane=QWidget()
        layout=QVBoxLayout(pane)
        layout.addWidget(QLabel("vCISO & Framework Governance • organization-scoped manual tracking"))
        self.vciso_summary=QLabel("Select an organization")
        layout.addWidget(self.vciso_summary)
        self.vciso_framework_picker=QComboBox()
        layout.addWidget(self.vciso_framework_picker)
        actions=QHBoxLayout()
        for label,handler in (
            ("Toggle selected framework",self.toggle_vciso_framework),
            ("Record implementation",self.record_vciso_implementation),
            ("Add initiative",self.add_vciso_initiative),
            ("Save board snapshot",self.save_vciso_board_snapshot)):
            button=QPushButton(label)
            button.clicked.connect(lambda _=False,fn=handler: self.protect(fn))
            actions.addWidget(button)
        layout.addLayout(actions)
        self.vciso_framework_table=table(["Framework","Type","Enabled","Edition","Owner","Target"])
        layout.addWidget(self.vciso_framework_table)
        self.vciso_items_table=table(["Framework","Reference","Title","Status","Owner","Due","Evidence"])
        layout.addWidget(self.vciso_items_table)
        self.vciso_board_table=table(["Period","Prepared by","Created","Summary"])
        layout.addWidget(self.vciso_board_table)
        self.tabs.addTab(pane,"vCISO & Frameworks")

    def refresh_vciso(self) -> None:
        org=self.org()
        self.vciso_framework_picker.clear()
        for widget in (self.vciso_framework_table,self.vciso_items_table,self.vciso_board_table):
            widget.setRowCount(0)
        if not org:
            self.vciso_summary.setText("Select an organization")
            return
        frameworks=self.service.frameworks(org)
        for fw in frameworks:
            self.vciso_framework_picker.addItem(fw["name"],fw["key"])
        self.fill(self.vciso_framework_table,
                  [{**f,"id":f["key"],"enabled":"Yes" if f["enabled"] else "No"} for f in frameworks],
                  ["name","kind","enabled","edition","owner","target_date"])
        self.fill(self.vciso_items_table,self.service.implementations(org),
                  ["framework_key","reference","title","status","owner","due_date","evidence_reference"])
        self.fill(self.vciso_board_table,self.service.board_reports(org),
                  ["period_label","prepared_by","created_at","executive_summary"])
        stats=self.service.board_snapshot(org)
        self.vciso_summary.setText(
            f'{stats["frameworks_enabled"]} active frameworks • {stats["assessed_items"]} tracked items • '
            f'{stats["implementation_counts"]["verified"]} reviewer-verified • '
            f'{stats["overdue_items"]} overdue • {stats["initiatives_total"]} initiatives')

    def toggle_vciso_framework(self) -> None:
        org=self.require_org()
        key=self.vciso_framework_picker.currentData()
        if not key: raise ValueError("Select a framework")
        current=next(f for f in self.service.frameworks(org) if f["key"]==key)
        edition,ok=QInputDialog.getText(self,"Framework edition","Edition / baseline:",text=current["edition"] or current["default_edition"])
        if not ok:return
        self.service.configure_framework(org,key,not current["enabled"],edition=edition,
                                        scope=current["scope"],owner=current["owner"],target_date=current["target_date"])
        self.refresh_vciso()

    def record_vciso_implementation(self) -> None:
        org=self.require_org()
        key=self.vciso_framework_picker.currentData()
        if not key: raise ValueError("Select a framework")
        ref,ok=QInputDialog.getText(self,"Control / requirement reference","Identifier:")
        if not ok:return
        title,ok=QInputDialog.getText(self,"Implementation","Title:")
        if not ok:return
        options=["not_started","planned","in_progress","implemented","verified","gap","not_applicable"]
        status,ok=QInputDialog.getItem(self,"Implementation state","Status:",options,0,False)
        if not ok:return
        evidence=""
        reviewer=""
        if status=="verified":
            evidence,ok=QInputDialog.getText(self,"Evidence","Evidence reference (manual):")
            if not ok:return
            reviewer,ok=QInputDialog.getText(self,"Reviewer","Reviewer name (unverified assertion):")
            if not ok:return
        self.service.upsert_implementation(org,key,ref,title,status,
                                            evidence_reference=evidence,verified_by=reviewer)
        self.refresh_vciso()

    def add_vciso_initiative(self) -> None:
        org=self.require_org()
        title,ok=QInputDialog.getText(self,"New vCISO initiative","Initiative:")
        if not ok:return
        owner,ok=QInputDialog.getText(self,"Owner","Owner:")
        if not ok:return
        due,ok=QInputDialog.getText(self,"Target date","YYYY-MM-DD (optional):")
        if not ok:return
        self.service.upsert_initiative(org,title,owner=owner,due_date=due)
        self.refresh_vciso()

    def save_vciso_board_snapshot(self) -> None:
        org=self.require_org()
        period,ok=QInputDialog.getText(self,"Board reporting","Reporting period:")
        if not ok:return
        preparer,ok=QInputDialog.getText(self,"Board reporting","Prepared by:")
        if not ok:return
        summary,ok=QInputDialog.getMultiLineText(self,"Board reporting","Executive summary:")
        if not ok:return
        self.service.publish_board_snapshot(org,period,preparer,summary)
        self.refresh_vciso()
        self.message("Board snapshot saved","Dated management snapshot saved in encrypted vault. This is not a board approval.")

    def build_governance(self) -> None:
        pane=QWidget();v=QVBoxLayout(pane)
        v.addWidget(QLabel("Change Control | CAB approval, maintenance windows, checks and rollback"))
        self.change_summary=QLabel("Select an organization")
        v.addWidget(self.change_summary)
        actions=QHBoxLayout()
        for caption,method in (
            ("+ Request",self.new_governance_change),
            ("Edit plan / window",self.plan_governance_change),
            ("Advance status",self.advance_governance_change),
            ("CAB decision",self.cab_governance_change),
            ("Validation check",self.check_governance_change)):
            button=QPushButton(caption)
            button.clicked.connect(lambda _=False,fn=method:self.protect(fn))
            actions.addWidget(button)
        v.addLayout(actions)
        self.change_register=table(["Change","Type","Risk","Owner","Start","End","Status"])
        v.addWidget(self.change_register)
        self.tabs.addTab(pane,"Change Control")

        pane=QWidget();v=QVBoxLayout(pane)
        v.addWidget(QLabel("Audit & Assurance | Internal, external, regulatory and supplier reviews"))
        self.audit_summary=QLabel("Select an organization")
        v.addWidget(self.audit_summary)
        actions=QHBoxLayout()
        for caption,method in (
            ("+ New audit",self.new_governance_audit),
            ("Advance audit",self.advance_governance_audit),
            ("+ Finding",self.new_governance_finding),
            ("Update finding",self.advance_governance_finding)):
            button=QPushButton(caption)
            button.clicked.connect(lambda _=False,fn=method:self.protect(fn))
            actions.addWidget(button)
        v.addLayout(actions)
        self.audit_register=table(["Audit","Type","Framework","Lead","Start","End","Status"])
        self.finding_register=table(["Finding","Severity","Owner","Due","Status"])
        v.addWidget(self.audit_register);v.addWidget(self.finding_register)
        self.tabs.addTab(pane,"Audit & Assurance")

    def _selected_id(self,widget):
        row=widget.currentRow()
        if row<0:raise ValueError("Select a record in the table first")
        return widget.item(row,0).data(Qt.ItemDataRole.UserRole)

    def _prompt(self,title,caption,default=""):
        value,ok=QInputDialog.getText(self,title,caption,text=default)
        return value.strip() if ok else None

    def _option(self,title,caption,values):
        value,ok=QInputDialog.getItem(self,title,caption,values,0,False)
        return value if ok else None

    def refresh_governance(self) -> None:
        for widget in (self.change_register,self.audit_register,self.finding_register):
            widget.setRowCount(0)
        org=self.org()
        if not org:
            self.change_summary.setText("Select an organization")
            self.audit_summary.setText("Select an organization")
            return
        self.fill(self.change_register,self.service.changes(org),
                  ["title","change_type","risk_level","owner","start_at","end_at","status"])
        self.fill(self.audit_register,self.service.audits(org),
                  ["title","audit_type","framework","lead","start_date","end_date","status"])
        self.fill(self.finding_register,self.service.findings(org),
                  ["title","severity","owner","due_date","status"])
        m=self.service.governance_metrics(org)
        self.change_summary.setText(
            f'{m["changes_total"]} changes | {m["changes_pending_cab"]} waiting CAB | '
            f'{m["changes_scheduled"]} approved/scheduled/in progress | {m["changes_rolled_back"]} rolled back')
        self.audit_summary.setText(
            f'{m["audits_open"]} active audits | {m["findings_open"]} open findings | '
            f'{m["findings_high_critical"]} high/critical | {m["findings_overdue"]} overdue')

    def new_governance_change(self):
        org=self.require_org()
        title=self._prompt("Change request","Change title:")
        if title is None:return
        kind=self._option("Change type","Select classification:",["normal","standard","emergency"])
        if kind is None:return
        requester=self._prompt("Requester","Requester name:")
        if requester is None:return
        owner=self._prompt("Owner","Implementation owner:")
        if owner is None:return
        risk=self._option("Impact level","Risk classification:",["low","medium","high","critical"])
        if risk is None:return
        self.service.create_change(org,title,kind,requester,owner,risk)
        self.refresh_governance()

    def plan_governance_change(self):
        org=self.require_org();ident=self._selected_id(self.change_register)
        record=self.service._change(org,ident)
        plan,ok=QInputDialog.getMultiLineText(self,"Implementation plan","Detailed implementation steps:",record["implementation_plan"])
        if not ok:return
        rollback,ok=QInputDialog.getMultiLineText(self,"Rollback plan","Restoration actions:",record["rollback_plan"])
        if not ok:return
        impact=self._prompt("Impact","Services and business impact:",record["impact"])
        if impact is None:return
        start=self._prompt("Maintenance window","Start (YYYY-MM-DD or YYYY-MM-DDTHH:MM):",record["start_at"])
        if start is None:return
        end=self._prompt("Maintenance window","End (YYYY-MM-DD or YYYY-MM-DDTHH:MM):",record["end_at"])
        if end is None:return
        self.service.set_change_plan(org,ident,plan,rollback,impact,start,end)
        self.refresh_governance()

    def advance_governance_change(self):
        org=self.require_org();ident=self._selected_id(self.change_register)
        record=self.service._change(org,ident)
        options={"draft":["submitted","cancelled"],"submitted":["review","cancelled"],
                 "review":["cancelled"],"approved":["scheduled","cancelled"],
                 "scheduled":["implementing","cancelled"],"implementing":["validation","rolled_back"],
                 "validation":["completed","rolled_back"]}.get(record["status"],[])
        if not options:raise ValueError("No manual transitions available for this state; CAB decisions use their own action")
        status=self._option("Change lifecycle","New status:",options)
        if status is None:return
        actor=self._prompt("Action owner","Your name:")
        if actor is None:return
        note=self._prompt("Change note","Reason / result:")
        if note is None:return
        self.service.transition_change(org,ident,status,actor,note)
        self.refresh_governance()

    def cab_governance_change(self):
        org=self.require_org();ident=self._selected_id(self.change_register)
        reviewer=self._prompt("CAB decision","Reviewer name:")
        if reviewer is None:return
        decision=self._option("CAB decision","Decision:",["approved","rejected","changes_requested"])
        if decision is None:return
        note=self._prompt("CAB decision","Decision rationale:")
        if note is None:return
        self.service.review_change(org,ident,reviewer,decision,note)
        self.refresh_governance()

    def check_governance_change(self):
        org=self.require_org();ident=self._selected_id(self.change_register)
        phase=self._option("Validation","Phase:",["pre","post","rollback"])
        if phase is None:return
        check=self._prompt("Validation","Check performed:")
        if check is None:return
        result=self._option("Validation","Result:",["pending","pass","fail","not_applicable"])
        if result is None:return
        tester=self._prompt("Validation","Tester name:")
        if tester is None:return
        evidence=self._prompt("Validation","Evidence reference (optional):")
        if evidence is None:return
        self.service.add_change_check(org,ident,phase,check,result,tester,evidence)
        self.refresh_governance()

    def new_governance_audit(self):
        org=self.require_org()
        title=self._prompt("Audit engagement","Title:")
        if title is None:return
        kind=self._option("Audit type","Type:",["internal","external","regulatory","supplier"])
        if kind is None:return
        lead=self._prompt("Audit lead","Lead auditor:")
        if lead is None:return
        fw=self._prompt("Assessment scope","Framework / regulation:")
        if fw is None:return
        scope=self._prompt("Assessment scope","Scope / business units:")
        if scope is None:return
        self.service.create_audit(org,title,kind,lead,framework=fw,scope=scope)
        self.refresh_governance()

    def advance_governance_audit(self):
        org=self.require_org();ident=self._selected_id(self.audit_register)
        record=self.service._audit_record(org,ident)
        options={"planned":["fieldwork","cancelled"],"fieldwork":["review","cancelled"],
                 "review":["closed","fieldwork"]}.get(record["status"],[])
        if not options:raise ValueError("Audit already closed or cancelled")
        status=self._option("Audit status","Next stage:",options)
        if status is None:return
        actor=self._prompt("Audit record","Recorded by:")
        if actor is None:return
        conclusion=""
        if status=="closed":
            conclusion=self._prompt("Closing audit","Management conclusion:")
            if conclusion is None:return
        self.service.update_audit_status(org,ident,status,actor,conclusion)
        self.refresh_governance()

    def new_governance_finding(self):
        org=self.require_org();audit=self._selected_id(self.audit_register)
        title=self._prompt("Audit finding","Finding title:")
        if title is None:return
        severity=self._option("Severity","Severity:",["low","medium","high","critical"])
        if severity is None:return
        description=self._prompt("Audit finding","Observation:")
        if description is None:return
        owner=self._prompt("Remediation owner","Owner:")
        if owner is None:return
        due=self._prompt("Remediation deadline","Due (YYYY-MM-DD, optional):")
        if due is None:return
        self.service.add_finding(org,audit,title,severity,description,owner,due)
        self.refresh_governance()

    def advance_governance_finding(self):
        org=self.require_org();ident=self._selected_id(self.finding_register)
        record=next(x for x in self.service.findings(org) if x["id"]==ident)
        options={"open":["in_progress","accepted"],"in_progress":["ready_for_verification","accepted"],
                 "ready_for_verification":["closed","in_progress"]}.get(record["status"],[])
        if not options:raise ValueError("No transitions available")
        status=self._option("Finding workflow","New status:",options)
        if status is None:return
        actor=self._prompt("Finding","Updated by:")
        if actor is None:return
        action=self._prompt("Remediation","Corrective action:",record["corrective_action"])
        if action is None:return
        response=self._prompt("Management","Management response:",record["management_response"])
        if response is None:return
        evidence="";reviewer=""
        if status=="closed":
            evidence=self._prompt("Verification","Evidence reference:")
            if evidence is None:return
            reviewer=self._prompt("Verification","Reviewer:")
            if reviewer is None:return
        self.service.update_finding(org,ident,status,actor,action,response,evidence,reviewer)
        self.refresh_governance()

    def build_enterprise_governance(self):
        from PySide6.QtWidgets import QCalendarWidget
        pane=QWidget();v=QVBoxLayout(pane)
        v.addWidget(QLabel("Governance Command Center • CAB policy, change calendar & board reporting"))
        actions=QHBoxLayout()
        for text,fn in (("CAB quorum policy",self.edit_cab_policy),
                        ("Board PDF",lambda:self.export_governance_board("pdf")),
                        ("Board Excel",lambda:self.export_governance_board("xlsx"))):
            b=QPushButton(text);b.clicked.connect(lambda _=False,callback=fn:self.protect(callback));actions.addWidget(b)
        v.addLayout(actions)
        self.governance_calendar=QCalendarWidget()
        self.governance_calendar.setGridVisible(True)
        self.governance_calendar.currentPageChanged.connect(lambda *_:self.protect(self.refresh_enterprise_governance))
        v.addWidget(self.governance_calendar)
        self.calendar_changes=table(["Change","Window start","Window end","Owner","Status"])
        v.addWidget(self.calendar_changes)
        self.tabs.addTab(pane,"Governance Center")

        pane=QWidget();v=QVBoxLayout(pane)
        v.addWidget(QLabel("Evidence Custody • encrypted attachments, SHA-256 integrity, review and lifecycle"))
        actions=QHBoxLayout()
        for text,fn in (("+ Import evidence",self.import_governance_evidence),
                        ("Verify / reject",self.review_governance_evidence),
                        ("Link to record",self.link_governance_evidence)):
            b=QPushButton(text);b.clicked.connect(lambda _=False,callback=fn:self.protect(callback));actions.addWidget(b)
        v.addLayout(actions)
        self.custody_register=table(["Title","Class","SHA-256","Size (bytes)","Review","Expires"])
        v.addWidget(self.custody_register)
        self.tabs.addTab(pane,"Evidence Custody")

    def refresh_enterprise_governance(self):
        self.calendar_changes.setRowCount(0);self.custody_register.setRowCount(0)
        org=self.org()
        if not org:return
        year=self.governance_calendar.yearShown();month=self.governance_calendar.monthShown()
        records=self.service.calendar_month(org,year,month)
        self.fill(self.calendar_changes,[{"id":r["id"],"title":r["title"],"start":r["start"],
                 "end":r["end"],"owner":r["owner"],"status":r["status"]} for r in records],
                  ["title","start","end","owner","status"])
        self.fill(self.custody_register,self.service.evidence_inventory(org),
                  ["title","classification","sha256","size_bytes","review_state","expires_on"])

    def edit_cab_policy(self):
        org=self.require_org();p=self.service.approval_policy(org)
        normal,ok=QInputDialog.getInt(self,"CAB policy","Normal-change approval quorum:",p["normal_quorum"],1,10)
        if not ok:return
        emergency,ok=QInputDialog.getInt(self,"CAB policy","Emergency approval quorum:",p["emergency_quorum"],1,10)
        if not ok:return
        self.service.set_approval_policy(org,normal,emergency,bool(p["require_separation"]))
        self.message("Policy saved","CAB quorum policy saved. Reviewer names remain operator-entered assertions.")

    def export_governance_board(self,kind):
        org=self.require_org()
        suffix="."+kind
        file,_=QFileDialog.getSaveFileName(self,"Save governance board packet",
                       "governance-board-packet"+suffix,
                       "PDF (*.pdf)" if kind=="pdf" else "Excel (*.xlsx)")
        if not file:return
        if Path(file).suffix.lower()!=suffix:file+=suffix
        board_packet(self.service,org,Path(file))
        self.message("Export complete",f"Saved: {file}\nPlaintext report: protect it as sensitive information.")

    def import_governance_evidence(self):
        org=self.require_org()
        file,_=QFileDialog.getOpenFileName(self,"Select evidence file")
        if not file:return
        data=Path(file).read_bytes()
        collector=self._prompt("Evidence custody","Collector name:")
        if collector is None:return
        classification=self._option("Evidence classification","Data classification:",
                                    ["internal","confidential","restricted","public"])
        if classification is None:return
        self.service.add_custody_evidence(org,Path(file).name,Path(file).name,data,
                                         collector,classification)
        self.refresh_enterprise_governance()

    def review_governance_evidence(self):
        org=self.require_org();ident=self._selected_id(self.custody_register)
        reviewer=self._prompt("Evidence verification","Reviewer name:")
        if reviewer is None:return
        decision=self._option("Evidence verification","Review outcome:",["verified","rejected"])
        if decision is None:return
        notes=self._prompt("Evidence verification","Review rationale:")
        if notes is None:return
        self.service.review_custody_evidence(org,ident,reviewer,decision,notes)
        self.refresh_enterprise_governance()

    def link_governance_evidence(self):
        org=self.require_org();ident=self._selected_id(self.custody_register)
        typ=self._option("Evidence relationship","Link to:",["change","audit","finding"])
        if typ is None:return
        collections={"change":self.service.changes(org),"audit":self.service.audits(org),
                     "finding":self.service.findings(org)}
        records=collections[typ]
        if not records:raise ValueError("Create a record before linking evidence")
        labels=[str(r["title"])+" ["+r["id"][:8]+"]" for r in records]
        label=self._option("Evidence relationship","Target record:",labels)
        if label is None:return
        target=records[labels.index(label)]["id"]
        self.service.link_custody_evidence(org,ident,typ,target)
        self.message("Evidence linked","Relationship saved to encrypted vault.")

    def organization_changed(self, _idx: int) -> None:
        self.assessment_id = None
        self.refresh_all()

    def refresh_all(self) -> None:
        self.protect(self._refresh)

    def _refresh(self) -> None:
        org = self.org()
        for t in (self.assessment_table, self.questions_table, self.risk_table, self.task_table,
                  self.template_table, self.evidence_table, self.catalog_table):
            t.setRowCount(0)
        if not org:
            self.dash_label.setText("Create an organization to begin")
            return
        self.refresh_vciso()
        self.refresh_governance()
        self.refresh_enterprise_governance()
        counts = self.service.overview(org)
        metrics=self.service.executive_metrics(org)
        self.dash_label.setText(f"{counts['assessments']} assessments • {counts['risks_open']} active risks • {counts['tasks_open']} open actions\n"
            f"{metrics['vulnerabilities_high_open']} high/critical vulnerabilities • {metrics['vendor_reviews_overdue']} vendor review gaps • "
            f"{metrics['evidence_expired']} expired evidence")
        self.fill(self.assessment_table, self.service.list_assessments(org), ["title", "status", "framework_label", "scope", "created_at"])
        self.fill(self.risk_table, self.service.list_risks(org), ["title", "likelihood", "impact", "score", "band", "residual_score", "acceptance_state", "status", "rationale"])
        self.fill(self.task_table, self.service.list_tasks(org), ["title", "owner", "due_date", "priority", "status", "risk_id"])
        self.load_questions()
        self.refresh_phase2()
        self.refresh_phase3()

    @staticmethod
    def fill(widget: QTableWidget, records: list[dict], fields: list[str]) -> None:
        widget.setRowCount(len(records))
        for i, rec in enumerate(records):
            for j, field in enumerate(fields):
                widget.setItem(i, j, item(rec.get(field), rec["id"] if j == 0 else None))

    def add_organization(self) -> None:
        name, ok = QInputDialog.getText(self, "Create organization", "Organization name:")
        if not ok or not name.strip():
            return
        industry, ok = QInputDialog.getText(self, "Industry", "Industry (optional):")
        if not ok:
            return
        ident = self.service.create_organization(name, industry)
        self.load_organizations()
        self.org_selector.setCurrentIndex(self.org_selector.findData(ident))

    def add_assessment(self) -> None:
        org = self.require_org()
        template_id = self.new_assessment_template.currentData()
        aid = self.service.create_assessment(org, self.new_assessment_name.text(), self.new_scope.text(),template_id)
        self.new_assessment_name.clear()
        self.new_scope.clear()
        self.assessment_id = aid
        self.refresh_all()
        self.tabs.setCurrentIndex(2)

    def require_org(self) -> str:
        org = self.org()
        if not org:
            raise ValueError("Create or select an organization first")
        return org

    def select_assessment(self) -> None:
        row = self.assessment_table.currentRow()
        if row < 0:
            raise ValueError("Select an assessment first")
        cell = self.assessment_table.item(row, 0)
        self.assessment_id = cell.data(Qt.ItemDataRole.UserRole)
        self.load_questions()
        self.tabs.setCurrentIndex(2)

    def load_questions(self) -> None:
        org = self.org()
        self.questions_table.setRowCount(0)
        if not org or not self.assessment_id:
            self.question_title.setText("Select an assessment on the Assessments tab.")
            return
        questions = self.service.questions(org, self.assessment_id)
        self.question_title.setText(f"Assessment questionnaire • {len(questions)} questions • manual answers")
        self.questions_table.setRowCount(len(questions))
        self.questions_table.setWordWrap(True)
        for row, question in enumerate(questions):
            self.questions_table.setItem(row, 0, item(f"{question['code']} ({question['domain']})", question["code"]))
            self.questions_table.setItem(row, 1, item(question["prompt"]))
            answer = QComboBox()
            answer.addItems(["Unanswered", "Yes", "Partial", "No", "N/A", "Unknown"])
            answer.setCurrentText(question["answer"])
            self.questions_table.setCellWidget(row, 2, answer)
            rationale = QLineEdit(question["rationale"])
            rationale.setPlaceholderText("Explain rationale and evidence")
            self.questions_table.setCellWidget(row, 3, rationale)
            self.questions_table.setRowHeight(row, 60)

    def save_answers(self) -> None:
        org = self.require_org()
        if not self.assessment_id:
            raise ValueError("Open an assessment first")
        for row in range(self.questions_table.rowCount()):
            code = self.questions_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            answer = self.questions_table.cellWidget(row, 2).currentText()
            rationale = self.questions_table.cellWidget(row, 3).text()
            self.service.answer_question(org, self.assessment_id, code, answer, rationale)
        self.refresh_all()
        self.statusBar().showMessage("Assessment answers saved to encrypted vault", 6000)

    def add_risk(self) -> None:
        org = self.require_org()
        dialog = QDialog(self)
        dialog.setWindowTitle("New risk")
        form = QFormLayout(dialog)
        name = QLineEdit()
        description = QTextEdit()
        description.setFixedHeight(65)
        likelihood = QSpinBox()
        likelihood.setRange(1, 5)
        impact = QSpinBox()
        impact.setRange(1, 5)
        rationale = QLineEdit()
        form.addRow("Risk title", name)
        form.addRow("Description", description)
        form.addRow("Likelihood (1–5)", likelihood)
        form.addRow("Impact (1–5)", impact)
        form.addRow("Scoring rationale", rationale)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.service.add_risk(org, name.text(), description.toPlainText(),
                              likelihood.value(), impact.value(), rationale.text(), self.assessment_id)
        self.refresh_all()

    def add_task(self) -> None:
        org = self.require_org()
        risks = self.service.list_risks(org)
        if not risks:
            raise ValueError("Create a risk before adding remediation tasks")
        dialog = QDialog(self)
        dialog.setWindowTitle("Add remediation action")
        form = QFormLayout(dialog)
        risk_picker = QComboBox()
        for risk in risks:
            risk_picker.addItem(risk["title"], risk["id"])
        title = QLineEdit()
        owner = QLineEdit()
        due = QLineEdit()
        due.setPlaceholderText("YYYY-MM-DD (optional)")
        form.addRow("Related risk", risk_picker)
        form.addRow("Action", title)
        form.addRow("Owner", owner)
        form.addRow("Due date", due)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.service.add_task(org, risk_picker.currentData(), title.text(), owner.text(), due.text())
        self.refresh_all()

    def change_task_status(self) -> None:
        org = self.require_org()
        row = self.task_table.currentRow()
        if row < 0:
            raise ValueError("Select a remediation action first")
        tid = self.task_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        current = self.task_table.item(row, 4).text()
        values = ["open", "in_progress", "blocked", "done"]
        new_status, ok = QInputDialog.getItem(self, "Update remediation status", "New status:", values, values.index(current), False)
        if ok:
            self.service.update_task_status(org, tid, new_status, "Updated from desktop UI")
            self.refresh_all()

    def export(self, kind: str) -> None:
        org = self.require_org()
        suffix = ".pdf" if kind == "pdf" else ".xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Save executive operations snapshot", "cyberstudio-operations-snapshot" + suffix,
                                              "PDF Documents (*.pdf)" if kind == "pdf" else "Excel Workbook (*.xlsx)")
        if not path:
            return
        if Path(path).suffix.lower() != suffix:
            path += suffix
        output = (export_pdf if kind == "pdf" else export_xlsx)(self.service, org, Path(path))
        self.message("Report exported", f"Saved to {output}\n\nHandle unencrypted reports appropriately.")

    def backup(self) -> None:
        file, _ = QFileDialog.getSaveFileName(self, "Save encrypted vault backup", "cyberstudio-backup.csvault", "Encrypted vault (*.csvault)")
        if file:
            if not file.endswith(".csvault"):
                file += ".csvault"
            self.vault.backup(Path(file))
            self.message("Backup complete", f"Encrypted backup saved: {file}\nRetain the original passphrase to restore it.")


def get_vault(parent: QWidget | None = None) -> Vault | None:
    path = Path(user_data_dir("Cyber Security Operations Online Studio", "CyberStudio")) / "studio.csvault"
    is_new = not path.exists()
    if is_new:
        QMessageBox.information(parent, "First-time setup", "Create a passphrase (12+ characters) to protect your encrypted local vault.\n\nThere is no password reset service. Store the passphrase securely.")
    for _ in range(3):
        password, ok = QInputDialog.getText(parent, "Create vault" if is_new else "Unlock vault",
                                            "Passphrase:", QLineEdit.EchoMode.Password)
        if not ok:
            return None
        if is_new:
            verify, accepted = QInputDialog.getText(parent, "Confirm passphrase", "Repeat the passphrase:", QLineEdit.EchoMode.Password)
            if not accepted:
                return None
            if password != verify:
                QMessageBox.warning(parent, "Passphrase mismatch", "Passphrases must match")
                continue
        try:
            return Vault(path, password, create=is_new)
        except (VaultError, ValueError) as exc:
            QMessageBox.warning(parent, "Vault error", str(exc))
    return None


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(THEME)
    vault = get_vault()
    if vault is None:
        return 1
    try:
        window = MainWindow(vault)
    except Exception as exc:
        vault.close()
        QMessageBox.critical(None, "Startup failed", str(exc))
        return 2
    app.aboutToQuit.connect(vault.close)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
