#!/usr/bin/env python3
"""
Debug script to verify Globus authentication and get client identity.
Run this to find the identity UUID that needs ACL permissions.
"""

import os
from dotenv import load_dotenv
from globus_sdk import (
    ConfidentialAppAuthClient,
    TransferClient,
    ClientCredentialsAuthorizer,
)

load_dotenv()

def main():
    client_id = os.getenv("GLOBUS_CLIENT_ID")
    client_secret = os.getenv("GLOBUS_CLIENT_SECRET")
    endpoint_id = os.getenv("GLOBUS_ENDPOINT_ID")

    if not client_id or not client_secret:
        print("❌ GLOBUS_CLIENT_ID and GLOBUS_CLIENT_SECRET must be set in .env")
        return

    print(f"📋 Client ID: {client_id}")
    print(f"📋 Endpoint ID: {endpoint_id}\n")

    # Authenticate
    auth_client = ConfidentialAppAuthClient(
        client_id=client_id,
        client_secret=client_secret,
    )

    scopes = "urn:globus:auth:scope:transfer.api.globus.org:all"
    cc_authorizer = ClientCredentialsAuthorizer(auth_client, scopes)
    transfer_client = TransferClient(authorizer=cc_authorizer)

    print("✅ Successfully authenticated with Globus\n")

    # Get endpoint info
    try:
        endpoint = transfer_client.get_endpoint(endpoint_id)
        print("📁 Endpoint Information:")
        print(f"   Name: {endpoint['display_name']}")
        print(f"   Owner: {endpoint.get('owner_string', 'N/A')}")
        print(f"   Type: {endpoint.get('entity_type', 'N/A')}")
        print(f"   Activated: {endpoint.get('activated', False)}")
        print()
    except Exception as e:
        print(f"⚠️  Could not get endpoint info: {e}\n")

    # Try to get endpoint ACL
    try:
        print("🔐 Checking endpoint ACL rules...")
        acl_list = transfer_client.endpoint_acl_list(endpoint_id)

        if acl_list.data:
            print(f"   Found {len(acl_list.data)} ACL rules:")
            for acl in acl_list.data:
                print(f"   - Principal: {acl.get('principal', 'N/A')}")
                print(f"     Path: {acl.get('path', '/')}")
                print(f"     Permissions: {acl.get('permissions', 'N/A')}")
                print()
        else:
            print("   ⚠️  No ACL rules found (this is likely the problem!)")
        print()
    except Exception as e:
        print(f"   ⚠️  Could not retrieve ACLs: {e}\n")

    # Test path access
    test_path = "/archive/packages/2025-10/test/"
    print(f"🧪 Testing access to: {test_path}")
    try:
        result = transfer_client.operation_stat(endpoint_id, path=test_path)
        print("   ✅ Success! Path exists and is accessible")
        print(f"   Type: {result.get('type')}")
    except Exception as e:
        print(f"   ❌ Access denied: {e}")
        print("\n💡 Action Required:")
        print(f"   Add an ACL rule to endpoint '{endpoint_id}' with:")
        print(f"   - Principal: {client_id}")
        print("   - Path: /archive/ (or /)")
        print("   - Permissions: read, write")

    print("\n" + "="*60)
    print("Next Steps:")
    print("="*60)
    print("1. Go to: https://app.globus.org/file-manager")
    print("2. Find your endpoint in 'Collections'")
    print("3. Click 'Open in File Manager' → 'Sharing' tab")
    print("4. Add permission with:")
    print(f"   - Identity/Group: {client_id}")
    print("   - Path: /archive/")
    print("   - Permissions: read + write")
    print("\n   OR use the endpoint owner account to run:")
    print("   globus endpoint permission create \\")
    print(f"     --identity {client_id} \\")
    print("     --permissions rw \\")
    print("     --path /archive/ \\")
    print(f"     {endpoint_id}")

if __name__ == "__main__":
    main()
