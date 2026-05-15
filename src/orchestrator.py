import uuid
from src.planner import plan_task
from src.executor import execute_plan
from src.memory.vector_store import store_memory, search_memory
from src.memory.state import save_checkpoint
from src.api.observability import log_event


async def execute(run_id: str, payload: dict):
    task = payload.get("task")

    log_event(run_id, "orchestrator_started", {
        "task": task
    })

    # Step 1: Retrieve previous memory
    previous_context = search_memory(task)

    log_event(run_id, "memory_retrieved", {
        "context": previous_context
    })

    # Step 2: Create plan
    plan = plan_task(task, previous_context)

    log_event(run_id, "plan_created", {
        "plan": plan
    })

    # Step 3: Execute plan
    result = execute_plan(plan)

    log_event(run_id, "execution_completed", {
        "result": result
    })

    # Step 4: Store new memory
    store_memory(
        text=f"Task: {task}\nResult: {result}"
    )

    log_event(run_id, "memory_stored", {})

    # Step 5: Save checkpoint
    save_checkpoint(run_id, {
        "task": task,
        "plan": plan,
        "result": result
    })

    log_event(run_id, "checkpoint_saved", {})

    return {
        "run_id": run_id,
        "status": "completed",
        "task": task,
        "plan": plan,
        "result": result,
        "previous_context": previous_context
    }
