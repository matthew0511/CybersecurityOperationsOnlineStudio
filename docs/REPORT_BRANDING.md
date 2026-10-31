# Organization report branding

Open **Board & reporting**, then **Report branding** below the report download cards. Set a report display name, tagline, primary/accent colors, and confidentiality/footer note. Upload a PNG or JPEG logo and choose **Save report branding**. Subsequent executive and board PDF/Excel downloads use the saved identity. Each organization has its own settings. Existing logos are retained when saving other fields; choose Remove the saved logo to remove only the client logo.

The preview shows the identity layout. PDF exports use proportional logo placement, brand colors, repeating page headers, readable table colors, page numbering and footer text. Excel exports include a Report Identity cover sheet with the logo, themed worksheet headers, summary charts and print headers/footers. Original detailed worksheet names and report disclosures are retained. Program Owner - Matthew Harris is fixed separately and cannot be altered through branding settings.

## Storage and access

Settings and normalized PNG logo bytes are stored in the encrypted organization-scoped PostgreSQL database, in the existing `xp_settings` organization settings. The workspace and report branding screens share the same logo, name, accent and footer. The standalone desktop service uses a separate `report_branding` table. Both read endpoints and logo downloads require authentication; writes require the existing CSRF-protected owner session and create an audit entry. Organization membership is checked for reads. Only the workspace owner can change branding; editor, reviewer and viewer roles cannot change it. No public logo bucket or external image fetch is used.

Endpoints: GET/POST `/api/report-branding/{org}`; GET `/api/report-branding/{org}/logo`. Only documented branding fields are accepted. No client-supplied path, image URL or template code is evaluated. Logo files are limited to 2 MiB and eight million source pixels, decoded as PNG/JPEG, stripped of metadata, and resized within 1200 × 400 pixels without cropping. SVG, animated formats and unrecognized content are rejected. Report renderers further fit the normalized image to their header/cover slot while preserving proportions. Transparent PNG is recommended for logos with transparent backgrounds.

## Deployment

This release uses the existing workspace settings table and requires no additional production schema migration. Existing reminders and unrelated settings are retained when branding is saved. The normal migration creates the workspace schema for fresh installations. Build from a pinned GitHub commit using an immutable image tag; the project's historical S3 source archive may be older than the GitHub branch.

Tests cover normalization, invalid files/oversized pixels, organization isolation, persisted settings, logo retention/removal, Excel formula protection, embedded images, fixed owner footers, authentication/CSRF and all four branded report downloads.
