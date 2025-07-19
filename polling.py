# client_polling.py

import asyncio
import httpx
from uuid import uuid4
import traceback

from a2a.client import A2AClient, A2ACardResolver, A2AClientError
from a2a.client.helpers import create_text_message_object
from a2a.types import (
    MessageSendParams,
    SendMessageRequest,
    SendMessageSuccessResponse,
    GetTaskRequest,
    TaskQueryParams,
    GetTaskSuccessResponse,
    Role,
    Task,
    TaskState,
    TextPart,
    JSONRPCErrorResponse,
)

BASE_URL = "http://localhost:8002"


def get_text_from_part_list(parts: list | None) -> str | None:
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
        async with httpx.AsyncClient(timeout=10) as httpx_client:
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=BASE_URL)
            agent_card = await resolver.get_agent_card()
            client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

            print(f"✅ Connected to: '{agent_card.name}'")
            print("--------------------------------------------------")
            print("You can now chat with the Pizzeria (Polling Mode).")
            print("Examples: 'salami', 'pepperoni'")
            print("Type 'quit' to exit.")
            print("--------------------------------------------------")

            while True:
                user_input = input("You: ")
                if user_input.lower() == "quit":
                    print("👋 Goodbye!")
                    break

                start_request = SendMessageRequest(
                    params=MessageSendParams(
                        message=create_text_message_object(
                            role=Role.user, content=user_input
                        )
                    ),
                    id=f"start-request-{uuid4().hex}",
                )
                print("... sending start request ...\n")

                start_response = await client.send_message(start_request)

                if not isinstance(
                    start_response.root, SendMessageSuccessResponse
                ) or not isinstance(start_response.root.result, Task):
                    print("❌ Failed to start a task.")
                    error = (
                        start_response.root.error
                        if isinstance(start_response.root, JSONRPCErrorResponse)
                        else "Unknown error"
                    )
                    print(f"   Reason: {error}")
                    continue

                initial_task = start_response.root.result
                task_id = initial_task.id
                print(
                    f"Pizzeria: Task {task_id} created with status '{initial_task.status.state.value}'."
                )

                last_printed_message = ""
                terminal_states = [
                    TaskState.completed,
                    TaskState.failed,
                    TaskState.canceled,
                    TaskState.rejected,
                ]

                while True:
                    await asyncio.sleep(5)

                    get_task_request = GetTaskRequest(
                        params=TaskQueryParams(id=task_id),
                        id=f"get-task-request-{uuid4().hex}",
                    )

                    get_task_response = await client.get_task(get_task_request)

                    if not isinstance(get_task_response.root, GetTaskSuccessResponse):
                        print("❌ Error while polling for task status.")
                        break

                    current_task = get_task_response.root.result

                    status_message = get_text_from_part_list(
                        current_task.status.message.parts
                        if current_task.status.message
                        else None
                    )

                    if status_message and status_message != last_printed_message:
                        print(
                            f"Pizzeria: (Update) Status is '{current_task.status.state.value}': {status_message}"
                        )
                        last_printed_message = status_message

                    if current_task.status.state in terminal_states:
                        print(
                            f"Pizzeria: Task finished with status '{current_task.status.state.value}'."
                        )
                        if current_task.artifacts:
                            final_result = get_text_from_part_list(
                                current_task.artifacts[0].parts
                            )
                            print(f"Pizzeria: (Result) {final_result}")
                        break

                print("\n--- Next Order ---")

    except (httpx.ConnectError, A2AClientError) as e:
        print(f"\n❌ An error occurred: {e}")
    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
