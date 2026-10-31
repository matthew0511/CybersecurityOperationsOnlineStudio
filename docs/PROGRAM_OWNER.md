# Program owner attribution

Program Owner - Matthew Harris is fixed in application source, displayed on the sign-in screen, workspace header and footer, and included in the shared executive/board PDF and Excel report footers.

The attribution is independent of signed-in usernames and organization records. There is no application preference, form field, or API operation for changing or removing it. The production container serves the bundled source from its read-only filesystem.

This protects the attribution from removal through normal application use. Repository and deployment administrators can still modify or replace source code; absolute removal prevention against those administrators is not technically possible.
