"""
VAPI webhook endpoint.

VAPI sends a POST to this URL when the voice agent invokes a tool.
We dispatch on the function name and return results in VAPI's expected format.

Webhook payload (abbreviated):
{
  "message": {
    "type": "tool-calls",
    "toolCallList": [
      {
        "id": "call_abc123",
        "type": "function",
        "function": {
          "name": "find_nearby_hospitals",
          "arguments": "{\"location_description\": \"near Murtala Airport Lagos\", \"radius_km\": 20}"
        }
      }
    ]
  }
}

Expected response:
{
  "results": [
    {
      "toolCallId": "call_abc123",
      "result": "<string the assistant will read/use>"
    }
  ]
}
"""
import json
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.vapi_tools import find_nearby_hospitals, filter_by_condition

router = APIRouter(prefix="/vapi", tags=["vapi"])


# ── Request / response models ─────────────────────────────────────────────────

class VapiFunction(BaseModel):
    name: str
    arguments: str  # JSON-encoded string


class VapiToolCall(BaseModel):
    id: str
    type: str = "function"
    function: VapiFunction


class VapiMessage(BaseModel):
    type: str
    toolCallList: list[VapiToolCall] = []


class VapiWebhookPayload(BaseModel):
    message: VapiMessage


class VapiToolResult(BaseModel):
    toolCallId: str
    result: str


class VapiWebhookResponse(BaseModel):
    results: list[VapiToolResult]


# ── Dispatcher ────────────────────────────────────────────────────────────────

async def _dispatch(name: str, args: dict[str, Any]) -> str:
    if name == "find_nearby_hospitals":
        result = await find_nearby_hospitals(
            location_description=args["location_description"],
            radius_km=float(args.get("radius_km", 20.0)),
        )
    elif name == "filter_by_condition":
        result = await filter_by_condition(
            condition_description=args["condition_description"],
            hospital_ids=args["hospital_ids"],
        )
    else:
        result = {"error": f"Unknown tool: {name}"}

    return json.dumps(result)


# ── Webhook endpoint ──────────────────────────────────────────────────────────

@router.post("/webhook", response_model=VapiWebhookResponse)
async def vapi_webhook(payload: VapiWebhookPayload) -> VapiWebhookResponse:
    if payload.message.type != "tool-calls":
        # VAPI may send other event types (e.g. status-update); acknowledge silently
        return VapiWebhookResponse(results=[])

    results: list[VapiToolResult] = []

    for tool_call in payload.message.toolCallList:
        try:
            args = json.loads(tool_call.function.arguments)
            result_str = await _dispatch(tool_call.function.name, args)
        except Exception as exc:
            result_str = json.dumps({"error": str(exc)})

        results.append(VapiToolResult(toolCallId=tool_call.id, result=result_str))

    return VapiWebhookResponse(results=results)


# ── Tool schema endpoint (VAPI can fetch these to auto-build the assistant) ───

@router.get("/tools")
async def list_tools() -> dict:
    """
    Returns the OpenAI-style function definitions that should be registered
    on your VAPI assistant under Settings → Tools → Custom.
    """
    return {
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "find_nearby_hospitals",
                    "description": (
                        "Find hospitals near the patient's location that have available beds. "
                        "Call this first after learning where the patient is. "
                        "Returns a list of nearby hospitals with ward availability."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location_description": {
                                "type": "string",
                                "description": (
                                    "The patient's location as a natural-language description, "
                                    "e.g. 'near Murtala Muhammed Airport, Lagos' or 'Ikeja GRA'."
                                ),
                            },
                            "radius_km": {
                                "type": "number",
                                "description": "Search radius in kilometres. Defaults to 20.",
                                "default": 20,
                            },
                        },
                        "required": ["location_description"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "filter_by_condition",
                    "description": (
                        "Filter a shortlist of hospitals based on the patient's medical condition. "
                        "Call this after find_nearby_hospitals, passing the hospital_ids from those results. "
                        "Returns only hospitals with available beds in the appropriate ward type."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "condition_description": {
                                "type": "string",
                                "description": (
                                    "The patient's condition or symptoms in plain language, "
                                    "e.g. 'severe chest pain and difficulty breathing' or 'about to give birth'."
                                ),
                            },
                            "hospital_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "List of hospital_id strings returned by find_nearby_hospitals."
                                ),
                            },
                        },
                        "required": ["condition_description", "hospital_ids"],
                    },
                },
            },
        ]
    }
