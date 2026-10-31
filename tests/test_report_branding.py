from io import BytesIO
from pathlib import Path
import zipfile
import pytest
from PIL import Image
from openpyxl import load_workbook
from cyberstudio.vault import Vault
from cyberstudio.enterprise import EnterpriseGovernanceService
from cyberstudio.report_branding import normalize_logo
from cyberstudio.service import ValidationError, NotFoundError
from cyberstudio.governance_reports import board_packet
from cyberstudio.reports_phase3 import export_executive_pdf, export_executive_xlsx


def logo(size=(600,180),format='PNG'):
    data=BytesIO();Image.new('RGB',size,'#174665').save(data,format=format);return data.getvalue()


def test_logo_normalization_and_rejection():
    normalized=normalize_logo(logo((2400,400),'JPEG'))
    with Image.open(BytesIO(normalized)) as image:
        assert image.format=='PNG' and image.size==(1200,200)
        assert not image.info
    for content in [b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',b'invalid',b'x'*(2*1024*1024+1),logo((4001,2000))]:
        with pytest.raises(ValidationError):normalize_logo(content)


def test_branding_isolation_persistence_and_exports(tmp_path):
    vault_path=tmp_path/'branding.csvault'
    with Vault(vault_path,'synthetic-branding-passphrase-only',create=True) as vault:
        service=EnterpriseGovernanceService(vault);org=service.create_organization('Synthetic Alpha');other=service.create_organization('Synthetic Bravo')
        service.save_report_branding(org,'=Example identity','Security oversight','#234567','#008080','Internal use only',logo=logo())
        assert service.report_branding(other)['logo']==b''
        with pytest.raises(NotFoundError):service.report_branding('missing')
        with pytest.raises(ValidationError):service.save_report_branding(org,'Example','','invalid','#008080','')
        assert service.report_branding(org)['primary_color']=='234567'
        service.save_report_branding(org,'=Example identity','Security oversight','234567','008080','Internal use only')
        assert service.report_branding(org)['logo']
        for kind in ('board','executive'):
            pdf=tmp_path/(kind+'.pdf');xlsx=tmp_path/(kind+'.xlsx')
            if kind=='board':board_packet(service,org,pdf);board_packet(service,org,xlsx)
            else:export_executive_pdf(service,org,pdf);export_executive_xlsx(service,org,xlsx)
            assert pdf.read_bytes().startswith(b'%PDF')
            wb=load_workbook(xlsx)
            assert wb['Report Identity']['A1'].data_type!='f'
            assert wb['Report Identity']['A1'].value.startswith("'=Example")
            assert all(ws.oddFooter.center.text=='Program Owner - Matthew Harris' for ws in wb)
            with zipfile.ZipFile(xlsx) as archive:assert any(n.startswith('xl/media/') for n in archive.namelist())
    with Vault(vault_path,'synthetic-branding-passphrase-only') as vault:
        service=EnterpriseGovernanceService(vault);assert service.report_branding(org)['logo']
        service.save_report_branding(org,'Example','','234567','008080','',remove_logo=True)
        assert service.report_branding(org)['logo']==b''
