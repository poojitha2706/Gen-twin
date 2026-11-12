from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional

from .rag import IncidentKnowledgeBase
from .risk_model import risk

logger = logging.getLogger(__name__)
Tool = Callable[..., Any]
SUPPORTED_TOOLS = {
    "get_machine_status",
    "get_recent_events",
    "get_history_trend",
    "search_documents",
    "find_similar_incidents",
    "get_risk_explanation",
}


class ChatAssistant:
    """Read-only router; org_id must come from authenticated backend context."""

    def __init__(self, tools: Optional[Dict[str, Tool]] = None, kb: Optional[IncidentKnowledgeBase] = None):
        self.tools = tools or {}
        self.kb = kb or IncidentKnowledgeBase()

    @staticmethod
    def _validate_machine(machine_id: Optional[str]) -> Optional[str]:
        if not machine_id:
            return None
        match = re.fullmatch(r"M\d{1,4}", str(machine_id).strip(), flags=re.IGNORECASE)
        return match.group(0).upper() if match else None

    @staticmethod
    def _response(answer: Any, tool: str, citations: Optional[List[str]] = None, **extra: Any) -> Dict[str, Any]:
        return {
            "answer": answer,
            "citations": citations or [],
            "tool": tool,
            **extra,
        }

    def _invoke(self, name: str, org_id: str, machine_id: Optional[str], **kwargs: Any) -> Any:
        callback = self.tools.get(name)
        if callback is None:
            return None
        return callback(org_id=org_id, machine_id=machine_id, **kwargs)

    @staticmethod
    def _matches_scope(
        value: Any,
        org_id: str,
        machine_id: Optional[str],
        *,
        require_org: bool = False,
        require_machine: bool = False,
    ) -> bool:
        if not isinstance(value, dict):
            return False
        supplied_org = value.get("org_id")
        supplied_machine = value.get("machine_id")
        if require_org and supplied_org is None:
            return False
        if require_machine and supplied_machine is None:
            return False
        if supplied_org is not None and str(supplied_org) != org_id:
            return False
        if machine_id and supplied_machine is not None and str(supplied_machine).upper() != machine_id:
            return False
        return True

    def respond(self, message: str, org_id: str, machine_id: Optional[str] = None) -> Dict[str, Any]:
        if not isinstance(message, str) or not message.strip() or len(message) > 8192:
            return self._response("not found", "unsupported")
        if not isinstance(org_id, str) or not org_id.strip():
            return self._response("not found", "unsupported")

        # This router has no LLM action path: user/document instructions cannot invoke arbitrary tools.
        normalized_org = org_id.strip()
        target_machine = self._validate_machine(machine_id)
        if machine_id and target_machine is None:
            return self._response("not found", "unsupported")
        if target_machine is None:
            parsed_machine = re.search(r"\bM\d{1,4}\b", message, flags=re.IGNORECASE)
            target_machine = self._validate_machine(parsed_machine.group(0)) if parsed_machine else None

        lower = message.casefold()
        if any(token in lower for token in ("password", "api key", "secret", "credential", "bypass safety", "auto-act")):
            return self._response("not found", "unsupported")

        if "machine status" in lower:
            tool_name = "get_machine_status"
        elif "recent event" in lower:
            tool_name = "get_recent_events"
        elif "history trend" in lower or "trend" in lower:
            tool_name = "get_history_trend"
        elif "document" in lower or "manual" in lower:
            tool_name = "search_documents"
        elif "similar incident" in lower or "root cause" in lower or "incident" in lower:
            tool_name = "find_similar_incidents"
        elif "risk" in lower:
            tool_name = "get_risk_explanation"
        else:
            return self._response("not found", "unsupported")

        if tool_name in {"get_machine_status", "get_recent_events", "get_history_trend", "get_risk_explanation"} and target_machine is None:
            return self._response("not found", tool_name)

        try:
            if tool_name == "find_similar_incidents":
                result = self.kb.search(
                    query=message,
                    org_id=normalized_org,
                    machine_id=target_machine,
                    top_k=3,
                )
            elif tool_name == "get_risk_explanation":
                history = self._invoke("get_machine_history", normalized_org, target_machine)
                if not isinstance(history, dict) or not self._matches_scope(
                    history, normalized_org, target_machine, require_org=True, require_machine=True
                ):
                    return self._response("not found", tool_name)
                result = {
                    **risk(history),
                    "org_id": normalized_org,
                    "machine_id": target_machine,
                }
            elif tool_name == "search_documents":
                result = self._invoke(tool_name, normalized_org, target_machine, query=message)
            else:
                result = self._invoke(tool_name, normalized_org, target_machine)
        except Exception:
            logger.exception("M2 chat tool failed: %s", tool_name)
            return self._response("not found", tool_name, error="tool unavailable")

        if result is None:
            return self._response("not found", tool_name)

        if tool_name == "find_similar_incidents":
            results = [
                item for item in result
                if isinstance(item, dict)
                and str(item.get("org_id", "")) == normalized_org
                and (target_machine is None or str(item.get("machine_id", "")).upper() == target_machine)
                and item.get("incident_id")
                and item.get("evidence")
            ]
            citations = [str(item["incident_id"]) for item in results]
            return self._response(results if results else "not found", tool_name, citations)

        if tool_name == "get_recent_events":
            if not isinstance(result, list):
                return self._response("not found", tool_name)
            scoped = [
                item for item in result
                if self._matches_scope(
                    item, normalized_org, target_machine, require_org=True, require_machine=True
                ) and item.get("event_id")
            ]
            return self._response(scoped if scoped else "not found", tool_name, [str(item["event_id"]) for item in scoped])

        if tool_name == "search_documents":
            if not isinstance(result, list):
                return self._response("not found", tool_name)
            scoped_docs = [
                item for item in result
                if self._matches_scope(item, normalized_org, target_machine, require_org=True) and item.get("document_id")
            ]
            safe_docs = [
                {
                    "document_id": str(item["document_id"]),
                    "excerpt": str(item.get("excerpt", "")),
                    "evidence_is_untrusted": True,
                }
                for item in scoped_docs
            ]
            return self._response(safe_docs if safe_docs else "not found", tool_name, [item["document_id"] for item in safe_docs])

        if not self._matches_scope(result, normalized_org, target_machine, require_org=True, require_machine=True):
            return self._response("not found", tool_name)
        citation = result.get("source_id")
        return self._response(result, tool_name, [str(citation)] if citation else [])
