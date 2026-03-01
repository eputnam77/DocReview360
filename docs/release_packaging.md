# Release Packaging

This guide covers supply-chain packaging steps for DocReview360 release artifacts.

## Docker OCI metadata labels

The `Dockerfile` includes OCI labels using these build args:

- `VERSION`
- `VCS_REF`
- `BUILD_DATE`
- `IMAGE_SOURCE`
- `IMAGE_URL`

Example build:

```bash
docker build \
  --build-arg VERSION=0.1.2 \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  -t ghcr.io/<org>/docreview360:0.1.2 .
```

## Publish container digest in release notes

After pushing images, capture the immutable digest and generate release notes:

```bash
python scripts/generate_release_notes.py \
  --version 0.1.2 \
  --image-digest ghcr.io/<org>/docreview360@sha256:<digest>
```

The script writes `dist/release/RELEASE_NOTES.md` by default and includes each provided digest in the "Container Images" section.

## Sign and verify release tags

Create a signed annotated tag (GPG):

```bash
python scripts/sign_release_tag.py \
  --tag v0.1.2 \
  --message "DocReview360 v0.1.2"
```

(Optional) sign with an explicit key id:

```bash
python scripts/sign_release_tag.py \
  --tag v0.1.2 \
  --message "DocReview360 v0.1.2" \
  --key-id <GPG_KEY_ID>
```

Verify the signature before publishing release assets:

```bash
python scripts/verify_release_tag_signature.py --tag v0.1.2
```

Sigstore users can substitute an equivalent tag-signing + verification process, but signature verification must be run before publishing.
