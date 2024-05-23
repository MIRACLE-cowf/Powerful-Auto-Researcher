import asyncio
import operator
from typing import Annotated, Any

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.runnables import RunnableSerializable

from CustomHelper.Helper import retry_with_delay_async


async def agent_outcome_checker(
    agent: RunnableSerializable,
    input: dict,
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
) -> dict[str, Any] | dict[str, AgentFinish]:

    for attempt in range(5):
        agent_outcome = await retry_with_delay_async(
            chain=agent,
            input={
                "input"             : input["input"],
                "section_info"      : input["section_info"],
                "intermediate_steps": intermediate_steps
            },
            max_retries=3,
            delay_seconds=45.0,
        )
        if isinstance(agent_outcome, list) and len(agent_outcome) > 0:
            return {"agent_outcome": agent_outcome[0]}
        elif isinstance(agent_outcome, AgentFinish):
            if not agent_outcome.return_values["output"]:
                print(f"agent outcome is {agent_outcome.return_values['output']}")
                await asyncio.sleep(10)  # 5초 대기 후 다시 시도
                continue
            return {"agent_outcome": agent_outcome}
        else:
            raise ValueError(f"Unexpected agent_outcome: {agent_outcome}")

