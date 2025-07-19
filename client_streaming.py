# client.py

import asyncio
import httpx
from uuid import uuid4
import traceback

from a2a.client import A2AClient, A2ACardResolver, A2AClientError
from a2a.client.helpers import create_text_message_object
from a2a.types import (
    MessageSendParams,
    SendStreamingMessageRequest,
    SendStreamingMessageSuccessResponse,
    Role,
    Task,
    TextPart,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    JSONRPCErrorResponse,
)

BASE_URL = "http://localhost:8002"


def get_text_from_part_list(parts: list) -> str | None:
    if not parts:
        return None
    for part in parts:
        part_obj = part.root
        if isinstance(part_obj, TextPart):
            return part_obj.text
    return None


async def main():
    print(f"➡️  Connecting to A2A Agent at {BASE_URL}...")
    try:
        async with httpx.AsyncClient(timeout=30) as httpx_client:
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=BASE_URL)
            agent_card = await resolver.get_agent_card()
            client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

            print(f"✅ Connected to: '{agent_card.name}'")
            print("--------------------------------------------------")
            print("You can now chat with the Pizzeria.")
            print("Examples: 'salami', 'pepperoni'")
            print("Type 'quit' to exit.")
            print("--------------------------------------------------")

            while True:
                user_input = input("You: ")
                if user_input.lower() == "quit":
                    print("👋 Goodbye!")
                    break

                request = SendStreamingMessageRequest(
                    params=MessageSendParams(
                        message=create_text_message_object(
                            role=Role.user, content=user_input
                        )
                    ),
                    id=f"request-{uuid4().hex}",
                )

                print("... sending request and waiting for live updates ...\n")

                try:
                    async for event in client.send_message_streaming(request):
                        event_model = event.root

                        if isinstance(event_model, JSONRPCErrorResponse):
                            error_info = event_model.error
                            print(
                                f"❌ Error from server: {error_info.code} - {error_info.message}"
                            )
                            break

                        if isinstance(event_model, SendStreamingMessageSuccessResponse):
                            result = event_model.result

                            if isinstance(result, Task):
                                print(
                                    f"Pizzeria: Task {result.id} created with status '{result.status.state.value}'."
                                )

                            elif isinstance(result, TaskStatusUpdateEvent):
                                status_text = (
                                    f"Status is now '{result.status.state.value}'"
                                )
                                message_text = get_text_from_part_list(
                                    result.status.message.parts
                                    if result.status.message
                                    else []
                                )
                                if message_text:
                                    status_text += f": {message_text}"
                                print(f"Pizzeria: (Update) {status_text}")

                            elif isinstance(result, TaskArtifactUpdateEvent):
                                artifact_text = get_text_from_part_list(
                                    result.artifact.parts
                                )
                                if artifact_text:
                                    print(f"Pizzeria: (Result) {artifact_text}")

                except A2AClientError as e:
                    print(f"❌ A2A Stream Error: {e}")

                print("\n--- Next Order ---")

    except httpx.ConnectError:
        print("\n❌ Connection error. Is the 'server.py' server running on port 8002?")
    except Exception as e:
        print(f"\n🚨 An unexpected error occurred: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
