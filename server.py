import asyncio
from uuid import uuid4

import uvicorn
from fastapi import FastAPI

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import RequestHandler

# CHANGE 1: Import the official TaskStore from the library
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    Artifact,
    MessageSendParams,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
    TextPart,
    TaskQueryParams,
    TaskPushNotificationConfig,
)
from a2a.utils import new_agent_text_message, new_task

# The custom TaskStore class is no longer needed.


class AgentExecutor:
    # This class does not need any changes, as it uses the TaskStore via a standard interface.
    def __init__(self, task_store: InMemoryTaskStore):
        self.task_store = task_store

    async def run_pizza_process(
        self, task_id: str, user_input: str, update_queue: asyncio.Queue | None = None
    ):
        print(f"⚙️  Background executor started for task {task_id}...")

        async def update_status(new_state: TaskState, message_text: str | None = None):
            task = await self.task_store.get(task_id)
            if not task:
                return
            task.status.state = new_state
            if message_text:
                task.status.message = new_agent_text_message(message_text)
            else:
                task.status.message = None
            await self.task_store.save(task)
            return task.status

        async def notify(event):
            if update_queue:
                await update_queue.put(event)

        try:
            status = await update_status(
                TaskState.working,
                "Okay, your order is being prepared. First, kneading the dough...",
            )
            await notify(
                TaskStatusUpdateEvent(
                    taskId=task_id,
                    contextId=(await self.task_store.get(task_id)).contextId,
                    status=status,
                    final=False,
                )
            )
            await asyncio.sleep(1.5)

            status = await update_status(
                TaskState.working, "The dough is ready and is now being rolled out."
            )
            await notify(
                TaskStatusUpdateEvent(
                    taskId=task_id,
                    contextId=(await self.task_store.get(task_id)).contextId,
                    status=status,
                    final=False,
                )
            )
            await asyncio.sleep(2)

            status = await update_status(
                TaskState.working, "Applying tomato sauce and cheese."
            )
            await notify(
                TaskStatusUpdateEvent(
                    taskId=task_id,
                    contextId=(await self.task_store.get(task_id)).contextId,
                    status=status,
                    final=False,
                )
            )
            await asyncio.sleep(2)

            topping_message = "The toppings are being added."
            if "salami" in user_input:
                topping_message = (
                    "The fresh salami is being carefully placed on the pizza."
                )
            elif "pepperoni" in user_input:
                topping_message = "The spicy pepperoni is being placed on the pizza."
            status = await update_status(TaskState.working, topping_message)
            await notify(
                TaskStatusUpdateEvent(
                    taskId=task_id,
                    contextId=(await self.task_store.get(task_id)).contextId,
                    status=status,
                    final=False,
                )
            )
            await asyncio.sleep(2)

            status = await update_status(
                TaskState.working,
                "Perfect! The pizza is now in the hot stone oven and smells delicious.",
            )
            await notify(
                TaskStatusUpdateEvent(
                    taskId=task_id,
                    contextId=(await self.task_store.get(task_id)).contextId,
                    status=status,
                    final=False,
                )
            )
            await asyncio.sleep(3)

            if "salami" in user_input:
                final_message = (
                    "Ding! 🍕 Your Salami pizza is golden-brown and ready for pickup!"
                )
            elif "pepperoni" in user_input:
                final_message = (
                    "Ding! 🍕 Your Pepperoni pizza is ready and waiting for you!"
                )
            else:
                final_message = (
                    "Sorry, I didn't understand that. Please order salami or pepperoni."
                )

            task = await self.task_store.get(task_id)
            task.artifacts = [
                Artifact(
                    artifactId=f"artifact-{uuid4().hex}",
                    parts=[TextPart(text=final_message)],
                )
            ]
            await notify(
                TaskArtifactUpdateEvent(
                    taskId=task_id,
                    contextId=task.contextId,
                    artifact=task.artifacts[0],
                    lastChunk=True,
                )
            )

            status = await update_status(TaskState.completed)
            await notify(
                TaskStatusUpdateEvent(
                    taskId=task_id,
                    contextId=(await self.task_store.get(task_id)).contextId,
                    status=status,
                    final=True,
                )
            )

            print(f"✅ Background executor finished for task {task_id}.")
        finally:
            if update_queue:
                await update_queue.put(None)


class HybridPizzeriaHandler(RequestHandler):
    def __init__(self, task_store: InMemoryTaskStore, agent_executor: AgentExecutor):
        self.task_store = task_store
        self.agent_executor = agent_executor

    async def on_message_send(self, params: MessageSendParams, context=None) -> Task:
        task = new_task(request=params.message)
        await self.task_store.save(task)
        user_input = (
            params.message.parts[0].root.text.lower() if params.message.parts else ""
        )
        print(
            f"📬 Polling Handler: Accepted task {task.id}. Starting background executor."
        )
        asyncio.create_task(
            self.agent_executor.run_pizza_process(
                task_id=task.id, user_input=user_input
            )
        )
        return task

    async def on_get_task(self, params: TaskQueryParams, context=None) -> Task:
        print(f"📬 Polling Handler: Received get_task request for {params.id}")
        task = await self.task_store.get(params.id)
        if not task:
            raise ValueError(f"Task with ID {params.id} not found.")
        return task

    async def on_message_send_stream(self, params: MessageSendParams, context=None):
        task = new_task(request=params.message)
        await self.task_store.save(task)
        user_input = (
            params.message.parts[0].root.text.lower() if params.message.parts else ""
        )
        print(
            f"📬 Streaming Handler: Accepted task {task.id}. Starting background executor."
        )
        update_queue = asyncio.Queue()
        asyncio.create_task(
            self.agent_executor.run_pizza_process(
                task_id=task.id, user_input=user_input, update_queue=update_queue
            )
        )
        yield task
        while True:
            update = await update_queue.get()
            if update is None:
                break
            yield update

    async def on_cancel_task(self, params, context=None):
        raise NotImplementedError("Not implemented.")

    async def on_resubscribe_to_task(self, params, context=None):
        raise NotImplementedError("Not implemented.")

    async def on_set_task_push_notification_config(self, params, context=None):
        raise NotImplementedError("Not implemented.")

    async def on_get_task_push_notification_config(self, params, context=None):
        raise NotImplementedError("Not implemented.")

    async def on_list_task_push_notification_config(
        self, params, context=None
    ) -> list[TaskPushNotificationConfig]:
        raise NotImplementedError("Not implemented.")

    async def on_delete_task_push_notification_config(
        self, params, context=None
    ) -> None:
        raise NotImplementedError("Not implemented.")


def build_app() -> FastAPI:
    task_store = InMemoryTaskStore()
    agent_executor = AgentExecutor(task_store)

    skill = AgentSkill(
        id="order-pizza-hybrid",
        name="Order Pizza (Hybrid)",
        description="Takes pizza orders and provides live status updates via streaming or polling.",
        tags=["food", "order", "pizza", "hybrid"],
        examples=["I would like a salami pizza."],
    )
    card = AgentCard(
        name="Hybrid Pizzeria Agent",
        description="An agent that processes orders and supports both streaming and polling.",
        url="http://localhost:8002/",
        version="4.0",
        defaultInputModes=["text/plain"],
        defaultOutputModes=["text/plain"],
        skills=[skill],
        capabilities=AgentCapabilities(streaming=True, pushNotifications=False),
    )

    http_handler = HybridPizzeriaHandler(task_store, agent_executor)

    a2a_app = A2AStarletteApplication(
        agent_card=card, http_handler=http_handler
    ).build()
    api = FastAPI(title="Hybrid A2A Pizzeria Server")
    api.mount("/", a2a_app)
    return api


app = build_app()

if __name__ == "__main__":
    print("🍕 Starting Hybrid Pizzeria Server on http://localhost:8002")
    uvicorn.run(app, host="0.0.0.0", port=8002)
