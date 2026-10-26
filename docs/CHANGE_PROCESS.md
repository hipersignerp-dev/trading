# From prototype change to ERPNext change

Every prototype change is translated into one or more of these building blocks. Write the list in the pull request,
implement it, deploy to the demo site, and test.

| Prototype change | Build it as | Where in this app |
|---|---|---|
| New field on an existing document | Custom Field (module *Hipersign Trading*) | `fixtures/custom_field.json` |
| New list / record type | DocType | `hipersign_trading/doctype/<name>/` |
| New approval step or threshold | Workflow + Hipersign Settings field | `fixtures/workflow.json`, `doctype/hipersign_settings` |
| New rule ("cannot do X before Y") | `validate` / `on_submit` hook | `overrides/<doctype>.py`, `hooks.py → doc_events` |
| New dashboard tile or chart | Number Card / Dashboard Chart + workspace block | `number_card/`, `dashboard_chart/`, `workspace/` |
| New printed document | Print Format (Jinja, uses `templates/print/macros.html`) | `print_format/` |
| New screen that is not a form or list | Page | `page/<name>/` |
| New reminder or alert | Scheduler task | `tasks.py`, `hooks.py → scheduler_events` |
| Change to a button on a form | Client script | `public/js/*.js` |
| New sample record | Demo loader | `demo/data.py`, `demo/__init__.py`, `demo/v12.py` |
| New setting on an upgraded site | Patch | `patches/`, `patches.txt` |
| New calculated list (no new records) | Script Report | `report/<name>/` |

## Release checklist
- [ ] Version bumped in `hipersign_trading/__init__.py` and `hooks.py`, CHANGELOG.md updated
- [ ] `bench --site <demo> migrate` runs clean
- [ ] Changed Test Centre scripts pass on the demo site
- [ ] Live site backed up before `migrate`
