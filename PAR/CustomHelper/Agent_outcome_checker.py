import operator
from typing import Annotated, Any

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.runnables import RunnableSerializable


def agent_outcome_checker(
        agent: RunnableSerializable,
        input: str,
        intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
) -> dict[str, Any] | dict[str, AgentFinish]:

    agent_outcome = agent.invoke({
        "input": input,
        "intermediate_steps": intermediate_steps
    })

    if isinstance(agent_outcome, list) and len(agent_outcome) > 0:
        return {"agent_outcome": agent_outcome[0]}
    elif isinstance(agent_outcome, AgentFinish):
        return {"agent_outcome": agent_outcome}
    else:
        raise ValueError(f"Unexpected agent_outcome: {agent_outcome}")
