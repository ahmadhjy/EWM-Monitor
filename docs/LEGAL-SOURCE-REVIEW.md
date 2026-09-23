# Legal source restoration

The owner supplied the rendered original Privacy Policy and Terms and Conditions in September 2026 because the legacy site blocked automated retrieval. The files in data/pages preserve that English wording, including the Privacy Policy's March 15, 2022 update date. Arabic files translate the full text rather than substituting summaries.

Only semantic HTML and the privacy definition's archived website hyperlink were normalized. The hyperlink now targets the live canonical website. These documents are a restoration and translation, not newly reviewed legal advice or a certification of compliance.

## Owner review before domain launch

- The Market Information section of the original Terms says EWM and third-party providers **will be liable** for termination, interruption, delay or inaccuracy. This appears inconsistent with surrounding exclusions. It has deliberately NOT been silently changed; the Arabic translation also preserves positive liability.
- The original Privacy Policy mentions Flash cookies, third-party social login and tracking technologies that may not reflect the rebuilt site's actual behavior. Confirm these provisions and consent requirements with qualified counsel for the jurisdictions served.
- The Personal Data paragraph ends with “may include, but is not limited to:” without a following list in the supplied source. No missing list was invented.
- The original uses “employers” in one liability paragraph and “ElliottWaveMonittor” in another. These source choices are preserved rather than legally reinterpreted.
- SMTP/newsletter campaigns and analytics are not enabled. Contact messages and subscriber addresses are stored in the admin. Review retention, newsletter consent/unsubscribe handling and any future third-party processors before enabling those services.

## Editor and import workflow

Edit both languages under **Pages** in the English admin. Routine deployments never re-import these files or overwrite editor changes.

For a deliberate restoration from the bundled source only:

```bash
python manage.py populate_support_pages --overwrite
```

Without --overwrite, existing legal pages are preserved. Back up the database before replacing an owner's later amendments.
