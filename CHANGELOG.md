# Linbit\.Linstor Release Notes

**Topics**

- <a href="#v0-9-7">v0\.9\.7</a>
    - <a href="#minor-changes">Minor Changes</a>
    - <a href="#breaking-changes--porting-guide">Breaking Changes / Porting Guide</a>
    - <a href="#bugfixes">Bugfixes</a>
    - <a href="#new-plugins">New Plugins</a>
        - <a href="#lookup">Lookup</a>
This changelog describes changes after version 0\.9\.6\.

<a id="v0-9-7"></a>
## v0\.9\.7

<a id="minor-changes"></a>
### Minor Changes

* New filter plugin <code>linstor\_addr</code> and lookup plugin <code>group\_addresses</code> for resolving LINSTOR\-facing addresses from host vars and group membership\.
* gateway\_install \- inline the LINSTOR Gateway GitHub download URL rather than templating it\. Simplifies the role and removes a variable from the public surface\.

<a id="breaking-changes--porting-guide"></a>
### Breaking Changes / Porting Guide

* gateway\_satellite \- role variables have been renamed with a <code>gateway\_satellite\_</code> prefix for namespacing\. Update any overrides in <code>hosts\.yaml</code>\, <code>group\_vars/</code>\, or playbook <code>vars\:</code> blocks\.

<a id="bugfixes"></a>
### Bugfixes

* client\_install \- replace the broken <code>linstor\-client\.j2</code> symlink with the real template so <code>/etc/linstor/linstor\-client\.conf</code> renders correctly\.
* gateway\_satellite \- fix <code>nfsv4\_only</code> handling so the NFSv4\-only path is honored end to end\.
* ha\_gateway \- default the NFS <code>mountd</code> listen address to <code>0\.0\.0\.0/0\.0\.0\.0</code> to match <code>linstor\-gateway</code> interop and avoid binding failures when the service IP is not yet present\.

<a id="new-plugins"></a>
### New Plugins

<a id="lookup"></a>
#### Lookup

* linbit\.linstor\.group\_addresses \- Resolve LINSTOR\-facing addresses for every host in an Ansible group\.
