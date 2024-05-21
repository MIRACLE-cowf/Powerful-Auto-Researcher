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

    agent_outcome = await retry_with_delay_async(
        chain=agent,
        input={
            "input": input["input"],
            "section_info": input["section_info"],
            "intermediate_steps": intermediate_steps
        },
        max_retries=3,
        delay_seconds=45,
    )

    # agent_outcome = await agent.ainvoke({
    #     "input": input,
    #     "intermediate_steps": intermediate_steps
    # })

    if isinstance(agent_outcome, list) and len(agent_outcome) > 0:
        return {"agent_outcome": agent_outcome[0]}
    elif isinstance(agent_outcome, AgentFinish):
        return {"agent_outcome": agent_outcome}
    else:
        raise ValueError(f"Unexpected agent_outcome: {agent_outcome}")
