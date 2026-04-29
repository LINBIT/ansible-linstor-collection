Sanity test ignore-list rationale
=================================

`ignore-X.Y.txt` files document violations from `ansible-test sanity` that are deliberately deferred.
The file format is strict — one entry per line, no blank lines, no comments — so this README captures the why.

Two categories of entries currently sit in `ignore-2.20.txt`:

License convention (permanent for this collection)
--------------------------------------------------

`validate-modules:missing-gplv3-license` is ignored on every module under `plugins/modules/`.
Ansible's sanity test assumes plugins are GPLv3-licensed.
This collection is MIT-licensed at the collection level (see top-level `LICENSE` and `galaxy.yml`).
Per-module GPLv3 headers are not used.

Real bugs to address before Galaxy publication
----------------------------------------------

The following entries are TODOs that should be fixed and removed from the ignore file when work proceeds.

| Entry | Action |
|---|---|
| `plugins/modules/resource.py validate-modules:doc-default-does-not-match-spec` | `argument_spec` defines `nodes` default as `[]` but `DOCUMENTATION` says `None`. Reconcile. |
| `plugins/modules/file.py validate-modules:undocumented-parameter` | `controllers` argument is in `argument_spec` but missing from `DOCUMENTATION`. Add documentation. |
| `plugins/modules/file.py validate-modules:parameter-type-not-in-doc` | Same `controllers` argument: type missing from doc. Fix together with the entry above. |
| `plugins/modules/backup.py validate-modules:no-log-needed` | `s3_key` is a credential and should set `no_log: true` in `argument_spec`. |
| `plugins/modules/backup.py validate-modules:parameter-state-invalid-choice` | `state` extends Ansible's standard `{present, absent}` with custom values (`info`, `list`) used by the read-side workflow. Ansible's validator expects standard choices; LINSTOR's API surface needs these. Decide whether to refactor or keep ignored. |
