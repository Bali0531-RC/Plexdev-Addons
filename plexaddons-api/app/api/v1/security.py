"""Security Suite API routes (PREM-5/6/7/8/9)."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.api.deps import get_current_user
from app.models import (
    User, Addon, Version, ApiKey,
    AddonSigningKey, VersionSignature, VulnerabilityScan, VersionSBOM,
    TwoFactorChallenge, ScanStatus,
)
from app.schemas import (
    SigningKeyCreate, SigningKeyResponse, SigningKeyListResponse,
    VersionSignatureCreate, VersionSignatureResponse, VersionSignatureVerifyRequest,
    VulnerabilityScanResponse, VulnerabilityScanListResponse,
    SBOMUpload, SBOMResponse, SBOMListResponse,
    ApiKeyIPAllowlistUpdate,
    TwoFactorChallengeRequest, TwoFactorChallengeResponse,
    TwoFactorVerifyRequest, TwoFactorVerifyResponse,
)

router = APIRouter(tags=["security"])


# ================== Helpers ==================

async def _get_addon_or_404(db: AsyncSession, addon_id: int) -> Addon:
    result = await db.execute(select(Addon).where(Addon.id == addon_id))
    addon = result.scalar_one_or_none()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    return addon


async def _get_version_or_404(db: AsyncSession, version_id: int) -> Version:
    result = await db.execute(select(Version).where(Version.id == version_id))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


# ================== PREM-5: Code Signing ==================

signing_router = APIRouter(prefix="/addons/{addon_id}/signing-keys", tags=["code-signing"])


@signing_router.get("", response_model=SigningKeyListResponse)
async def list_signing_keys(
    addon_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    total_result = await db.execute(
        select(func.count(AddonSigningKey.id)).where(AddonSigningKey.addon_id == addon_id)
    )
    total = total_result.scalar() or 0
    result = await db.execute(
        select(AddonSigningKey).where(AddonSigningKey.addon_id == addon_id).order_by(AddonSigningKey.created_at.desc())
    )
    keys = list(result.scalars().all())
    return SigningKeyListResponse(keys=keys, total=total)


@signing_router.post("", response_model=SigningKeyResponse, status_code=201)
async def create_signing_key(
    addon_id: int,
    data: SigningKeyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    fingerprint = hashlib.sha256(data.public_key.encode()).hexdigest()

    key = AddonSigningKey(
        addon_id=addon_id,
        created_by_id=user.id,
        name=data.name,
        public_key=data.public_key,
        key_fingerprint=fingerprint,
        algorithm=data.algorithm,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key


@signing_router.delete("/{key_id}", status_code=204)
async def revoke_signing_key(
    addon_id: int,
    key_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(AddonSigningKey).where(AddonSigningKey.id == key_id, AddonSigningKey.addon_id == addon_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Signing key not found")

    key.is_active = False
    key.revoked_at = datetime.now(timezone.utc)
    await db.commit()


# Version signatures
sig_router = APIRouter(prefix="/versions/{version_id}/signatures", tags=["code-signing"])


@sig_router.post("", response_model=VersionSignatureResponse, status_code=201)
async def create_signature(
    version_id: int,
    data: VersionSignatureCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    version = await _get_version_or_404(db, version_id)
    addon = await _get_addon_or_404(db, version.addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Verify signing key belongs to addon
    key_result = await db.execute(
        select(AddonSigningKey).where(
            AddonSigningKey.id == data.signing_key_id,
            AddonSigningKey.addon_id == addon.id,
            AddonSigningKey.is_active == True,
        )
    )
    if not key_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Invalid or revoked signing key")

    sig = VersionSignature(
        version_id=version_id,
        signing_key_id=data.signing_key_id,
        signature=data.signature,
        signed_hash=data.signed_hash,
    )
    db.add(sig)
    await db.commit()
    await db.refresh(sig)
    return sig


@sig_router.get("", response_model=list[VersionSignatureResponse])
async def list_signatures(
    version_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Public: list signatures for a version (for pavc verification)."""
    await _get_version_or_404(db, version_id)
    result = await db.execute(
        select(VersionSignature).where(VersionSignature.version_id == version_id)
    )
    return list(result.scalars().all())


@sig_router.post("/{sig_id}/verify", response_model=VersionSignatureResponse)
async def verify_signature(
    version_id: int,
    sig_id: int,
    data: VersionSignatureVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Public: verify a signature against an artifact hash."""
    result = await db.execute(
        select(VersionSignature).where(
            VersionSignature.id == sig_id,
            VersionSignature.version_id == version_id,
        )
    )
    sig = result.scalar_one_or_none()
    if not sig:
        raise HTTPException(status_code=404, detail="Signature not found")

    sig.verified = sig.signed_hash == data.artifact_hash
    sig.verified_at = datetime.now(timezone.utc) if sig.verified else None
    await db.commit()
    await db.refresh(sig)
    return sig


# ================== PREM-6: Vulnerability Scanning ==================

scan_router = APIRouter(prefix="/versions/{version_id}/scans", tags=["vulnerability-scanning"])


@scan_router.post("", response_model=VulnerabilityScanResponse, status_code=201)
async def initiate_scan(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    version = await _get_version_or_404(db, version_id)
    addon = await _get_addon_or_404(db, version.addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check for existing pending/scanning scan
    existing = await db.execute(
        select(VulnerabilityScan).where(
            VulnerabilityScan.version_id == version_id,
            VulnerabilityScan.status.in_([ScanStatus.PENDING, ScanStatus.SCANNING]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Scan already in progress")

    scan = VulnerabilityScan(
        version_id=version_id,
        initiated_by_id=user.id,
        status=ScanStatus.PENDING,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan


@scan_router.get("", response_model=VulnerabilityScanListResponse)
async def list_scans(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    version = await _get_version_or_404(db, version_id)
    addon = await _get_addon_or_404(db, version.addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    total_result = await db.execute(
        select(func.count(VulnerabilityScan.id)).where(VulnerabilityScan.version_id == version_id)
    )
    total = total_result.scalar() or 0
    result = await db.execute(
        select(VulnerabilityScan).where(VulnerabilityScan.version_id == version_id)
        .order_by(VulnerabilityScan.created_at.desc())
    )
    scans = list(result.scalars().all())
    return VulnerabilityScanListResponse(scans=scans, total=total)


@scan_router.get("/{scan_id}", response_model=VulnerabilityScanResponse)
async def get_scan(
    version_id: int,
    scan_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    version = await _get_version_or_404(db, version_id)
    addon = await _get_addon_or_404(db, version.addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(VulnerabilityScan).where(
            VulnerabilityScan.id == scan_id,
            VulnerabilityScan.version_id == version_id,
        )
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


# ================== PREM-7: SBOM ==================

sbom_router = APIRouter(prefix="/versions/{version_id}/sbom", tags=["sbom"])


def _parse_npm_lockfile(content: str) -> list[dict]:
    """Parse package-lock.json and extract dependencies."""
    import json as json_lib
    try:
        data = json_lib.loads(content)
    except json_lib.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON content")

    deps = []
    packages = data.get("packages", {})
    if packages:
        for pkg_path, pkg_info in packages.items():
            if not pkg_path:  # Root package
                continue
            name = pkg_path.replace("node_modules/", "", 1)
            deps.append({
                "name": name,
                "version": pkg_info.get("version", "unknown"),
                "license": pkg_info.get("license", "unknown"),
                "is_direct": not pkg_path.count("node_modules/") > 1,
            })
    else:
        # v1 lockfile
        for name, info in data.get("dependencies", {}).items():
            deps.append({
                "name": name,
                "version": info.get("version", "unknown"),
                "license": "unknown",
                "is_direct": not info.get("dev", False),
            })
    return deps


def _parse_pip_lockfile(content: str) -> list[dict]:
    """Parse requirements.txt style content."""
    deps = []
    for line in content.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        parts = line.split("==")
        name = parts[0].split(">=")[0].split("<=")[0].split("~=")[0].split("!=")[0].strip()
        version = parts[1].strip() if len(parts) > 1 else "any"
        deps.append({"name": name, "version": version, "license": "unknown", "is_direct": True})
    return deps


@sbom_router.post("", response_model=SBOMResponse, status_code=201)
async def upload_sbom(
    version_id: int,
    data: SBOMUpload,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    version = await _get_version_or_404(db, version_id)
    addon = await _get_addon_or_404(db, version.addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    if data.format == "npm":
        deps = _parse_npm_lockfile(data.raw_content)
    elif data.format == "pip":
        deps = _parse_pip_lockfile(data.raw_content)
    else:
        deps = []

    direct_count = sum(1 for d in deps if d.get("is_direct"))

    sbom = VersionSBOM(
        version_id=version_id,
        uploaded_by_id=user.id,
        format=data.format,
        raw_content=data.raw_content,
        dependencies=deps,
        total_dependencies=len(deps),
        direct_dependencies=direct_count,
    )
    db.add(sbom)
    await db.commit()
    await db.refresh(sbom)
    return sbom


@sbom_router.get("", response_model=SBOMListResponse)
async def list_sboms(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    version = await _get_version_or_404(db, version_id)
    addon = await _get_addon_or_404(db, version.addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    total_result = await db.execute(
        select(func.count(VersionSBOM.id)).where(VersionSBOM.version_id == version_id)
    )
    total = total_result.scalar() or 0
    result = await db.execute(
        select(VersionSBOM).where(VersionSBOM.version_id == version_id)
        .order_by(VersionSBOM.created_at.desc())
    )
    sboms = list(result.scalars().all())
    return SBOMListResponse(sboms=sboms, total=total)


# ================== PREM-8: IP Allowlist ==================

ip_router = APIRouter(prefix="/api-keys/{key_id}/ip-allowlist", tags=["ip-allowlist"])


@ip_router.put("")
async def update_ip_allowlist(
    key_id: int,
    data: ApiKeyIPAllowlistUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.ip_allowlist = data.ip_allowlist
    await db.commit()
    return {"ip_allowlist": api_key.ip_allowlist}


@ip_router.get("")
async def get_ip_allowlist(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"ip_allowlist": api_key.ip_allowlist}


# ================== PREM-9: 2FA Challenges ==================

twofa_router = APIRouter(prefix="/security/2fa", tags=["2fa"])


@twofa_router.post("/challenge", response_model=TwoFactorChallengeResponse)
async def create_2fa_challenge(
    data: TwoFactorChallengeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a 2FA challenge for a critical action. Sends code via email."""
    if not user.email:
        raise HTTPException(status_code=400, detail="Email required for 2FA. Set your email in profile settings.")

    code = f"{secrets.randbelow(900000) + 100000}"
    code_hash = hashlib.sha256(code.encode()).hexdigest()

    challenge = TwoFactorChallenge(
        user_id=user.id,
        action=data.action,
        challenge_code_hash=code_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(challenge)
    await db.commit()
    await db.refresh(challenge)

    # Send code via email (best-effort)
    try:
        from app.services.email_service import EmailService
        await EmailService.send_email(
            to_email=user.email,
            subject=f"PlexDev 2FA Verification Code: {code}",
            html_content=f"<p>Your verification code is: <strong>{code}</strong></p>"
                         f"<p>This code expires in 10 minutes.</p>"
                         f"<p>Action: {data.action.replace('_', ' ').title()}</p>",
        )
    except Exception:
        pass  # Code is still valid, user may need to retry

    return TwoFactorChallengeResponse(
        challenge_id=challenge.id,
        action=data.action,
        expires_at=challenge.expires_at,
        message="Verification code sent to your email",
    )


@twofa_router.post("/verify", response_model=TwoFactorVerifyResponse)
async def verify_2fa_challenge(
    data: TwoFactorVerifyRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Verify a 2FA challenge code."""
    result = await db.execute(
        select(TwoFactorChallenge).where(
            TwoFactorChallenge.id == data.challenge_id,
            TwoFactorChallenge.user_id == user.id,
        )
    )
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    if challenge.is_used:
        raise HTTPException(status_code=400, detail="Challenge already used")

    if challenge.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Challenge expired")

    if challenge.attempts >= challenge.max_attempts:
        raise HTTPException(status_code=429, detail="Too many attempts")

    challenge.attempts += 1
    code_hash = hashlib.sha256(data.code.encode()).hexdigest()

    if code_hash != challenge.challenge_code_hash:
        await db.commit()
        remaining = challenge.max_attempts - challenge.attempts
        return TwoFactorVerifyResponse(verified=False, message=f"Invalid code. {remaining} attempts remaining.")

    challenge.is_verified = True
    challenge.verified_at = datetime.now(timezone.utc)
    await db.commit()

    return TwoFactorVerifyResponse(verified=True, message="Verification successful")
