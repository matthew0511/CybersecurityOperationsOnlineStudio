"""Organization-scoped report identity and safe raster logo normalization."""
from io import BytesIO
import re
import json
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError
from .service import ValidationError, utc_now

SCHEMA = """
CREATE TABLE IF NOT EXISTS report_branding (
 organization_id TEXT PRIMARY KEY REFERENCES organizations(id),
 display_name TEXT NOT NULL,tagline TEXT NOT NULL,primary_color TEXT NOT NULL,
 accent_color TEXT NOT NULL,footer_note TEXT NOT NULL,logo BLOB NOT NULL,
 updated_at TEXT NOT NULL);
"""

def normalize_logo(content):
    if not content or len(content)>2*1024*1024:
        raise ValidationError('Choose a PNG or JPEG logo up to 2 MiB')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(content), formats=['PNG','JPEG']) as source:
                if source.width*source.height>8_000_000:
                    raise ValidationError('Logo must contain no more than 8 million pixels')
                source.load()
                image=ImageOps.exif_transpose(source).convert('RGBA')
                image.thumbnail((1200,400),Image.Resampling.LANCZOS)
                # Re-encode pixels only: strip source metadata, scripts and profiles.
                clean=Image.new('RGBA',image.size);clean.paste(image)
                result=BytesIO();clean.save(result,format='PNG',optimize=True)
                return result.getvalue()
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise ValidationError('Upload a valid PNG or JPEG image') from None

def text(value,label,limit):
    if not isinstance(value,str) or len(value.strip())>limit or any(ord(c)<32 for c in value):
        raise ValidationError(f'{label} must be a single line of at most {limit} characters')
    return value.strip()

def defaults(name='Cyber Security Operations Online Studio'):
    return dict(display_name=name,tagline='Security & governance reporting',primary_color='112C3A',accent_color='0C827D',footer_note='Confidential management records',logo=b'',updated_at='')

def for_report(service,org):
    if hasattr(service,'report_branding'):return service.report_branding(org)
    return defaults(service.organization(org)['name'])

class ReportBrandingMixin:
    def report_branding(self,org):
        record=self.organization(org)
        if hasattr(self.vault,'raw'):
            row=self.vault.raw.execute('SELECT settings,logo FROM xp_settings WHERE organization_id=%s',(org,)).fetchone()
            result=defaults(record['name']);cfg=row['settings'] if row else {}
            result.update(display_name=cfg.get('brand_name') or record['name'],
                tagline=cfg.get('report_tagline',result['tagline']),
                primary_color=cfg.get('report_primary_color',result['primary_color']).lstrip('#'),
                accent_color=cfg.get('accent','#'+result['accent_color']).lstrip('#'),
                footer_note=cfg.get('report_footer',result['footer_note']),
                logo=normalize_logo(bytes(row['logo'])) if row and row['logo'] else b'',
                updated_at=cfg.get('report_branding_updated_at',''))
            return result
        row=self.db.execute('SELECT * FROM report_branding WHERE organization_id=?',(org,)).fetchone()
        result=dict(row) if row else defaults(record['name'])
        result['logo']=bytes(result.get('logo') or b'')
        return result

    def save_report_branding(self,org,display_name,tagline,primary_color,accent_color,footer_note,logo=None,remove_logo=False):
        self._org(org)
        name=text(display_name,'Display name',100)
        if not name:raise ValidationError('Enter a report display name')
        tagline=text(tagline,'Tagline',160);footer_note=text(footer_note,'Footer note',120)
        colors=[]
        for value in (primary_color,accent_color):
            if not isinstance(value,str) or not re.fullmatch(r'#?[0-9a-fA-F]{6}',value):
                raise ValidationError('Brand colors must be six-digit hex colors')
            colors.append(value.lstrip('#').upper())
        if logo is not None and remove_logo:raise ValidationError('Choose a new logo or remove the existing logo')
        existing=self.report_branding(org)
        image=normalize_logo(logo) if logo is not None else b'' if remove_logo else existing['logo']
        stamp=utc_now()
        with self.vault.transaction() as conn:
            if hasattr(self.vault,'raw'):
                cfg=dict(brand_name=name,report_tagline=tagline,report_primary_color=colors[0],accent='#'+colors[1],report_footer=footer_note,report_branding_updated_at=stamp)
                self.vault.raw.execute('''INSERT INTO xp_settings(organization_id,settings,logo,logo_mime) VALUES (%s,%s::jsonb,%s,'image/png')
                 ON CONFLICT(organization_id) DO UPDATE SET settings=xp_settings.settings||EXCLUDED.settings,
                 logo=EXCLUDED.logo,logo_mime=EXCLUDED.logo_mime''',(org,json.dumps(cfg),image or None))
            else:
                conn.execute('''INSERT INTO report_branding VALUES(?,?,?,?,?,?,?,?)
                 ON CONFLICT(organization_id) DO UPDATE SET display_name=excluded.display_name,
                 tagline=excluded.tagline,primary_color=excluded.primary_color,accent_color=excluded.accent_color,
                 footer_note=excluded.footer_note,logo=excluded.logo,updated_at=excluded.updated_at''',
                 (org,name,tagline,*colors,footer_note,image,stamp))
            self._audit(conn,org,'report_branding',org,'update',{'display_name':name,'logo_bytes':len(image)})
        return {k:v for k,v in self.report_branding(org).items() if k!='logo'}
