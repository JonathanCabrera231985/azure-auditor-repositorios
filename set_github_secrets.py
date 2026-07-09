# set_github_secrets.py

import os
import requests
import base64
from nacl import encoding, public

# Define the repository
OWNER = "JonathanCabrera231985"
REPO = "azure-auditor-repositorios"
API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}"

def encrypt(public_key: str, secret_value: str) -> str:
    """Encrypts a string using the repository's public key for GitHub Secrets."""
    public_key_obj = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder)
    sealed_box = public.SealedBox(public_key_obj)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return encoding.Base64Encoder.encode(encrypted).decode("utf-8")

def main():
    print("="*60)
    print("  GitHub Secrets Uploader for Azure DevOps Auditor")
    print("="*60)
    
    # Check if .env file exists
    env_path = ".env"
    if not os.path.exists(env_path):
        print(f"Error: No se encontró el archivo '{env_path}'.")
        return

    # Read .env file manually to keep exact pairs and ignore comments
    secrets_to_upload = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Ignore empty lines and comments
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                # Strip quotes if present
                val = val.strip().strip('"').strip("'")
                secrets_to_upload[key.strip()] = val

    if not secrets_to_upload:
        print("No se encontraron secretos válidos en el archivo .env.")
        return

    print(f"Se detectaron {len(secrets_to_upload)} secreto(s) para cargar:")
    for key in secrets_to_upload:
        print(f" - {key}")
    print()

    # Prompt user for GitHub Token
    github_token = input("Por favor, ingresa tu GitHub Personal Access Token (PAT) con permisos de 'repo': ").strip()
    if not github_token:
        print("El Token de GitHub es obligatorio.")
        return

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    # Step 1: Get the public key of the repository
    print("\nObteniendo la clave pública del repositorio...")
    pubkey_url = f"{API_URL}/actions/secrets/public-key"
    try:
        res = requests.get(pubkey_url, headers=headers)
        if res.status_code == 404:
            print("Error: No se encontró el repositorio o no tienes permisos de acceso.")
            return
        res.raise_for_status()
        pubkey_data = res.json()
        key_id = pubkey_data["key_id"]
        public_key = pubkey_data["key"]
        print("Clave pública obtenida con éxito.")
    except Exception as e:
        print(f"Error al obtener la clave pública: {e}")
        return

    # Step 2: Encrypt and upload each secret
    print("\nCargando secretos a GitHub...")
    success_count = 0
    for name, value in secrets_to_upload.items():
        # Encrypt the value
        try:
            encrypted_value = encrypt(public_key, value)
        except Exception as e:
            print(f"❌ Error al cifrar {name}: {e}")
            continue

        # PUT request to upload the secret
        secret_url = f"{API_URL}/actions/secrets/{name}"
        data = {
            "encrypted_value": encrypted_value,
            "key_id": key_id
        }
        
        try:
            put_res = requests.put(secret_url, headers=headers, json=data)
            if put_res.status_code in [201, 204]:
                print(f"✅ Secreto '{name}' cargado exitosamente.")
                success_count += 1
            else:
                print(f"❌ Falló la carga de '{name}'. Código de estado: {put_res.status_code}. Detalle: {put_res.text}")
        except Exception as e:
            print(f"❌ Error de red al cargar '{name}': {e}")

    print("\n" + "="*60)
    print(f"Proceso finalizado. {success_count} de {len(secrets_to_upload)} secretos cargados con éxito.")
    print("="*60)

if __name__ == "__main__":
    main()
