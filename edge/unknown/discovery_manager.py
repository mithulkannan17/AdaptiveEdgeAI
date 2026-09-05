"""
Unknown Sound Intelligence Manager

Open-set unknown-sound discovery pipeline:

    model probabilities
        -> unknown detector
        -> embedding extraction
        -> pending buffer
        -> DBSCAN clustering
        -> persistent cluster records
        -> human/manual labeling

The classifier is never retrained automatically.  A cluster label is
human metadata until a future model-training workflow explicitly uses it.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import torch

from edge.unknown.clusterer import ClusterResult, UnknownClusterer
from edge.unknown.embedding_extractor import EmbeddingExtractor
from edge.unknown.unknown_buffer import UnknownBuffer, UnknownSample
from edge.unknown.unknown_detector import UnknownDecision, UnknownDetector


@dataclass
class ClusterSampleRecord:
    """Human-reviewable metadata for one acoustic observation."""

    sample_id: str
    cluster_id: str
    captured_at: float
    predicted_class: int
    confidence: float
    audio_path: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ClusterRecord:
    """Persistent human-reviewable representation of one cluster."""

    cluster_id: str
    created_at: float
    updated_at: float
    sample_count: int
    noise_samples: int = 0
    status: str = "UNLABELED"
    label: Optional[str] = None
    notes: str = ""
    source_batch_size: int = 0
    samples: list[ClusterSampleRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["samples"] = [
            sample.to_dict()
            for sample in self.samples
        ]
        return payload


@dataclass
class DiscoveryResult:
    """
    Result returned after processing one prediction.

    ``decision`` describes the open-set gate.  ``reported_label`` is the
    value that should be exposed to the rest of the system when the model
    prediction is rejected as unknown.
    """

    decision: UnknownDecision
    buffered: bool
    buffer_size: int
    clustering_triggered: bool
    cluster_result: Optional[ClusterResult] = None
    cluster_ids: list[str] = field(default_factory=list)
    reported_label: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.to_dict(),
            "buffered": self.buffered,
            "buffer_size": self.buffer_size,
            "clustering_triggered": self.clustering_triggered,
            "cluster_result": (
                self.cluster_result.to_dict()
                if self.cluster_result is not None
                else None
            ),
            "cluster_ids": list(self.cluster_ids),
            "reported_label": self.reported_label,
        }


class UnknownDiscoveryManager:
    """
    Coordinates open-set detection, embeddings, buffering and clustering.

    Important behavior:
      * Unknown observations are buffered.
      * Once ``clustering_batch_size`` is reached, only that oldest batch is
        clustered and removed from the pending buffer.
      * Cluster records remain available for dashboard/manual review.
      * Human labels are persistent when ``state_path`` is supplied.
      * A human label never silently changes the CNN itself.
    """

    def __init__(
        self,
        model,
        device: torch.device,
        confidence_threshold: float = 0.60,
        margin_threshold: float = 0.15,
        buffer_size: int = 500,
        clustering_batch_size: int = 30,
        clusterer: Optional[UnknownClusterer] = None,
        state_path: Optional[str | Path] = None,
    ):
        if clustering_batch_size <= 0:
            raise ValueError("clustering_batch_size must be greater than zero.")

        self.detector = UnknownDetector(
            confidence_threshold=confidence_threshold,
            margin_threshold=margin_threshold,
        )

        self.embedding_extractor = EmbeddingExtractor(
            model=model,
            device=device,
        )

        self.buffer = UnknownBuffer(max_size=buffer_size)

        self.clusterer = clusterer if clusterer is not None else UnknownClusterer()

        self.clustering_batch_size = int(clustering_batch_size)

        self.state_path = (
            Path(state_path)
            if state_path is not None
            else None
        )

        self._clusters: dict[str, ClusterRecord] = {}
        self._total_unknown_samples = 0
        self._total_cluster_runs = 0
        self._last_cluster_result: Optional[ClusterResult] = None
        self._last_cluster_ids: list[str] = []
        self._last_cluster_at: Optional[float] = None
        self._last_decision: Optional[dict] = None

        self._load_state()

    # ==========================================================
    # Processing
    # ==========================================================

    def process(
        self,
        probabilities,
        spectrogram: torch.Tensor,
        audio_path: Optional[str] = None,
        audio_rms: float | None = None,
    ) -> DiscoveryResult:
        """
        Process one model prediction through the open-set pipeline.

        ``audio_rms`` is the measured RMS of the original waveform. It is
        forwarded to ``UnknownDetector`` so effectively silent audio can be
        rejected as Unknown before buffering.
        """

        decision = self.detector.decide(
            probabilities,
            audio_rms=audio_rms,
        )
        self._last_decision = decision.to_dict()

        # Known sound: accept the classifier's result.
        if not decision.is_unknown:
            return DiscoveryResult(
                decision=decision,
                buffered=False,
                buffer_size=self.buffer.size(),
                clustering_triggered=False,
                reported_label=None,
            )

        # Rejected classifier result: extract a representation and retain it.
        embedding = self.embedding_extractor.extract(spectrogram)

        self.buffer.add(
            embedding=embedding,
            predicted_class=decision.predicted_class,
            confidence=decision.confidence,
            audio_path=audio_path,
        )

        self._total_unknown_samples += 1

        should_cluster = self.buffer.is_ready(
            self.clustering_batch_size
        )

        cluster_result = None
        cluster_ids: list[str] = []

        if should_cluster:
            cluster_result, cluster_ids = self.cluster()

        self._save_state()

        return DiscoveryResult(
            decision=decision,
            buffered=True,
            buffer_size=self.buffer.size(),
            clustering_triggered=should_cluster,
            cluster_result=cluster_result,
            cluster_ids=cluster_ids,
            reported_label="Unknown",
        )

    # ==========================================================
    # Clustering
    # ==========================================================

    def cluster(self) -> tuple[ClusterResult, list[str]]:
        """
        Cluster exactly one pending batch.

        Returns:
            (ClusterResult, stable_cluster_ids)
        """

        if not self.buffer.is_ready(self.clustering_batch_size):
            # Keep the public behavior safe for callers that invoke cluster()
            # manually before enough samples are available.
            embeddings = self.buffer.embeddings()
            if embeddings.shape[0] == 0:
                result = ClusterResult(
                    labels=[],
                    number_of_clusters=0,
                    number_of_noise_samples=0,
                    sample_count=0,
                )
                self._last_cluster_result = result
                self._last_cluster_ids = []
                return result, []

            result = self.clusterer.cluster(embeddings)
            self._last_cluster_result = result
            self._last_cluster_ids = []
            return result, []

        batch = self.buffer.pop_batch(self.clustering_batch_size)
        embeddings = torch.stack([sample.embedding for sample in batch])

        result = self.clusterer.cluster(embeddings)

        cluster_ids = self._persist_cluster_batch(batch, result)

        self._total_cluster_runs += 1
        self._last_cluster_result = result
        self._last_cluster_ids = cluster_ids
        self._last_cluster_at = time.time()

        self._save_state()

        return result, cluster_ids

    def _persist_cluster_batch(
        self,
        samples: list[UnknownSample],
        result: ClusterResult,
    ) -> list[str]:
        """
        Convert local DBSCAN IDs into stable application cluster IDs.

        Every non-noise observation receives a persistent sample ID and keeps
        its original audio_path so the dashboard can later play the evidence
        used to discover the cluster.
        """

        now = time.time()
        local_to_stable: dict[int, str] = {}
        stable_ids_in_batch: list[str] = []

        # Map each DBSCAN cluster to one stable application cluster ID.
        for local_label in sorted(
            {label for label in result.labels if label != -1}
        ):
            stable_id = f"CL-{uuid.uuid4().hex[:8].upper()}"
            local_to_stable[local_label] = stable_id

            count = sum(
                1
                for label in result.labels
                if label == local_label
            )

            self._clusters[stable_id] = ClusterRecord(
                cluster_id=stable_id,
                created_at=now,
                updated_at=now,
                sample_count=count,
                noise_samples=0,
                status="UNLABELED",
                source_batch_size=len(samples),
                samples=[],
            )

        # Attach the original evidence to its discovered cluster.
        for sample, local_label in zip(samples, result.labels):
            if local_label == -1:
                continue

            stable_id = local_to_stable[local_label]
            record = self._clusters[stable_id]

            sample_record = ClusterSampleRecord(
                sample_id=f"US-{uuid.uuid4().hex[:10].upper()}",
                cluster_id=stable_id,
                captured_at=float(
                    sample.timestamp if sample.timestamp else now
                ),
                predicted_class=int(sample.predicted_class),
                confidence=float(sample.confidence),
                audio_path=(
                    str(sample.audio_path)
                    if sample.audio_path
                    else None
                ),
            )

            record.samples.append(sample_record)

            if stable_id not in stable_ids_in_batch:
                stable_ids_in_batch.append(stable_id)

        # Keep counts internally consistent even if a custom clusterer returns
        # an unexpected label distribution.
        for stable_id in stable_ids_in_batch:
            record = self._clusters[stable_id]
            record.sample_count = len(record.samples)
            record.updated_at = now

        return stable_ids_in_batch

    # ==========================================================
    # Manual labeling
    # ==========================================================

    def label_cluster(
        self,
        cluster_id: str,
        label: str,
        notes: str = "",
    ) -> dict:
        """
        Apply a human label to a discovered cluster.
        """

        cluster_id = str(cluster_id).strip()
        label = str(label).strip()

        if not cluster_id:
            raise ValueError("cluster_id cannot be empty.")

        if not label:
            raise ValueError("label cannot be empty.")

        record = self._clusters.get(cluster_id)

        if record is None:
            raise KeyError(f"Unknown cluster_id: {cluster_id}")

        record.label = label
        record.notes = str(notes).strip()
        record.status = "LABELED"
        record.updated_at = time.time()

        self._save_state()

        return record.to_dict()

    def unlabel_cluster(self, cluster_id: str) -> dict:
        """Remove a human label while retaining the cluster."""

        record = self._clusters.get(str(cluster_id).strip())

        if record is None:
            raise KeyError(f"Unknown cluster_id: {cluster_id}")

        record.label = None
        record.notes = ""
        record.status = "UNLABELED"
        record.updated_at = time.time()

        self._save_state()

        return record.to_dict()

    # ==========================================================
    # Dashboard/API state
    # ==========================================================

    def status(self) -> dict:
        """Return dashboard-ready discovery state."""

        clusters = [
            record.to_dict()
            for record in sorted(
                self._clusters.values(),
                key=lambda item: item.created_at,
                reverse=True,
            )
        ]

        labeled = sum(
            1 for record in self._clusters.values()
            if record.status == "LABELED"
        )

        unlabeled = len(self._clusters) - labeled

        return {
            "enabled": True,
            "confidence_threshold": self.detector.confidence_threshold,
            "margin_threshold": self.detector.margin_threshold,
            "buffer_size": self.buffer.size(),
            "buffer_capacity": self.buffer.max_size,
            "clustering_batch_size": self.clustering_batch_size,
            "samples_until_clustering": max(
                0,
                self.clustering_batch_size - self.buffer.size(),
            ),
            "total_unknown_samples": self._total_unknown_samples,
            "total_cluster_runs": self._total_cluster_runs,
            "clusters_discovered": len(self._clusters),
            "labeled_clusters": labeled,
            "unlabeled_clusters": unlabeled,
            "last_cluster_at": self._last_cluster_at,
            "last_cluster_ids": list(self._last_cluster_ids),
            "last_cluster_result": (
                self._last_cluster_result.to_dict()
                if self._last_cluster_result is not None
                else None
            ),
            "last_decision": self._last_decision,
            "clusters": clusters,
        }

    def get_clusters(self) -> list[dict]:
        return self.status()["clusters"]

    def get_cluster(self, cluster_id: str) -> Optional[dict]:
        record = self._clusters.get(str(cluster_id).strip())
        return record.to_dict() if record is not None else None

    def get_samples(
        self,
        cluster_id: str,
    ) -> list[dict]:
        """Return human-reviewable sample metadata for one cluster."""
        record = self._clusters.get(str(cluster_id).strip())

        if record is None:
            raise KeyError(f"Unknown cluster_id: {cluster_id}")

        return [
            sample.to_dict()
            for sample in record.samples
        ]

    def get_sample(
        self,
        sample_id: str,
    ) -> Optional[dict]:
        """Return one stored sample record by its stable sample ID."""
        target = str(sample_id).strip()

        if not target:
            return None

        for record in self._clusters.values():
            for sample in record.samples:
                if sample.sample_id == target:
                    return sample.to_dict()

        return None

    # ==========================================================
    # Compatibility helpers
    # ==========================================================

    def clear(self) -> None:
        """Clear pending unknown observations, retaining reviewed clusters."""
        self.buffer.clear()
        self._save_state()

    def buffer_size(self) -> int:
        return self.buffer.size()

    def total_unknown_samples(self) -> int:
        return self._total_unknown_samples

    def get_last_result(self) -> Optional[dict]:
        """
        Return a dashboard/API-friendly snapshot.

        This method intentionally does not expose embeddings.
        """
        return self.status()

    # ==========================================================
    # Persistence
    # ==========================================================

    def _load_state(self) -> None:
        if self.state_path is None or not self.state_path.exists():
            return

        try:
            payload = json.loads(
                self.state_path.read_text(encoding="utf-8")
            )

            self._total_unknown_samples = int(
                payload.get("total_unknown_samples", 0)
            )
            self._total_cluster_runs = int(
                payload.get("total_cluster_runs", 0)
            )
            self._last_cluster_at = payload.get("last_cluster_at")
            self._last_decision = payload.get("last_decision")

            for raw in payload.get("clusters", []):
                record = ClusterRecord(
                    cluster_id=str(raw["cluster_id"]),
                    created_at=float(raw["created_at"]),
                    updated_at=float(raw.get("updated_at", raw["created_at"])),
                    sample_count=int(raw.get("sample_count", 0)),
                    noise_samples=int(raw.get("noise_samples", 0)),
                    status=str(raw.get("status", "UNLABELED")),
                    label=raw.get("label"),
                    notes=str(raw.get("notes", "")),
                    source_batch_size=int(raw.get("source_batch_size", 0)),
                    samples=[
                        ClusterSampleRecord(
                            sample_id=str(
                                sample.get(
                                    "sample_id",
                                    f"US-{uuid.uuid4().hex[:10].upper()}",
                                )
                            ),
                            cluster_id=str(
                                sample.get(
                                    "cluster_id",
                                    raw["cluster_id"],
                                )
                            ),
                            captured_at=float(
                                sample.get(
                                    "captured_at",
                                    raw.get("created_at", time.time()),
                                )
                            ),
                            predicted_class=int(
                                sample.get("predicted_class", -1)
                            ),
                            confidence=float(
                                sample.get("confidence", 0.0)
                            ),
                            audio_path=sample.get("audio_path"),
                        )
                        for sample in raw.get("samples", [])
                        if isinstance(sample, dict)
                    ],
                )

                # Older state files may not contain sample records.
                if record.samples:
                    record.sample_count = len(record.samples)

                self._clusters[record.cluster_id] = record

        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            json.JSONDecodeError,
        ):
            # Corrupt/missing state must not prevent the edge service from
            # starting.  A fresh state will be written on the next update.
            self._clusters = {}

    def _save_state(self) -> None:
        if self.state_path is None:
            return

        try:
            self.state_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            payload = {
                "version": 2,
                "total_unknown_samples": self._total_unknown_samples,
                "total_cluster_runs": self._total_cluster_runs,
                "last_cluster_at": self._last_cluster_at,
                "last_decision": self._last_decision,
                "clusters": [
                    record.to_dict()
                    for record in self._clusters.values()
                ],
            }

            temp_path = self.state_path.with_suffix(
                self.state_path.suffix + ".tmp"
            )

            temp_path.write_text(
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            temp_path.replace(self.state_path)

        except OSError:
            # Discovery must remain non-fatal if persistence is unavailable.
            pass
