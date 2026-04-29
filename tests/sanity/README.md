Sanity test ignore-list rationale
=================================

`ignore-X.Y.txt` files document violations from `ansible-test sanity` that are deliberately deferred.
The file format is strict (one entry per line, no blank lines, no comments), so this README captures the why.

License convention (permanent for this collection)
--------------------------------------------------

`validate-modules:missing-gplv3-license` is ignored on every module under `plugins/modules/`.
Ansible's sanity test assumes plugins are GPLv3-licensed.
This collection is MIT-licensed at the collection level (see top-level `LICENSE` and `galaxy.yml`).
Per-module GPLv3 headers are not used.
