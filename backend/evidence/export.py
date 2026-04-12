"""
Case bundle export — generates a ZIP with evidence, manifest, custody trail and verify script.
"""
import io
import json
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlmodel import Session, select, col

from config import settings
from database import engine, Message, EvidenceManifest, write_audit_log
from evidence.chain_of_custody import format_custody_text

VERIFY_SCRIPT = '''#!/usr/bin/env python3
"""
GhostExodus Evidence Verification Script
Independently verify SHA-256 hashes without the GhostExodus system.
"""
import hashlib
import json
import sys
from pathlib import Path

def verify_bundle(bundle_dir: str):
    bundle = Path(bundle_dir)
    manifest_path = bundle / "manifest.json"
    if not manifest_path.exists():
        print("ERROR: manifest.json not found")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    pass_count = 0
    fail_count = 0
    for item in manifest.get("evidence_items", []):
        rel_path = item.get("file_path_relative")
        if not rel_path:
            continue
        full_path = bundle / rel_path
        if not full_path.exists():
            print(f"MISSING: {rel_path}")
            fail_count += 1
            continue
        with open(full_path, "rb") as f:
            computed = hashlib.sha256(f.read()).hexdigest()
        stored = item.get("sha256_hash")
        if computed == stored:
            print(f"VERIFIED: {rel_path}")
            pass_count += 1
        else:
            print(f"TAMPERED: {rel_path}")
            print(f"  Stored:   {stored}")
            print(f"  Computed: {computed}")
            fail_count += 1

    print(f"\\nResult: {pass_count} verified, {fail_count} failed")
    sys.exit(0 if fail_count == 0 else 1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python verification_script.py <bundle_directory>")
        sys.exit(1)
    verify_bundle(sys.argv[1])
'''


async def generate_case_bundle(
    case_reference: str,
    message_ids: list[int],
    user_id: Optional[int] = None,
) -> bytes:
    """
    Generate a ZIP case bundle for the given message IDs.
    Returns raw ZIP bytes.
    """
    buf = io.BytesIO()

    with Session(engine) as session:
        messages = session.exec(
            select(Message).where(col(Message.id).in_(message_ids))
        ).all()
        manifests = session.exec(
            select(EvidenceManifest).where(
                col(EvidenceManifest.message_id).in_(message_ids)
            )
        ).all()

        manifest_data = {
            "case_reference": case_reference,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "message_count": len(messages),
            "evidence_items": [],
        }

        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Add message JSON files
            for m in manifests:
                file_path = Path(m.file_path)
                if file_path.exists():
                    rel = f"messages/{file_path.name}"
                    zf.write(str(file_path), rel)
                    manifest_data["evidence_items"].append({
                        "message_id": m.message_id,
                        "file_path_relative": rel,
                        "sha256_hash": m.sha256_hash,
                        "captured_at_utc": m.captured_at_utc.isoformat(),
                        "capture_method": m.capture_method,
                    })
                    m.exported_in_bundle = True
                    session.add(m)

                # Include media if present
                msg = next((msg for msg in messages if msg.id == m.message_id), None)
                if msg and msg.media_path:
                    media_path = Path(msg.media_path)
                    if media_path.exists():
                        rel_media = f"media/{media_path.name}"
                        zf.write(str(media_path), rel_media)

            # manifest.json
            zf.writestr("manifest.json", json.dumps(manifest_data, indent=2))

            # chain_of_custody.txt
            custody_text = format_custody_text(message_ids, case_reference)
            zf.writestr("chain_of_custody.txt", custody_text)

            # verification_script.py
            zf.writestr("verification_script.py", VERIFY_SCRIPT)

        session.commit()

        write_audit_log(
            session,
            action="EVIDENCE_EXPORT",
            user_id=user_id,
            target_type="CASE_BUNDLE",
            target_id=case_reference,
            detail={
                "case_reference": case_reference,
                "message_ids": message_ids,
                "item_count": len(manifest_data["evidence_items"]),
            },
        )

    return buf.getvalue()
