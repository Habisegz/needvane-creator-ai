import hashlib
import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from apps.api.src.models.creator import Creator
from apps.api.src.models.creator_post import CreatorPost
from apps.api.src.models.monitoring_log import CreatorMonitoringLog
from apps.api.src.models.creator_alert import CreatorAlert

def compute_sha256(content: str) -> str:
    """Computes a standardized SHA-256 hash."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two numeric vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 1.0
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)

def generate_pseudo_embedding(text_corpus: str, dim: int = 64) -> List[float]:
    """
    Deterministic semantic hash embedding generator used for theme drift calculations.
    Ensures stable comparisons across test and offline environments.
    """
    words = text_corpus.lower().split()
    vector = [0.0] * dim
    for word in words:
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        for i in range(dim):
            bit = (h >> (i % 32)) & 1
            vector[i] += (1.0 if bit else -1.0)
    norm = math.sqrt(sum(v * v for v in vector))
    if norm > 0:
        vector = [round(v / norm, 5) for v in vector]
    return vector

class CreatorMonitoringEngine:
    """
    Creator Page Monitoring Engine.
    Handles scheduled monitoring, content hashing, deduplication,
    semantic theme shift detection, recurring audience problem tracking,
    and automated alert notifications.
    """

    @staticmethod
    def configure_schedule(
        db: Session,
        creator_id: str,
        tenant_id: str,
        interval: str = "daily",
        status: str = "active",
        custom_interval_hours: int = 24,
        alert_preferences: Optional[Dict[str, bool]] = None
    ) -> Creator:
        creator = db.query(Creator).filter(
            Creator.id == creator_id,
            Creator.tenant_id == tenant_id
        ).first()
        if not creator:
            raise ValueError(f"Creator {creator_id} not found in current tenant workspace.")

        valid_intervals = ["one-time", "daily", "weekly", "custom"]
        if interval not in valid_intervals:
            raise ValueError(f"Invalid interval '{interval}'. Must be one of {valid_intervals}")

        creator.monitoring_interval = interval
        creator.monitoring_status = status
        creator.custom_interval_hours = max(1, custom_interval_hours)

        if alert_preferences is not None:
            current_prefs = dict(creator.alert_preferences or {})
            current_prefs.update(alert_preferences)
            creator.alert_preferences = current_prefs
        elif not creator.alert_preferences:
            creator.alert_preferences = {
                "notify_new_posts": True,
                "notify_theme_shift": True,
                "notify_problem_spike": True,
                "notify_source_unavailable": True
            }

        # Calculate next check due
        now = datetime.now(timezone.utc)
        if status == "active":
            if interval == "daily":
                creator.next_check_due = now + timedelta(days=1)
            elif interval == "weekly":
                creator.next_check_due = now + timedelta(days=7)
            elif interval == "custom":
                creator.next_check_due = now + timedelta(hours=creator.custom_interval_hours)
            elif interval == "one-time":
                creator.next_check_due = now
        else:
            creator.next_check_due = None

        db.commit()
        db.refresh(creator)
        return creator

    @classmethod
    def execute_monitoring_check(
        cls,
        db: Session,
        creator_id: str,
        tenant_id: str,
        incoming_feed: Optional[List[Dict[str, Any]]] = None,
        simulate_error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a monitoring check on a creator page.
        Handles content ingestion, hashing deduplication, semantic shift analysis,
        and alert dispatching.
        """
        creator = db.query(Creator).filter(
            Creator.id == creator_id,
            Creator.tenant_id == tenant_id
        ).first()
        if not creator:
            raise ValueError(f"Creator {creator_id} not found in tenant workspace.")

        now = datetime.now(timezone.utc)
        prefs = creator.alert_preferences or {
            "notify_new_posts": True,
            "notify_theme_shift": True,
            "notify_problem_spike": True,
            "notify_source_unavailable": True
        }

        # 1. Error / Source Unavailable Handling
        if simulate_error:
            creator.last_checked_at = now
            error_log = CreatorMonitoringLog(
                tenant_id=tenant_id,
                creator_id=creator.id,
                checked_at=now,
                status="source_unavailable",
                posts_checked=0,
                new_posts_count=0,
                changes_detected=False,
                summary=f"Monitoring failed: {simulate_error}",
                error_message=simulate_error
            )
            db.add(error_log)

            created_alerts = []
            if prefs.get("notify_source_unavailable", True):
                alert = CreatorAlert(
                    tenant_id=tenant_id,
                    creator_id=creator.id,
                    alert_type="source_unavailable",
                    severity="critical",
                    title=f"Source Unavailable: @{creator.username}",
                    message=f"Monitoring failed for @{creator.username} on {creator.platform}. Error: {simulate_error}",
                    data={"error": simulate_error, "platform": creator.platform}
                )
                db.add(alert)
                created_alerts.append({
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "title": alert.title
                })

            db.commit()
            return {
                "status": "source_unavailable",
                "error": simulate_error,
                "posts_checked": 0,
                "new_posts_count": 0,
                "changes_detected": False,
                "alerts_created": created_alerts
            }

        # 2. Feed Normalization & Mock/Real Retrieval
        if incoming_feed is None:
            # Provide sample recent content if none passed explicitly
            incoming_feed = [
                {
                    "external_post_id": f"post_{creator.username}_{int(now.timestamp())}_1",
                    "platform": creator.platform,
                    "caption": f"Breaking down high-ticket client acquisition systems for 2026. Stop wasting hours on cold calls.",
                    "transcript": "In this video we reveal why outbound email without hyper-personalization fails and how to build warm inbound systems.",
                    "topics": ["client_acquisition", "b2b_sales", "high_ticket"],
                    "recurring_problems": ["Difficulty finding qualified leads", "Low response rates to outreach"],
                    "posted_at": now.isoformat()
                }
            ]

        # 3. Content Hashing & Deduplication
        existing_hashes = set(
            row[0] for row in db.query(CreatorPost.content_hash).filter(
                CreatorPost.creator_id == creator.id,
                CreatorPost.tenant_id == tenant_id
            ).all()
        )

        new_posts: List[CreatorPost] = []
        new_problems: List[str] = []
        all_new_topics: List[str] = []

        for item in incoming_feed:
            ext_id = str(item.get("external_post_id", ""))
            caption = str(item.get("caption", ""))
            transcript = str(item.get("transcript", ""))
            platform = str(item.get("platform", creator.platform))
            topics = item.get("topics", [])
            problems = item.get("recurring_problems", [])

            # Compute unique content hash
            hash_str = f"{platform}:{ext_id}:{caption}:{transcript}"
            content_hash = compute_sha256(hash_str)

            if content_hash in existing_hashes:
                continue  # Deduplicated: identical content already processed

            post_date = now
            if item.get("posted_at"):
                try:
                    post_date = datetime.fromisoformat(item["posted_at"].replace("Z", "+00:00"))
                except Exception:
                    post_date = now

            new_post = CreatorPost(
                tenant_id=tenant_id,
                creator_id=creator.id,
                external_post_id=ext_id,
                platform=platform,
                caption=caption,
                transcript=transcript,
                content_hash=content_hash,
                detected_topics=topics,
                recurring_problems=problems,
                posted_at=post_date
            )
            new_posts.append(new_post)
            existing_hashes.add(content_hash)
            new_problems.extend(problems)
            all_new_topics.extend(topics)

        # 4. Change Detection & Fingerprinting
        changes_detected = len(new_posts) > 0
        sorted_hashes = sorted(list(existing_hashes))
        new_fingerprint = compute_sha256("".join(sorted_hashes)) if sorted_hashes else None

        created_alerts = []

        # 5. Semantic Shift Analysis (Theme Cosine Similarity)
        old_embedding = creator.theme_embedding
        combined_text = " ".join(all_new_topics + new_problems)
        new_embedding = generate_pseudo_embedding(combined_text) if combined_text else old_embedding

        theme_shift_detected = False
        similarity_score = 1.0

        if changes_detected and old_embedding and new_embedding:
            similarity_score = compute_cosine_similarity(old_embedding, new_embedding)
            # If similarity drops below 0.70, it signals a meaningful thematic drift
            if similarity_score < 0.70:
                theme_shift_detected = True
                if prefs.get("notify_theme_shift", True):
                    shift_alert = CreatorAlert(
                        tenant_id=tenant_id,
                        creator_id=creator.id,
                        alert_type="theme_shift",
                        severity="warning",
                        title=f"Thematic Shift Detected: @{creator.username}",
                        message=f"Recent posts by @{creator.username} indicate a content pivot (thematic similarity: {similarity_score * 100:.1f}%). New topics: {', '.join(all_new_topics[:3])}.",
                        data={
                            "similarity_score": round(similarity_score, 4),
                            "previous_themes": creator.theme_summary or [],
                            "new_topics": all_new_topics
                        }
                    )
                    db.add(shift_alert)
                    created_alerts.append({
                        "alert_type": shift_alert.alert_type,
                        "severity": shift_alert.severity,
                        "title": shift_alert.title
                    })

        # 6. New Relevant Post Alerts
        if changes_detected and prefs.get("notify_new_posts", True):
            post_alert = CreatorAlert(
                tenant_id=tenant_id,
                creator_id=creator.id,
                alert_type="new_relevant_post",
                severity="info",
                title=f"New Content Captured: @{creator.username}",
                message=f"Captured {len(new_posts)} new post(s) from @{creator.username} matching monitored criteria.",
                data={"new_posts_count": len(new_posts), "post_ids": [p.external_post_id for p in new_posts]}
            )
            db.add(post_alert)
            created_alerts.append({
                "alert_type": post_alert.alert_type,
                "severity": post_alert.severity,
                "title": post_alert.title
            })

        # 7. Recurring Problem Spike & Emerging Problems Alert
        if new_problems:
            # Check existing problems from historical posts
            historical_posts = db.query(CreatorPost).filter(
                CreatorPost.creator_id == creator.id,
                CreatorPost.tenant_id == tenant_id
            ).all()
            
            problem_freq: Dict[str, int] = {}
            for p in historical_posts:
                for prob in (p.recurring_problems or []):
                    problem_freq[prob] = problem_freq.get(prob, 0) + 1
            for prob in new_problems:
                problem_freq[prob] = problem_freq.get(prob, 0) + 1

            # Detect if any problem reached high recurring count (>= 2)
            spiked_problems = [prob for prob, count in problem_freq.items() if count >= 2]
            if spiked_problems and prefs.get("notify_problem_spike", True):
                spike_alert = CreatorAlert(
                    tenant_id=tenant_id,
                    creator_id=creator.id,
                    alert_type="recurring_problem_spike",
                    severity="warning",
                    title=f"Recurring Audience Problem Spike: @{creator.username}",
                    message=f"Audience recurring complaint '{spiked_problems[0]}' has spiked across {problem_freq[spiked_problems[0]]} posts. Prime opportunity for a targeted guide.",
                    data={"problem": spiked_problems[0], "frequency": problem_freq[spiked_problems[0]]}
                )
                db.add(spike_alert)
                created_alerts.append({
                    "alert_type": spike_alert.alert_type,
                    "severity": spike_alert.severity,
                    "title": spike_alert.title
                })

        # 8. Save New Posts & Update Creator State
        for post in new_posts:
            db.add(post)

        creator.last_checked_at = now
        creator.content_fingerprint = new_fingerprint
        if new_embedding:
            creator.theme_embedding = new_embedding
        if all_new_topics:
            combined_summary = list(set((creator.theme_summary or []) + all_new_topics))
            creator.theme_summary = combined_summary[:10]

        # Calculate next check due
        if creator.monitoring_status == "active":
            if creator.monitoring_interval == "daily":
                creator.next_check_due = now + timedelta(days=1)
            elif creator.monitoring_interval == "weekly":
                creator.next_check_due = now + timedelta(days=7)
            elif creator.monitoring_interval == "custom":
                creator.next_check_due = now + timedelta(hours=creator.custom_interval_hours)
            elif creator.monitoring_interval == "one-time":
                creator.monitoring_status = "paused"
                creator.next_check_due = None

        # 9. Record Monitoring Log Entry
        summary_msg = f"Check completed. {len(incoming_feed)} checked, {len(new_posts)} new posts, {len(created_alerts)} alerts."
        log_entry = CreatorMonitoringLog(
            tenant_id=tenant_id,
            creator_id=creator.id,
            checked_at=now,
            status="success",
            posts_checked=len(incoming_feed),
            new_posts_count=len(new_posts),
            changes_detected=changes_detected,
            summary=summary_msg,
            error_message=None
        )
        db.add(log_entry)

        db.commit()
        db.refresh(creator)

        return {
            "status": "success",
            "posts_checked": len(incoming_feed),
            "new_posts_count": len(new_posts),
            "changes_detected": changes_detected,
            "theme_shift_detected": theme_shift_detected,
            "theme_similarity": round(similarity_score, 4),
            "alerts_created": created_alerts,
            "summary": summary_msg
        }

    @staticmethod
    def get_creator_dashboard(db: Session, creator_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        Gathers comprehensive monitoring dashboard metrics for a creator.
        """
        creator = db.query(Creator).filter(
            Creator.id == creator_id,
            Creator.tenant_id == tenant_id
        ).first()
        if not creator:
            raise ValueError(f"Creator {creator_id} not found in tenant workspace.")

        posts = db.query(CreatorPost).filter(
            CreatorPost.creator_id == creator.id,
            CreatorPost.tenant_id == tenant_id
        ).order_by(desc(CreatorPost.posted_at)).all()

        recent_logs = db.query(CreatorMonitoringLog).filter(
            CreatorMonitoringLog.creator_id == creator.id,
            CreatorMonitoringLog.tenant_id == tenant_id
        ).order_by(desc(CreatorMonitoringLog.checked_at)).limit(10).all()

        alerts = db.query(CreatorAlert).filter(
            CreatorAlert.creator_id == creator.id,
            CreatorAlert.tenant_id == tenant_id
        ).order_by(desc(CreatorAlert.created_at)).limit(10).all()

        # Problem frequency aggregator
        problem_freq: Dict[str, int] = {}
        for p in posts:
            for prob in (p.recurring_problems or []):
                problem_freq[prob] = problem_freq.get(prob, 0) + 1

        emerging_problems = [
            {"problem": prob, "mentions": count}
            for prob, count in sorted(problem_freq.items(), key=lambda x: x[1], reverse=True)
        ]

        return {
            "creator": {
                "id": creator.id,
                "username": creator.username,
                "display_name": creator.display_name,
                "platform": creator.platform,
                "follower_count": creator.follower_count,
                "engagement_rate": float(creator.engagement_rate or 0.0),
                "data_tier": creator.data_tier,
                "monitoring_status": creator.monitoring_status,
                "monitoring_interval": creator.monitoring_interval,
                "custom_interval_hours": creator.custom_interval_hours,
                "last_checked_at": creator.last_checked_at.isoformat() if creator.last_checked_at else None,
                "next_check_due": creator.next_check_due.isoformat() if creator.next_check_due else None,
                "content_fingerprint": creator.content_fingerprint,
                "theme_summary": creator.theme_summary or [],
                "alert_preferences": creator.alert_preferences or {}
            },
            "metrics": {
                "total_monitored_posts": len(posts),
                "emerging_problems_count": len(emerging_problems),
                "unread_alerts_count": sum(1 for a in alerts if not a.is_read)
            },
            "emerging_problems": emerging_problems,
            "recent_posts": [
                {
                    "id": p.id,
                    "external_post_id": p.external_post_id,
                    "caption": p.caption,
                    "topics": p.detected_topics,
                    "problems": p.recurring_problems,
                    "posted_at": p.posted_at.isoformat() if p.posted_at else None
                }
                for p in posts[:5]
            ],
            "recent_logs": [
                {
                    "id": l.id,
                    "checked_at": l.checked_at.isoformat(),
                    "status": l.status,
                    "posts_checked": l.posts_checked,
                    "new_posts_count": l.new_posts_count,
                    "summary": l.summary,
                    "error_message": l.error_message
                }
                for l in recent_logs
            ],
            "recent_alerts": [
                {
                    "id": a.id,
                    "alert_type": a.alert_type,
                    "severity": a.severity,
                    "title": a.title,
                    "message": a.message,
                    "is_read": a.is_read,
                    "created_at": a.created_at.isoformat()
                }
                for a in alerts
            ]
        }
