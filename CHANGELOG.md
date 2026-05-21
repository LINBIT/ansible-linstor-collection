# Linbit\.Linstor Release Notes

**Topics**

- <a href="#v0-9-9">v0\.9\.9</a>
    - <a href="#minor-changes">Minor Changes</a>
- <a href="#v0-9-8">v0\.9\.8</a>
    - <a href="#major-changes">Major Changes</a>
    - <a href="#minor-changes-1">Minor Changes</a>
    - <a href="#bugfixes">Bugfixes</a>
    - <a href="#new-modules">New Modules</a>
- <a href="#v0-9-7">v0\.9\.7</a>
    - <a href="#minor-changes-2">Minor Changes</a>
    - <a href="#breaking-changes--porting-guide">Breaking Changes / Porting Guide</a>
    - <a href="#bugfixes-1">Bugfixes</a>
    - <a href="#new-plugins">New Plugins</a>
        - <a href="#lookup">Lookup</a>

This changelog describes changes after version 0\.9\.6\.

<a id="v0-9-9"></a>
## v0\.9\.9

<a id="minor-changes"></a>
### Minor Changes

* plugins/action \- add a shared action\-plugin base that forces <code>become\: false</code> on every LINSTOR API module\, so a parent play\'s <code>become\: true</code> no longer bleeds into the delegated API call\.
* plugins/action\, plugins/filter\, plugins/lookup \- SPDX headers flipped from MIT to GPL\-3\.0\-or\-later for Ansible community package inclusion compliance\. <code>galaxy\.yml</code> now declares both MIT and GPL\-3\.0\-or\-later\. Modules and <code>module\_utils</code> remain MIT\.
* plugins/modules \- document the recommended play structure \(single\-host play with <code>connection\: local</code>\, or <code>delegate\_to\: localhost</code> per task\) for invoking LINSTOR API modules\. Each module\'s first EXAMPLES entry now models the pattern\.

<a id="v0-9-8"></a>
## v0\.9\.8

<a id="major-changes"></a>
### Major Changes

* LINSTOR modules now execute on the Ansible control node and talk directly to the LINSTOR controller\, rather than running on each managed node via that node\'s <code>python\-linstor</code>\. The previous on\-node pattern piggybacked on the <code>python\-linstor</code> that ships transitively with <code>linstor\-client</code>\, which ruled out targeting hosts that cannot host it \(Windows nodes\, Linux nodes with mixed Python environments where Ansible\'s interpreter discovery is unreliable\)\. The Ansible control node now requires <code>python\-linstor</code>\. The collection\'s own roles handle the delegation internally\; user playbook surface is unchanged\.

<a id="minor-changes-1"></a>
### Minor Changes

* All package\-install tasks now wrap with <code>retries\: 3</code> and <code>delay\: 10</code> so transient mirror/TLS flake during package installation does not abort the role\.
* Every LINSTOR module that wraps <code>python\-linstor</code> now includes an <code>EXAMPLES</code> entry showing how to route the API call through a LINSTOR controller via <code>delegate\_to\:</code> for SSH jump host and segmented management network setups\. The <code>controller</code> module also demonstrates the <code>block\:</code> pattern for sharing delegation across a sequence of LINSTOR tasks\.
* New <code>controller\_env</code> filter and lookup for building an <code>LS\_CONTROLLERS</code> URI string from inventory\. The lookup emits a comma\-joined controller list \(no VIP\)\; LINSTOR clients walk it and connect to whichever controller responds\. The <code>linstors\://</code> scheme is used when <code>linstor\_ssl</code> is set\.
* New <code>linstor\_installed</code> module that reports whether <code>linstor\-controller</code>/<code>linstor\-satellite</code> are installed on the target host\. Replaces an earlier filter\-plugin prototype\.
* New <code>linstor</code> action group in <code>meta/runtime\.yml</code> covering every LINSTOR object module\. Helps keep LINSTOR module calling inside playbooks more straightforward with the new control\-node built\-in delegation pattern \(avoids repeating <code>controllers\:</code> on every module call\)\.
* Ship a <code>requirements\.txt</code> declaring <code>python\-linstor</code> so the control\-node side of the collection can be installed with <code>pip install \-r requirements\.txt</code>\.
* The <code>linstor\_connection\.py</code> shared module util now reads client certificate paths from both <code>/etc/linstor/</code> and the XDG user config directory so control\-node\-side runs and on\-node CLI invocations pick the same credentials\.
* The <code>linstor\_ha\_vip</code> variable is now <code>ha\_database</code>\-only\, no longer threaded through general client/controller address resolution\.
* The control\-node <code>\~/\.config/linstor/linstor\-client\.conf</code> is auto\-materialized on every cluster bring\-up so subsequent <code>linstor</code> CLI invocations target the right cluster\. The <code>client\_install</code> role writes the plain variant when <code>linstor\_ssl</code> is false\; <code>ssl\_init</code> fetches the cluster\'s CA from a controller and writes the <code>linstors\://</code> variant\.
* cluster\_membership \- pre\-flight that the control\-node\'s <code>\~/\.config/linstor/linstor\-client\.conf</code> actually reaches the LINSTOR controller and fail with an actionable message pointing at <code>client\_install</code> to refresh stale local config\, instead of letting the first module call fail with a generic connection error\.
* ssl\_init \- convert the controller/satellite restart sequence to handlers notified by change\-producing tasks\. A re\-run with no changes now fires zero restarts\; a partial re\-run only triggers restarts when keystores\, truststores\, or SSL TOML actually changed\.
* storage\_pool \- support the <code>storagespaces</code> and <code>storagespaces\_thin</code> drivers \(Windows Storage Spaces\)\, including the matching <code>DOCUMENTATION</code> choices on the module\.

<a id="bugfixes"></a>
### Bugfixes

* Roles now gather OS facts defensively at the start of their task lists\, so they can run from standalone playbooks that skip the usual <code>linbit\.internal\.common</code> fact\-gathering play\.
* cluster\_membership \- reject <code>localhost</code>/<code>127\.0\.0\.0/8</code> and loopback addresses when resolving the LINSTOR registration IP\, so misconfigured inventories fail fast instead of producing an unreachable cluster\.
* ssl\_init \- assert that any pre\-existing local CA on the control node matches the cluster\'s CA before continuing\. If they differ\, fail with a clear message pointing at the local path to remove rather than silently re\-keying the cluster and breaking trust for every other workstation and consumer\.
* ssl\_init \- flip satellite netinterfaces to SSL after the controller restart\, not before\, so the SSL connector is up when the modify lands and no longer produces a spurious <code>LinStorRuntimeException</code> ErrorReport per satellite\. The previous <code>failed\_when\: false</code> suppression is replaced with a <code>state\: query</code> gate so fresh installs still skip cleanly\.

<a id="new-modules"></a>
### New Modules

* linbit\.linstor\.linstor\_installed \- Detect whether LINSTOR is installed on the target host\.

<a id="v0-9-7"></a>
## v0\.9\.7

<a id="minor-changes-2"></a>
### Minor Changes

* New filter plugin <code>linstor\_addr</code> and lookup plugin <code>group\_addresses</code> for resolving LINSTOR\-facing addresses from host vars and group membership\.
* gateway\_install \- inline the LINSTOR Gateway GitHub download URL rather than templating it\. Simplifies the role and removes a variable from the public surface\.

<a id="breaking-changes--porting-guide"></a>
### Breaking Changes / Porting Guide

* gateway\_satellite \- role variables have been renamed with a <code>gateway\_satellite\_</code> prefix for namespacing\. Update any overrides in <code>hosts\.yaml</code>\, <code>group\_vars/</code>\, or playbook <code>vars\:</code> blocks\.

<a id="bugfixes-1"></a>
### Bugfixes

* client\_install \- replace the broken <code>linstor\-client\.j2</code> symlink with the real template so <code>/etc/linstor/linstor\-client\.conf</code> renders correctly\.
* gateway\_satellite \- fix <code>nfsv4\_only</code> handling so the NFSv4\-only path is honored end to end\.
* ha\_gateway \- default the NFS <code>mountd</code> listen address to <code>0\.0\.0\.0/0\.0\.0\.0</code> to match <code>linstor\-gateway</code> interop and avoid binding failures when the service IP is not yet present\.

<a id="new-plugins"></a>
### New Plugins

<a id="lookup"></a>
#### Lookup

* linbit\.linstor\.group\_addresses \- Resolve LINSTOR\-facing addresses for every host in an Ansible group\.
