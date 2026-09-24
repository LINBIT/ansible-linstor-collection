# Linbit\.Linstor Release Notes

**Topics**

- <a href="#v0-9-10">v0\.9\.10</a>
    - <a href="#major-changes">Major Changes</a>
    - <a href="#minor-changes">Minor Changes</a>
    - <a href="#breaking-changes--porting-guide">Breaking Changes / Porting Guide</a>
    - <a href="#bugfixes">Bugfixes</a>
    - <a href="#new-modules">New Modules</a>
- <a href="#v0-9-9">v0\.9\.9</a>
    - <a href="#minor-changes-1">Minor Changes</a>
- <a href="#v0-9-8">v0\.9\.8</a>
    - <a href="#major-changes-1">Major Changes</a>
    - <a href="#minor-changes-2">Minor Changes</a>
    - <a href="#bugfixes-1">Bugfixes</a>
    - <a href="#new-modules-1">New Modules</a>
- <a href="#v0-9-7">v0\.9\.7</a>
    - <a href="#minor-changes-3">Minor Changes</a>
    - <a href="#breaking-changes--porting-guide-1">Breaking Changes / Porting Guide</a>
    - <a href="#bugfixes-2">Bugfixes</a>
    - <a href="#new-plugins">New Plugins</a>
        - <a href="#lookup">Lookup</a>

This changelog describes changes after version 0\.9\.6\.

<a id="v0-9-10"></a>
## v0\.9\.10

<a id="major-changes"></a>
### Major Changes

* Support LINSTOR token authentication \(LINSTOR 1\.34\.0 and later\)\. All LINSTOR API modules authenticate with the <code>auth\-token</code> from <code>linstor\-client\.conf</code> or the <code>auth\_token</code> module parameter\. The <code>auth\_init</code>\, <code>auth\_token</code>\, and <code>auth\_token\_info</code> modules enable authentication and manage tokens\.

<a id="minor-changes"></a>
### Minor Changes

* Add read\-only <code>\_info</code> modules for every queryable LINSTOR object type\.
* LINSTOR modules \- add a <code>config\_file</code> option that reads the controller list\, auth token\, and TLS certificate paths from a given <code>linstor\-client\.conf</code> in place of <code>\~/\.config/linstor</code> and <code>/etc/linstor</code>\. When a module runs on the Ansible control node\, the action plugin fills the option from the <code>linstor\_client\_config\_file</code> variable\, so one inventory variable gives each cluster its own control node client configuration and several clusters\, or parallel playbook runs\, no longer overwrite each other\'s controllers and token\.
* Requirements \- raise the minimum python\-linstor version to 1\.28\.1\.
* auth\_init \- <code>auth\_init\_local\_cafile</code> follows <code>ssl\_init\_local\_dir</code> when it is set\.
* auth\_init \- new role that enables token authentication and saves the user token at mode <code>0600</code> in <code>linstor\-client\.conf</code> for the control node user and for root on the controllers\. The role skips controllers older than LINSTOR 1\.34\.0\.
* client\_install \- new <code>linstor\_client\_auth\_token</code> variable writes an <code>auth\-token</code> entry into <code>linstor\-client\.conf</code>\.
* client\_install \- new <code>linstor\_client\_cafile</code> variable sets the CA file in the control node <code>linstor\-client\.conf</code>\.
* client\_install\, auth\_init \- add <code>linstor\_client\_config\_file</code> to set where the <code>linstor\-client\.conf</code> on the control node is written\, and <code>client\_install\_local\_config</code> to skip writing it\. It defaults to <code>false</code> when <code>linstor\_api\_delegate</code> points at another host\, so delegating to a controller node leaves the control node untouched\. A saved auth token is kept in the control node config only when the file shares a controller address with the inventory\, so a cluster at other addresses never inherits it\.
* cluster\_init \- new <code>cluster\_init\_token\_auth</code> variable \(default <code>true</code>\) runs the <code>auth\_init</code> role after cluster membership registration\.
* cluster\_membership\, controller\_install\, ssl\_init\, ha\_database \- fail with a clear message when the <code>linstor\_controllers</code> group is empty\.
* controller\_install\, satellite\_install \- new <code>linstor\_install\_version</code> variable pins <code>linstor\-controller</code>\, <code>linstor\-satellite</code>\, and <code>linstor\-common</code> to a version\, for example <code>1\.33\.3</code>\, and locks them in the package manager\. Empty\, the default\, installs the newest version\.
* controller\_install\, satellite\_install\, gateway\_install\, gateway\_satellite\, ha\_controller\_proxy \- new <code>\<role\>\_firewalld\_zone</code> variable selects the firewalld zone for the ports each role opens\. Set it when a zone is bound to a source\, because a port in the default zone does not apply to traffic matched into a source zone\. Empty\, the default\, uses the default zone \([https\://github\.com/LINBIT/ansible\-linstor\-collection/issues/2](https\://github\.com/LINBIT/ansible\-linstor\-collection/issues/2)\)\.
* gateway\_install \- new <code>gateway\_install\_from\_github</code> variable installs the latest <code>linstor\-gateway</code> release binary from GitHub instead of the distribution package\.
* gateway\_install \- new <code>gateway\_install\_package\_state</code> variable \(default <code>present</code>\)\. Set it to <code>latest</code> to upgrade\.
* gateway\_install\, gateway\_satellite \- configure LINSTOR Gateway for token\-authenticated clusters\. The daemon connects to the controller HTTPS endpoint\, trusts the controller CA\, and reads its token from the <code>token\_file</code> key in <code>linstor\-gateway\.toml</code>\. Nodes holding a satellite token in <code>/var/lib/linstor\.d/auth\.json</code> use it\, and other nodes get a dedicated token that <code>gateway\_satellite\_token\_force</code> rotates\.
* gateway\_satellite \- install SCST with the <code>linbit\.drbd\_reactor\.scst\_install</code> role when <code>gateway\_satellite\_scst</code> is <code>true</code>\. By default it builds the latest SCST release\.
* gateway\_satellite \- install the HA dependencies on every host in <code>linstor\_gateway\_satellites</code>\.
* gateway\_satellite \- new <code>gateway\_satellite\_ganesha</code> variable \(default <code>false</code>\) installs the NFS\-Ganesha userspace NFS server with the <code>linbit\.drbd\_reactor\.ganesha\_install</code> role\.
* gateway\_satellite \- token authentication is detected from the controller or set with <code>gateway\_satellite\_token\_auth</code>\. Without <code>ssl\_init</code>\, the role trusts the controller\'s auto\-generated certificate\, or the CA in <code>gateway\_satellite\_ca\_cert</code>\. Requires linstor\-gateway 2\.3\.0 or later\.
* ha\_controller\_proxy \- new role that runs a dedicated HAProxy instance \(<code>linstor\-haproxy\.service</code>\) on the controllers and forwards LINSTOR API and GUI traffic to the active controller\. It is an alternative to a virtual IP that also works on routed and cloud networks\, and it leaves the distribution <code>haproxy\.service</code> untouched\.
* ha\_database \- check that an explicit <code>ha\_database\_pool</code> is a diskful pool on every combined node before the conversion starts\.
* ha\_database \- new <code>ha\_database\_haproxy</code> variable \(default <code>false</code>\) deploys the <code>ha\_controller\_proxy</code> role after the HA database conversion\.
* ha\_database\, ha\_gateway \- find the diskful nodes from the storage pools registered in LINSTOR instead of from inventory groups\.
* ha\_gateway \- NFS exports accept an <code>implementation</code> key \(<code>kernel</code> or <code>ganesha</code>\, default from <code>ha\_gateway\_nfs\_implementation</code>\)\. <code>ganesha</code> serves the export with NFS\-Ganesha and matches <code>linstor\-gateway nfs create \-\-implementation\=ganesha</code>\.
* ha\_gateway \- new per\-target <code>layer\_list</code> option sets the layer stack of iSCSI\, NFS\, and NVMe\-oF targets\, for example to add LUKS encryption\. Targets placed with a resource group take the layers from the group\.
* host\_storage\_pools filter \- new filter that returns the <code>linstor\_storage\_pools</code> entries that target a host\.
* physical\_storage \- new module that creates LVM\, LVM thin\, ZFS\, or SPDK device pools from unused block devices on a satellite\, with optional VDO or self\-encrypting drive setup\, and can register the result as a storage pool\. <code>physical\_storage\_info</code> lists the eligible devices\.
* resource \- new <code>layer\_list</code> parameter sets the layer stack of the resource definition in manual and autoplace modes\.
* roles \- support Ubuntu 26\.04 \(Resolute\)\.
* satellite\_install \- install ZFS with the <code>linbit\.common\.zfs\_install</code> role\.
* storage\_pool \- create Windows Storage Spaces pools on LINBIT SDS for Windows satellites with the <code>storagespaces</code> and <code>storagespaces\_thin</code> types and the <code>wss</code> key\. The role builds the pool from <code>physical\_devices</code> and refuses boot and system disks\.
* storage\_pool \- new <code>vdevs</code> key adds log\, special\, cache\, and extra data vdevs to ZFS pools\.
* storage\_pool \- support diskless storage pools with <code>driver\: diskless</code> in the module and <code>type\: diskless</code> in the role\. The role only registers the pool and needs no <code>physical\_devices</code> \([https\://github\.com/LINBIT/ansible\-linstor\-collection/issues/1](https\://github\.com/LINBIT/ansible\-linstor\-collection/issues/1)\)\.

<a id="breaking-changes--porting-guide"></a>
### Breaking Changes / Porting Guide

* Remove <code>state\: query</code> from the LINSTOR manage modules \(<code>controller</code>\, <code>node</code>\, <code>node\_interface</code>\, <code>storage\_pool</code>\, <code>resource</code>\, <code>resource\_definition</code>\, <code>resource\_group</code>\, <code>volume\_group</code>\, <code>snapshot</code>\, <code>remote</code>\, <code>schedule</code>\, <code>key\_value\_store</code>\, and <code>file</code>\)\. Use the matching <code>\_info</code> module instead\.
* The <code>controller\_env</code> filter is removed\. Use the <code>linbit\.linstor\.controller\_env</code> lookup\, which returns the same <code>LS\_CONTROLLERS</code> string\.
* cluster\_init \- <code>cluster\_init\_deploy\_storage</code> defaults to <code>true</code>\, and the HA database conversion \(<code>cluster\_init\_ha\_database</code>\, default <code>true</code>\) no longer requires it\. Set <code>cluster\_init\_ha\_database\: false</code> to keep a cluster without an HA database\.
* cluster\_init \- enables token authentication by default on clusters running LINSTOR 1\.34\.0 or later\. Clients that do not send a token\, such as storage plugins without token support\, get <code>401</code> responses\. Set <code>cluster\_init\_token\_auth\: false</code> to keep token authentication off\.
* gateway\_satellite \- <code>gateway\_satellite\_scst\_version</code> is removed\. Set <code>scst\_install\_version</code> to pin the SCST build reference\.
* ha\_database \- <code>ha\_database\_res</code> is removed and the HA database resource is always named <code>linstor\_db</code>\, the name the LINSTOR User Guide and the linstor\-controller\-ha\-setup script use\.
* storage\_pool \- a pool without <code>nodes</code> or <code>groups</code> targets every host in <code>linstor\_satellites</code>\. The <code>linstor\_diskful\_satellites</code> and <code>linstor\_diskless\_satellites</code> groups no longer limit pool placement\, so scope pools away from diskless satellites with <code>nodes</code> or <code>groups</code>\.

<a id="bugfixes"></a>
### Bugfixes

* LINSTOR API modules \- keep privilege escalation when <code>linstor\_api\_delegate</code> points at a remote host\, so the modules can read root\-owned client configuration there\. <code>become</code> is dropped only for <code>delegate\_to\: localhost</code>\.
* cluster\_membership \- do not restart the controller service after node registration\. On multi\-controller clusters it started standby controllers that must stay stopped\.
* controller\_env lookup \- read <code>linstor\_ssl</code> as a boolean\, so a string such as <code>\-e linstor\_ssl\=false</code> no longer selects the SSL scheme and breaks connections to non\-SSL clusters\.
* controller\_env lookup\, client\_install \- write the <code>linstor\+ssl\://</code> scheme for SSL clusters instead of <code>linstors\://</code>\, which python\-linstor does not recognize\. Clients connect to the HTTPS port directly instead of relying on the redirect from the plain port\.
* controller\_install \- select the first controller by exact hostname match\, so hostnames that contain one another no longer confuse the controller start and stop selection\.
* galaxy\.yml \- require <code>community\.general</code> 11\.0\.0 or later for the <code>zpool</code> module\, <code>linbit\.common</code> 0\.9\.9 or later for the <code>zfs\_install</code> role\, and <code>linbit\.drbd\_reactor</code> 0\.9\.9 or later for the <code>scst\_install</code> and <code>ganesha\_install</code> roles\.
* gateway\_install \- restart linstor\-gateway when <code>linstor\-gateway\.toml</code> changes\.
* gateway\_install \- restore the fallback to the GitHub release binary when the package install fails\. The package install is retried up to three times first\, so a transient repository failure does not trigger the fallback\.
* gateway\_install \- write a valid <code>linstor\-gateway\.toml</code> with full controller URLs\, including scheme and port\. The template produced invalid TOML and a garbled address\, so LINSTOR Gateway fell back to <code>localhost\:3370</code>\.
* gateway\_satellite \- fail when the NFS or iSCSI backend packages do not install\. The error was ignored and left targets unable to promote\.
* ha\_database \- an empty <code>ha\_database\_pool</code> selects the first diskful pool on the combined nodes\, as documented\, instead of failing the conversion\.
* ha\_database \- stop setting the immutable attribute on <code>/var/lib/linstor</code>\. It blocked teardown and re\-initialization of the HA database\.
* ha\_database \- treat an existing HA database resource definition as an already converted cluster\. Clusters converted with the linstor\-controller\-ha\-setup script do not carry the <code>ClusterIsHA</code> property\, and a second conversion failed on the mounted database\.
* ha\_gateway \- reject targets that set both <code>nodes</code> and <code>resource\_group</code>\. The combination ignored the resource group\'s storage pool and layer settings\.
* ha\_gateway \- remove absent targets one at a time and retry each delete until the resource is no longer in use\. Removing them all at once could leave a resource promoted\, so its delete never succeeded\.
* roles \- fix argument spec validation on ansible\-core 2\.19 and later when the <code>linstor\_controllers</code> group is empty\. A Jinja expression in the <code>linstor\_api\_delegate</code> description crashed the validation\.
* roles \- stop adding <code>localhost</code> to the <code>all</code> inventory group\. A later play with <code>hosts\: all</code> and <code>become\: true</code> gathered facts on localhost and failed with a sudo prompt on control nodes without passwordless root\.
* satellite\_install \- enable and start linstor\-satellite on every run\. A node whose package was installed outside the role\, or whose service was stopped\, never started it\.
* satellite\_install \- fix the ZFS install on Oracle Linux \(EPEL package and UEK DKMS compiler\) and on Debian OS family cloud kernels\. The Red Hat family kmod install no longer pulls an unversioned <code>kernel\-devel</code>\.
* ssl\_init \- create <code>/etc/linstor/ssl</code> at mode <code>0755</code> so the non\-root controller service user of LINSTOR 1\.34\.0 can read its keystore\. The private key keeps mode <code>0600</code>\.
* ssl\_init \- regenerate a cached node certificate whose SAN no longer matches the inventory\, and rebuild the keystore and truststores when the pushed certificate\, key\, or CA changes\. Stale material failed TLS hostname verification and skipped the service restart\.
* ssl\_init \- restore macOS control hosts\. LibreSSL wrote EC keys with explicit curve parameters that Java rejects\, so the role requests named\-curve keys\. Delete a <code>ca\.key</code> generated on a Mac under <code>ssl\_init\_local\_dir</code> before running the role again\.
* ssl\_init \- retry the controller status query on transient failures and do not double\-count controllers when the role runs twice in one play\.
* storage\_pool \- fail when a pool already exists with a different driver or backing pool instead of reporting <code>ok</code>\. LINSTOR cannot change either\, so delete the pool and create it again\.

<a id="new-modules"></a>
### New Modules

* linbit\.linstor\.auth\_init \- Initialize LINSTOR token authentication\.
* linbit\.linstor\.auth\_token \- Manage LINSTOR auth tokens\.
* linbit\.linstor\.auth\_token\_info \- Query LINSTOR auth tokens\.
* linbit\.linstor\.controller\_info \- Query LINSTOR controller properties\.
* linbit\.linstor\.encryption\_info \- Query LINSTOR encryption status\.
* linbit\.linstor\.file\_info \- Query a LINSTOR external file\.
* linbit\.linstor\.key\_value\_store\_info \- Query a LINSTOR key\-value store\.
* linbit\.linstor\.node\_info \- Query LINSTOR nodes\.
* linbit\.linstor\.node\_interface\_info \- Query LINSTOR node network interfaces\.
* linbit\.linstor\.physical\_storage \- Create LVM\, ZFS\, or SPDK device pools on LINSTOR satellites\.
* linbit\.linstor\.physical\_storage\_info \- Query unused block devices on LINSTOR satellites\.
* linbit\.linstor\.remote\_info \- Query LINSTOR remotes\.
* linbit\.linstor\.resource\_definition\_info \- Query LINSTOR resource definitions\.
* linbit\.linstor\.resource\_group\_info \- Query LINSTOR resource groups\.
* linbit\.linstor\.resource\_info \- Query LINSTOR resources\.
* linbit\.linstor\.schedule\_info \- Query LINSTOR backup schedules\.
* linbit\.linstor\.snapshot\_info \- Query LINSTOR snapshots\.
* linbit\.linstor\.storage\_pool\_info \- Query LINSTOR storage pools\.
* linbit\.linstor\.volume\_group\_info \- Query LINSTOR volume groups\.

<a id="v0-9-9"></a>
## v0\.9\.9

<a id="minor-changes-1"></a>
### Minor Changes

* plugins/action \- add a shared action\-plugin base that forces <code>become\: false</code> on every LINSTOR API module\, so a parent play\'s <code>become\: true</code> no longer bleeds into the delegated API call\.
* plugins/action\, plugins/filter\, plugins/lookup \- SPDX headers flipped from MIT to GPL\-3\.0\-or\-later for Ansible community package inclusion compliance\. <code>galaxy\.yml</code> now declares both MIT and GPL\-3\.0\-or\-later\. Modules and <code>module\_utils</code> remain MIT\.
* plugins/modules \- document the recommended play structure \(single\-host play with <code>connection\: local</code>\, or <code>delegate\_to\: localhost</code> per task\) for invoking LINSTOR API modules\. Each module\'s first EXAMPLES entry now models the pattern\.

<a id="v0-9-8"></a>
## v0\.9\.8

<a id="major-changes-1"></a>
### Major Changes

* LINSTOR modules now execute on the Ansible control node and talk directly to the LINSTOR controller\, rather than running on each managed node via that node\'s <code>python\-linstor</code>\. The previous on\-node pattern piggybacked on the <code>python\-linstor</code> that ships transitively with <code>linstor\-client</code>\, which ruled out targeting hosts that cannot host it \(Windows nodes\, Linux nodes with mixed Python environments where Ansible\'s interpreter discovery is unreliable\)\. The Ansible control node now requires <code>python\-linstor</code>\. The collection\'s own roles handle the delegation internally\; user playbook surface is unchanged\.

<a id="minor-changes-2"></a>
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

<a id="bugfixes-1"></a>
### Bugfixes

* Roles now gather OS facts defensively at the start of their task lists\, so they can run from standalone playbooks that skip the usual <code>linbit\.internal\.common</code> fact\-gathering play\.
* cluster\_membership \- reject <code>localhost</code>/<code>127\.0\.0\.0/8</code> and loopback addresses when resolving the LINSTOR registration IP\, so misconfigured inventories fail fast instead of producing an unreachable cluster\.
* ssl\_init \- assert that any pre\-existing local CA on the control node matches the cluster\'s CA before continuing\. If they differ\, fail with a clear message pointing at the local path to remove rather than silently re\-keying the cluster and breaking trust for every other workstation and consumer\.
* ssl\_init \- flip satellite netinterfaces to SSL after the controller restart\, not before\, so the SSL connector is up when the modify lands and no longer produces a spurious <code>LinStorRuntimeException</code> ErrorReport per satellite\. The previous <code>failed\_when\: false</code> suppression is replaced with a <code>state\: query</code> gate so fresh installs still skip cleanly\.

<a id="new-modules-1"></a>
### New Modules

* linbit\.linstor\.linstor\_installed \- Detect whether LINSTOR is installed on the target host\.

<a id="v0-9-7"></a>
## v0\.9\.7

<a id="minor-changes-3"></a>
### Minor Changes

* New filter plugin <code>linstor\_addr</code> and lookup plugin <code>group\_addresses</code> for resolving LINSTOR\-facing addresses from host vars and group membership\.
* gateway\_install \- inline the LINSTOR Gateway GitHub download URL rather than templating it\. Simplifies the role and removes a variable from the public surface\.

<a id="breaking-changes--porting-guide-1"></a>
### Breaking Changes / Porting Guide

* gateway\_satellite \- role variables have been renamed with a <code>gateway\_satellite\_</code> prefix for namespacing\. Update any overrides in <code>hosts\.yaml</code>\, <code>group\_vars/</code>\, or playbook <code>vars\:</code> blocks\.

<a id="bugfixes-2"></a>
### Bugfixes

* client\_install \- replace the broken <code>linstor\-client\.j2</code> symlink with the real template so <code>/etc/linstor/linstor\-client\.conf</code> renders correctly\.
* gateway\_satellite \- fix <code>nfsv4\_only</code> handling so the NFSv4\-only path is honored end to end\.
* ha\_gateway \- default the NFS <code>mountd</code> listen address to <code>0\.0\.0\.0/0\.0\.0\.0</code> to match <code>linstor\-gateway</code> interop and avoid binding failures when the service IP is not yet present\.

<a id="new-plugins"></a>
### New Plugins

<a id="lookup"></a>
#### Lookup

* linbit\.linstor\.group\_addresses \- Resolve LINSTOR\-facing addresses for every host in an Ansible group\.
