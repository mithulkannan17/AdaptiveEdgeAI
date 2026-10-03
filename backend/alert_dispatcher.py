"""
AuraForest — Local Emergency Alert Notification Dispatcher.

Handles multi-channel emergency alert generation, local beacon dispatch,
webhook broadcasting, and ranger dispatch logging for critical threats.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen

logger = logging.getLogger("auraforest.alert_dispatcher")


class EmergencyAlertDispatcher:
    """
    Emergency Alert Dispatcher for high-risk environmental threats.
    """

    def __init__(
        self,
        database: Optional[Any] = None,
        webhook_urls: Optional[List[str]] = None,
        ntfy_topic: Optional[str] = None,
    ):
        self.database = database
        self.webhook_urls = webhook_urls or []
        env_webhook = os.getenv("EMERGENCY_WEBHOOK_URL")
        if env_webhook and env_webhook not in self.webhook_urls:
            self.webhook_urls.append(env_webhook)
        self.ntfy_topic = ntfy_topic or os.getenv("EMERGENCY_NTFY_TOPIC", "auraforest-alerts")

    @staticmethod
    def get_threat_tier_info(threat_type: str) -> Dict[str, Any]:
        """
        Map threat category to operational priority tier:
        - Fire -> HIGH (Highest Priority)
        - Logging (Chainsaw, Drill) -> HIGH (Highest Priority)
        - Vehicles -> MODERATE (Need to be Addressed)
        - Human -> MODERATE (Need to be Addressed)
        - Others -> LOW
        """
        t = threat_type.lower()
        if any(k in t for k in ["fire", "smoke", "burn", "flame"]):
            return {
                "category": "FIRE",
                "tier": "HIGH (HIGHEST PRIORITY)",
                "default_risk": "CRITICAL",
                "default_action": "DISPATCH_RANGERS",
            }
        if any(k in t for k in ["chainsaw", "drill", "jackhammer", "logging", "saw"]):
            return {
                "category": "LOGGING",
                "tier": "HIGH (HIGHEST PRIORITY)",
                "default_risk": "CRITICAL",
                "default_action": "DISPATCH_RANGERS",
            }
        if any(k in t for k in ["gunshot", "explosion", "blast", "poaching"]):
            return {
                "category": "POACHING/GUNSHOT",
                "tier": "HIGH (HIGHEST PRIORITY)",
                "default_risk": "CRITICAL",
                "default_action": "DISPATCH_RANGERS",
            }
        if any(k in t for k in ["vehicle", "truck", "car", "engine", "motor", "emergencyvehicle"]):
            return {
                "category": "VEHICLES",
                "tier": "MODERATE (NEED TO BE ADDRESSED)",
                "default_risk": "HIGH",
                "default_action": "INTERCEPT_VEHICLE",
            }
        if any(k in t for k in ["human", "speech", "footsteps", "intrusion", "voice"]):
            return {
                "category": "HUMAN",
                "tier": "MODERATE (NEED TO BE ADDRESSED)",
                "default_risk": "HIGH",
                "default_action": "INVESTIGATE_INTRUSION",
            }
        return {
            "category": "OTHERS",
            "tier": "LOW",
            "default_risk": "LOW",
            "default_action": "MONITOR",
        }

    def should_trigger_emergency(
        self,
        prediction: Dict[str, Any],
        cadie_decision: Dict[str, Any],
    ) -> bool:
        """
        Evaluate if an event warrants an emergency alert.
        Emergency alerts & audible sirens trigger ONLY on confirmed high-priority threats:
        - Fire & Logging & Gunshots (Critical Priority): triggers at >= 0.70 confidence
        - Unauthorized Vehicles & Human Intrusion: triggers at >= 0.78 confidence + HIGH/CRITICAL CADIE risk
        - Benign sounds (Birds, Insects, Wildlife, Water, Wind, Rain, Ambient, Silence, Unknown) NEVER trigger emergency sirens.
        """
        risk = str(cadie_decision.get("risk_level", "")).upper()
        requires_attention = bool(cadie_decision.get("requires_attention", False))
        label = str(prediction.get("label", "")).strip().lower()
        confidence = float(prediction.get("confidence", 0.0))

        # 0. Strict filter for benign / non-threat classes
        benign_classes = {
            "bird", "birds", "chirp", "tweet", "wildlife", "animal", "dog", "cat",
            "insects", "insect", "cricket", "cicada", "bee",
            "water", "river", "stream", "ocean", "waves", "waterfall",
            "wind", "breeze", "rain", "thunderstorm", "thunder",
            "ambient", "silence", "unknown", "background", "none"
        }
        if label in benign_classes or any(b in label for b in ["bird", "insect", "water", "wind", "rain", "ambient", "silence"]):
            return False

        # 1. Fire, Logging & Poaching/Gunshot (Critical / Highest Priority)
        high_threat_keywords = ["fire", "wildfire", "chainsaw", "drill", "jackhammer", "gunshot", "explosion", "poaching", "logging"]
        if any(t in label for t in high_threat_keywords) and confidence >= 0.70:
            return True

        # 2. Heavy Vehicles & Human Intrusion (Moderate Priority - requires corroboration)
        moderate_threat_keywords = ["vehicle", "truck", "car", "engine", "motorcycle", "human", "footsteps", "intrusion"]
        if any(t in label for t in moderate_threat_keywords):
            if confidence >= 0.78 and (risk in {"CRITICAL", "HIGH"} or requires_attention):
                return True

        # 3. Emergency Vehicles (Siren detection) - triggers only if high confidence and CADIE validated
        if "emergencyvehicle" in label or "siren" in label:
            if confidence >= 0.82 and risk in {"CRITICAL", "HIGH"}:
                return True

        # 4. CADIE Critical Risk override (Only for unmapped critical threats with >= 0.85 confidence)
        if risk == "CRITICAL" and confidence >= 0.85 and not any(b in label for b in benign_classes):
            return True

        return False

    def create_alert_payload(
        self,
        device_id: str,
        threat_type: str,
        confidence: float,
        risk_level: str,
        location: Dict[str, Any],
        decision: Dict[str, Any],
        contributing_factors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Format an emergency notification payload."""
        alert_id = f"alert-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        now_ts = time.time()
        now_iso = datetime.utcnow().isoformat() + "Z"

        tier_info = self.get_threat_tier_info(threat_type)
        category = tier_info["category"]
        tier = tier_info["tier"]

        lat = location.get("latitude")
        lon = location.get("longitude")
        lat_str = f"{lat:.5f}°N" if lat is not None else "Unknown Lat"
        lon_str = f"{lon:.5f}°E" if lon is not None else "Unknown Lon"

        action = decision.get("recommended_action") or decision.get("action") or tier_info["default_action"]
        factors = contributing_factors or decision.get("contributing_factors") or []

        # Construct human-readable emergency message
        msg_lines = [
            f"🚨 LOCAL EMERGENCY ALERT: {threat_type.upper()} DETECTED",
            f"• Priority Tier: {tier} (Confidence: {confidence * 100:.1f}%)",
            f"• Location: {lat_str}, {lon_str} (Device: {device_id})",
            f"• Recommended Action: {action}",
        ]
        if factors:
            msg_lines.append(f"• Evidence Factors: {', '.join(factors[:3])}")

        message = "\n".join(msg_lines)

        channels = ["LOCAL_DEVICE_STROBE", "DASHBOARD_LIVE_CONSOLE"]
        if self.ntfy_topic:
            channels.append("MOBILE_PHONE_PUSH_NTFY")
        if self.webhook_urls:
            channels.append("REST_WEBHOOK_DISPATCH")
        channels.append("RANGER_HOTLINE_BROADCAST")

        return {
            "alert_id": alert_id,
            "device_id": device_id,
            "timestamp": now_ts,
            "created_at": now_iso,
            "threat_type": threat_type,
            "threat_category": category,
            "priority_tier": tier,
            "confidence": float(confidence),
            "risk_level": risk_level,
            "location": location,
            "location_lat": lat,
            "location_lon": lon,
            "decision": decision,
            "channels": channels,
            "message": message,
            "status": "DISPATCHED",
            "acknowledged_at": None,
            "acknowledged_by": None,
        }

    def dispatch_alert(self, alert_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast alert to all local notification sinks, phone push, and database."""
        alert_id = alert_payload["alert_id"]
        threat = alert_payload.get("threat_type", "Threat").upper()
        conf = float(alert_payload.get("confidence", 0.95)) * 100
        logger.warning(
            f"[EMERGENCY ALERT] Dispatching {alert_id}: {threat} at {alert_payload.get('location')}"
        )

        # 1. Save to SQLite database if available
        if self.database is not None:
            try:
                self.database.insert_emergency_alert(alert_payload)
            except Exception as e:
                logger.error(f"Failed to persist alert in database: {e}")

        webhook_results = []

        # 2. Dispatch to Mobile Phone Notification Bar via ntfy
        if self.ntfy_topic:
            try:
                ntfy_url = f"https://ntfy.sh/{self.ntfy_topic}"
                dash_url = os.getenv("DASHBOARD_URL", "https://auraforest-sentinel.streamlit.app/")
                req = Request(
                    ntfy_url,
                    data=alert_payload.get("message", "Emergency Alert").encode("utf-8"),
                    headers={
                        "Title": f"🚨 EMERGENCY: {threat} ({conf:.1f}%)",
                        "Priority": "5",  # Maximum priority for instant phone notification bar pop-up & chime
                        "Tags": "rotating_light,warning,sos",
                        "Click": dash_url,
                        "User-Agent": "AuraForest-PhonePush/1.0",
                    },
                    method="POST",
                )
                with urlopen(req, timeout=3.0) as resp:
                    webhook_results.append({
                        "channel": "MOBILE_PHONE_PUSH_NTFY",
                        "topic": self.ntfy_topic,
                        "status": resp.status,
                    })
            except Exception as e:
                logger.debug(f"Mobile push notification delivery notice: {e}")
                webhook_results.append({
                    "channel": "MOBILE_PHONE_PUSH_NTFY",
                    "topic": self.ntfy_topic,
                    "error": str(e),
                })

        # 3. Dispatch to external webhooks if configured
        for url in self.webhook_urls:
            try:
                req = Request(
                    url,
                    data=json.dumps(alert_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json", "User-Agent": "AuraForest-Alert/1.0"},
                    method="POST",
                )
                with urlopen(req, timeout=3.0) as resp:
                    webhook_results.append({"url": url, "status": resp.status})
            except Exception as e:
                webhook_results.append({"url": url, "error": str(e)})

        alert_payload["webhook_results"] = webhook_results
        return alert_payload
