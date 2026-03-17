ssl_init
========

Configure SSL/TLS for LINSTOR REST API and satellite connections.

This role automates the full certificate lifecycle and LINSTOR configuration for two independently toggleable features:
REST API HTTPS (controller serves HTTPS on port 3371) and satellite SSL (controller-to-satellite mutual TLS on port 3367).
An optional third feature, REST API mTLS, adds client certificate authentication on top of HTTPS.

The role generates a private CA, signs per-node certificates with Subject Alternative Names (SANs), converts them to Java keystores for LINSTOR's Java components, and installs the CA certificate into the operating system trust store.
This CA-based approach ensures that all clients (Java, Python, Go, Perl) trust the LINSTOR certificates without manual trust store configuration.
After the role completes, `linstor-client.conf` is updated with the `linstors://` scheme so that subsequent module calls (for example `cluster_membership`) connect over HTTPS.

Requirements
------------

The following inventory groups must be defined:

- `linstor_controllers`: nodes running the LINSTOR controller
- `linstor_satellites`: nodes running the LINSTOR satellite

`openssl` must be available on all cluster nodes for certificate generation.

Java `keytool` must be available on all cluster nodes (installed by the `linstor-controller` and `linstor-satellite` packages) for JKS keystore conversion.

Role Variables
--------------

| Variable | Default | Description |
|---|---|---|
| `ssl_init_https` | `true` | Enable HTTPS on the LINSTOR REST API (port 3371) |
| `ssl_init_satellite` | `true` | Enable SSL for controller-to-satellite communication (port 3367) |
| `ssl_init_https_mtls` | `false` | Enable client certificate authentication for the REST API (requires `ssl_init_https`) |
| `ssl_init_generate_certs` | `true` | Generate a private CA and sign per-node certificates |
| `ssl_init_ca_name` | `LINSTOR CA` | Common name for the private CA certificate |
| `ssl_init_ca_validity_days` | `3650` | Validity period in days for the CA certificate |
| `ssl_init_cert_validity_days` | `3650` | Validity period in days for node and client certificates |
| `ssl_init_key_algorithm` | `RSA` | Key algorithm for certificate generation |
| `ssl_init_key_size` | `4096` | Key size in bits for all keys (CA, node, client) |
| `ssl_init_cert_ou` | `{{ linstor_hostname }}` | Organizational unit for the certificate DN |
| `ssl_init_cert_o` | `""` | Organization for the certificate DN |
| `ssl_init_cert_c` | `""` | Country code for the certificate DN |
| `ssl_init_dir` | `/etc/linstor/ssl` | Directory for SSL keystores and certificates |
| `ssl_init_keystore_password` | `linstor` | Password for Java keystores (use Ansible Vault for production) |
| `ssl_init_truststore_password` | `linstor` | Password for Java truststores (use Ansible Vault for production) |
| `ssl_init_key_password` | `linstor` | Password for private keys in TOML configuration (use Ansible Vault for production) |
| `ssl_init_https_port` | `3371` | HTTPS port for the LINSTOR REST API |
| `ssl_init_satellite_port` | `3367` | SSL port for satellite communication |
| `ssl_init_satellite_protocol` | `TLSv1.3` | TLS protocol version for satellite SSL |

Firewall ports 3370-3371 (controller) and 3366-3367 (satellite) are managed by the `controller_install` and `satellite_install` roles respectively.

### Certificate files

When `ssl_init_generate_certs` is true, the role creates the following files in `ssl_init_dir` on each node:

| File | Purpose |
|---|---|
| `ca.crt` | CA certificate (all nodes) |
| `ca.key` | CA private key (first controller only) |
| `node.key` | Node private key |
| `node.crt` | CA-signed node certificate with SANs |
| `keystore.jks` | Java keystore containing node key and certificate |
| `certificates.jks` | Java truststore containing the CA certificate |

The CA certificate is also installed into the operating system trust store:

- Debian/Ubuntu: `/usr/local/share/ca-certificates/linstor-ca.crt`
- RedHat: `/etc/pki/ca-trust/source/anchors/linstor-ca.crt`
- SUSE: `/etc/pki/trust/anchors/linstor-ca.crt`

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
        name: linbit.linstor.ssl_init
```

### Adding a new node

When adding a node to an existing CA-secured cluster, run the role again.
The CA certificate and key persist on the first controller.
The role signs a new certificate for the new node without affecting existing nodes.

License
-------

MIT

Author Information
------------------

[LINBIT](https://linbit.com)
