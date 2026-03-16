ssl
===

Configure SSL/TLS for LINSTOR REST API and satellite connections.

This role automates the full certificate lifecycle and LINSTOR configuration for two independently toggleable features:
REST API HTTPS (controller serves HTTPS on port 3371) and satellite SSL (controller-to-satellite mutual TLS on port 3367).
An optional third feature, REST API mTLS, adds client certificate authentication on top of HTTPS.

The role generates self-signed certificates using Java keytool, builds cross-node truststores, patches LINSTOR TOML configuration files, and restarts services.
After the role completes, `linstor-client.conf` is updated with the `linstors://` scheme so that subsequent module calls (for example `cluster_membership`) connect over HTTPS.

Requirements
------------

The following inventory groups must be defined:

- `linstor_controllers`: nodes running the LINSTOR controller
- `linstor_satellites`: nodes running the LINSTOR satellite

Java `keytool` must be available on all cluster nodes (installed by the `linstor-controller` and `linstor-satellite` packages).

When `ssl_https_mtls` is true, `openssl` must also be available on the first controller node.

Role Variables
--------------

| Variable | Default | Description |
|---|---|---|
| `ssl_https` | `true` | Enable HTTPS on the LINSTOR REST API (port 3371) |
| `ssl_satellite` | `true` | Enable SSL for controller-to-satellite communication (port 3367) |
| `ssl_https_mtls` | `false` | Enable client certificate authentication for the REST API (requires `ssl_https`) |
| `ssl_generate_certs` | `true` | Generate self-signed certificates using keytool |
| `ssl_cert_validity_days` | `3650` | Certificate validity period in days |
| `ssl_key_algorithm` | `RSA` | Key algorithm for certificate generation |
| `ssl_key_size` | `2048` | Key size in bits |
| `ssl_cert_ou` | `LINSTOR` | Organizational unit for the certificate DN |
| `ssl_cert_o` | `""` | Organization for the certificate DN |
| `ssl_cert_c` | `""` | Country code for the certificate DN |
| `ssl_dir` | `/etc/linstor/ssl` | Directory for SSL keystores and certificates |
| `ssl_keystore_password` | `linstor` | Password for Java keystores (use Ansible Vault for production) |
| `ssl_truststore_password` | `linstor` | Password for Java truststores (use Ansible Vault for production) |
| `ssl_key_password` | `linstor` | Password for private keys (use Ansible Vault for production) |
| `ssl_https_port` | `3371` | HTTPS port for the LINSTOR REST API |
| `ssl_satellite_port` | `3367` | SSL port for satellite communication |
| `ssl_satellite_protocol` | `TLSv1.3` | TLS protocol version for satellite SSL |
Firewall ports 3370-3371 (controller) and 3366-3367 (satellite) are managed by the `controller_install` and `satellite_install` roles respectively.

Dependencies
------------

None.

This role should run after `controller_install` and `satellite_install` (services must be installed) and before `cluster_membership` (nodes must be registered with the correct `com_type`).

When used through `cluster_init`, ordering is handled automatically.

Example Playbook
----------------

Enable SSL through `cluster_init` (encrypts both REST API and satellite connections):

```yaml
- name: Deploy LINSTOR
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install and initialize LINSTOR
      ansible.builtin.import_role:
        name: linbit.linstor.cluster_init
      vars:
        cluster_init_ssl: true
```

Use the role standalone (after controller and satellite are installed):

```yaml
- name: Configure LINSTOR SSL
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Configure SSL/TLS
      ansible.builtin.import_role:
        name: linbit.linstor.ssl
      vars:
        ssl_https: true
        ssl_satellite: true
```

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
