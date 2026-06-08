# ssl_init

Configure SSL/TLS for LINSTOR REST API and satellite connections.

This role automates the full certificate lifecycle and LINSTOR configuration for two independently toggleable features:
REST API HTTPS (controller serves HTTPS on port 3371) and satellite SSL (controller-to-satellite mutual TLS on port 3367).
An optional third feature, REST API mTLS, adds client certificate authentication on top of HTTPS.

The role generates a private CA, signs per-node certificates with Subject Alternative Names (SANs), converts them to Java keystores for LINSTOR's Java components, and installs the CA certificate into the operating system trust store.
This CA-based approach ensures that all clients (Java, Python, Go, Perl) trust the LINSTOR certificates without manual trust store configuration.
After the role completes, `linstor-client.conf` is updated with the `linstor+ssl://` scheme so that subsequent module calls (for example `cluster_membership`) connect over HTTPS.

## Requirements

The following inventory groups must be defined:

- `linstor_controllers`: nodes running the LINSTOR controller
- `linstor_satellites`: nodes running the LINSTOR satellite

`openssl` must be available on the Ansible control node (for CA and certificate generation) and on all cluster nodes (for PKCS12 keystore conversion).

Java `keytool` must be available on all cluster nodes (installed by the `linstor-controller` and `linstor-satellite` packages) for JKS keystore conversion.

## Role variables

| Variable | Default | Description |
|---|---|---|
| `ssl_init_https` | `true` | Enable HTTPS on the LINSTOR REST API (port 3371) |
| `ssl_init_satellite` | `true` | Enable SSL for controller-to-satellite communication (port 3367) |
| `ssl_init_https_mtls` | `false` | Enable client certificate authentication for the REST API (requires `ssl_init_https`) |
| `ssl_init_generate_certs` | `true` | Generate a private CA and sign per-node certificates |
| `ssl_init_ca_name` | `LINSTOR CA` | Common name for the private CA certificate |
| `ssl_init_ca_validity_days` | `3650` | Validity period in days for the CA certificate |
| `ssl_init_cert_validity_days` | `3650` | Validity period in days for node and client certificates |
| `ssl_init_key_algorithm` | `EC` | Key algorithm: `EC` (ECDSA) or `RSA` |
| `ssl_init_ca_curve` | `secp384r1` | Elliptic curve for the CA key (EC only) |
| `ssl_init_node_curve` | `prime256v1` | Elliptic curve for node and client keys (EC only) |
| `ssl_init_rsa_key_size` | `4096` | Key size in bits for RSA keys (RSA only) |
| `ssl_init_cert_ou` | `{{ inventory_hostname }}` | Organizational unit for the certificate DN |
| `ssl_init_cert_o` | `""` | Organization for the certificate DN |
| `ssl_init_cert_c` | `""` | Country code for the certificate DN |
| `ssl_init_dir` | `/etc/linstor/ssl` | Directory for SSL keystores and certificates on cluster nodes |
| `ssl_init_local_dir` | `~/.config/linstor/ssl` | Directory on the Ansible control node for the CA key, CA cert, and signed per-node certs; persists across runs so new nodes can be signed without touching the cluster |
| `ssl_init_keystore_password` | `linstor` | Password for Java keystores (use Ansible Vault for production) |
| `ssl_init_truststore_password` | `linstor` | Password for Java truststores (use Ansible Vault for production) |
| `ssl_init_key_password` | `linstor` | Password for private keys in TOML configuration (use Ansible Vault for production) |
| `ssl_init_https_port` | `3371` | HTTPS port for the LINSTOR REST API |
| `ssl_init_satellite_port` | `3367` | SSL port for satellite communication |
| `ssl_init_satellite_protocol` | `TLSv1.3` | TLS protocol version for satellite SSL |
| `linstor_api_delegate` | `localhost` | Delegation target for LINSTOR API tasks; override to a cluster node (for example `{{ groups['linstor_controllers'][0] }}`) when the control node cannot reach the controller directly; OpenSSL and keytool tasks always run on the control node regardless |

Firewall ports 3370-3371 (controller) and 3366-3367 (satellite) are managed by the `controller_install` and `satellite_install` roles respectively.

### Certificate files

When `ssl_init_generate_certs` is true, the role creates the following files on the Ansible control node at `ssl_init_local_dir`:

| File | Purpose |
|---|---|
| `ca.key` | CA private key, never distributed to cluster nodes |
| `ca.crt` | CA certificate |
| `<hostname>/node.key` | Per-node private key |
| `<hostname>/node.crt` | CA-signed per-node certificate with SANs |

The following files are pushed to each cluster node at `ssl_init_dir`:

| File | Purpose |
|---|---|
| `ca.crt` | CA certificate |
| `node.key` | Node private key |
| `node.crt` | CA-signed node certificate with SANs |
| `keystore.jks` | Java keystore containing node key and certificate |
| `certificates.jks` | Java truststore containing the CA certificate |

After completing the SSL configuration, `~/.config/linstor/linstor-client.conf` is written on the Ansible control node with the `linstor+ssl://` controller address and `cafile` pointing to `ssl_init_local_dir/ca.crt`.

The CA certificate is also installed into the operating system trust store:

- Debian/Ubuntu: `/usr/local/share/ca-certificates/linstor-ca.crt`
- Red Hat: `/etc/pki/ca-trust/source/anchors/linstor-ca.crt`
- SUSE: `/etc/pki/trust/anchors/linstor-ca.crt`

### Using externally-provided certificates

Set `ssl_init_generate_certs: false` to use certificates from an external CA instead of the built-in private CA.
Place PEM certificate files on each node before running the role.
The role handles JKS keystore conversion, truststore creation, OS trust store installation, and LINSTOR configuration.

#### Required files

Place the following files in `ssl_init_dir` (`/etc/linstor/ssl` by default) on each node:

| File | Purpose |
|---|---|
| `ca.crt` | CA certificate, or full chain (root and intermediates concatenated) |
| `node.crt` | CA-signed node certificate with SANs |
| `node.key` | Node private key |

The role asserts that all three files exist before proceeding.

#### Subject alternative names (SANs)

Request certificates from your CA with the following SANs per node:

- `DNS:<inventory_hostname>` (the LINSTOR node name)
- `DNS:<inventory_hostname_short>` (when the inventory entry is an FQDN)
- `IP:<replication_ip>` (the node's replication network address)
- `IP:127.0.0.1`

Controller certificates need additional SANs:

- `IP:<replication_ip>` for every controller node (so any controller certificate is valid behind a VIP)
- `IP:<linstor_ha_vip>` if using HA database with a virtual IP

These match the SANs that the built-in certificate generation creates automatically.
For complete certificate generation instructions, refer to the SSL/TLS section in the LINSTOR User's Guide.

mTLS client certificate authentication (`ssl_init_https_mtls`) is not supported with external certificates because client certificate signing requires the CA private key.

#### Example playbook

```yaml
- name: Deploy LINSTOR with external certificates
  hosts: linstor_cluster
  any_errors_fatal: true
  become: true
  tasks:
    - name: Install and initialize LINSTOR
      ansible.builtin.import_role:
        name: linbit.linstor.cluster_init
      vars:
        cluster_init_ssl: true
        ssl_init_generate_certs: false
        ssl_init_keystore_password: "{{ vault_ssl_keystore_password }}"
        ssl_init_truststore_password: "{{ vault_ssl_truststore_password }}"
        ssl_init_key_password: "{{ vault_ssl_key_password }}"
```

## Dependencies

None.

This role should run after `controller_install` and `satellite_install` (services must be installed).
The role updates node network interfaces to SSL automatically, so it can run before or after `cluster_membership`.

When used through `cluster_init`, ordering is handled automatically.

## Example playbook

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

### Converting an existing cluster to SSL

Run the role against an existing non-SSL cluster to enable SSL.
The role generates certificates, configures TOML files, updates node network interfaces to SSL, and restarts services.
Use `--limit` for staged rollouts: the role detects which nodes still need SSL and only processes those.

### Adding a new node

When adding a node to an existing CA-secured cluster, run the role again.
The CA key persists on the Ansible control node at `ssl_init_local_dir`.
The role signs a new certificate for the new node without touching any running cluster node or affecting existing nodes.

## License

MIT

## Author information

[LINBIT](https://linbit.com)
