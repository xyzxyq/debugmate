# 04-05 Independent Security Review Remediation

## Scope

This addendum closes the five blocking findings raised during independent
review of Plan 04-05.  It records the implemented control and the regression
that proves the former attack path cannot pass silently.

| Finding | Implemented control | Regression evidence |
|---|---|---|
| Candidate object mutation can change published fields | The consistency gate creates a private, immutable `_CandidateSnapshot` behind an RLock and weak identity registry.  Publisher checkout is atomic and consumes that snapshot, never public dataclass attributes. | `test_gate_issued_candidate_has_a_private_immutable_business_snapshot`, `test_gate_rejects_copied_or_concurrently_checked_out_candidate`, and `test_publisher_requires_factory_issued_root_and_private_candidate_snapshot` |
| `LoadedDiagnosisSource.model_copy()` can forge a source revision | Loader records exact canonical source/outcome bytes, evidence root and a private proof for only its return object.  Presentation binds that proof; gate performs a fresh Phase 3 `load_verified_outcome` replay and rejects any copied, constructed or mutated source. | `test_gate_rejects_source_revision_model_copy_before_any_publication` |
| Raw result root and mkdir race allow reparse redirection | `TrustedResultRoot` is factory-issued and registry-backed.  The publisher holds Windows no-delete leases for parent/root/case/temp, rechecks each creation and removes a hostile junction/symlink itself without traversal. | `test_publisher_requires_factory_issued_root_and_private_candidate_snapshot`, `test_temp_directory_reparse_race_never_writes_external_target` |
| Download resolver returns a TOCTOU-prone path | `resolve_verified_download` rereads the verified member through a bounded descriptor, checks identity/size/hash while reading, then issues a noncopyable, nonserializable, one-shot `VerifiedDownload` byte capability. | `test_download_is_opaque_one_shot_bytes_not_a_reopenable_path` plus existing swap/symlink tests |
| ZIP verifier can decompress before enforcing bomb policy | Archive verification validates all `ZipInfo` names, count, duplicates, flags, fixed metadata, compressed/uncompressed caps and ratio before opening a member.  Payloads then use bounded streaming CRC/hash checks; `testzip()` is never called. | `test_zip_bomb_metadata_rejects_before_any_member_open` |

## Citation proof on disk

`citations.json` is no longer treated as merely typed metadata.  The public
verifier reconstructs every row from the manifest-hashed `diagnosis.json`:
evidence ID, source URL/locator/chunk/build, supported facts and grounded
candidate relationships must all match exactly.  The narrow source summary
remains identity/facts-revision proof; the diagnosis support graph is the
authoritative claim proof.

Regression: `test_disk_verifier_rederives_citation_url_and_support_graph`
rewrites a canonical, rehashed citation URL and an equivalently updated record;
the verifier rejects it because the diagnosis source graph does not authorize
the new value.

## Verification record

- Result suite: `187 passed, 5 deselected`.
- Full offline suite: `659 passed, 27 deselected`.
- Ruff (changed result modules/tests), `pip check`, and `git diff --check`:
  passed.

No Phase 3 evidence bundle or Phase 4 audio fail-closed behavior was modified.
