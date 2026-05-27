## Certificates (Local Root CA with mkcert)

This project uses mkcert to generate and trust a local Root Certificate Authority (CA) for HTTPS testing in a local environment.

### Automated (recommended)

Run `certs.ps1` from the BUIZZ root. It installs mkcert automatically (via winget or Chocolatey), registers the root CA, generates all required certificates, and copies them to the correct server directories in one step:

```powershell
PowerShell -ExecutionPolicy Bypass -File ..\certs.ps1
```

### Manual

1. Install and initialize mkcert — creates a local Root CA and installs it into the system trust store:

```bash
mkcert -install
```

You can locate the CA directory with:
```bash
mkcert -CAROOT
```

2. Add the Root CA to the Windows trust store explicitly:

```bash
certutil -addstore Root rootCA.pem
```

3. Generate certificates for each server group and copy the resulting `.pem` / `-key.pem` files to the `nginx/certs/` or `corpus/certs/` directory of each affected server (see `certs.ps1` for the exact mapping).

After this step, all certificates signed by the mkcert Root CA will be treated as trusted, allowing HTTPS connections without browser security warnings.