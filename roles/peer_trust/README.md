peer_trust
==========

Trust a peer LINSTOR cluster's CA for cross-cluster backup shipping.

LINSTOR-to-LINSTOR backup shipping coordinates over the controller's REST API.
When the destination cluster runs HTTPS-only (the default for clusters initialized with `ssl_init`), the source cluster's controller must trust the destination's CA certificate.
This role imports a peer cluster's CA into the local Java truststore so that subsequent `backup_ship` calls can negotiate TLS successfully.

The role is one-shot per peer relationship.
Re-running with the same `peer_trust_alias` and unchanged peer cert is a no-op via `community.general.java_cert`'s alias check, and does not restart `linstor-controller`.

Requirements
------------

`community.general` (>= 10.4.0) for the `java_cert` module.

The peer cluster must be reachable over SSH from the local controller for the CA-cert read step (the role uses `delegate_to: "{{ peer_trust_peer_host }}"`).

Role Variables
--------------

| Variable | Default | Description |
|---|---|---|
| `peer_trust_peer_host` | _required_ | Inventory hostname of a controller in the peer cluster, used as `delegate_to` to read the peer's CA. |
| `peer_trust_alias` | _required_ | Alias under which the peer CA is stored in the local Java truststore. Must be unique per peer. |
| `peer_trust_remote_ca_path` | `/etc/linstor/ssl/ca.crt` | Path on the peer controller where the peer cluster's CA cert lives. |
| `peer_trust_keystore_path` | `/etc/ssl/certs/java/cacerts` | Path to the Java truststore on the local controller. |
| `peer_trust_keystore_password` | `changeit` | Password for the local Java truststore. Matches the OpenJDK default. |

Dependencies
------------

None.

Example Playbook
----------------

Trust a single peer cluster's CA on every controller in the local cluster:

```yaml
- name: Trust the DR cluster CA on the primary cluster controllers
  hosts: linstor_controllers
  become: true
  tasks:
    - ansible.builtin.import_role:
        name: linbit.linstor.peer_trust
      vars:
        peer_trust_peer_host: dr-linstor-0.example.com
        peer_trust_alias: dr-cluster-ca
```

Trust multiple peer clusters in one play with a loop:

```yaml
- name: Trust multiple peer cluster CAs
  hosts: linstor_controllers
  become: true
  tasks:
    - ansible.builtin.include_role:
        name: linbit.linstor.peer_trust
      vars:
        peer_trust_peer_host: "{{ item.host }}"
        peer_trust_alias: "{{ item.alias }}"
      loop:
        - { host: dr-linstor-0.example.com, alias: dr-cluster-ca }
        - { host: archive-linstor-0.example.com, alias: archive-cluster-ca }
```

After the role completes, run the `linbit.linstor.remote` module to register the bidirectional remote pointing at the peer's HTTPS endpoint, then proceed with `linbit.linstor.backup_ship`.

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
