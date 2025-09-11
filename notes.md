For pydantic-AI agents, you can use register tools via either the `@agent.tool` decorator or via
```
    tools=[  
        Tool(roll_dice, takes_ctx=False),
        Tool(get_player_name, takes_ctx=True),
    ],
```
https://ai.pydantic.dev/tools/#registering-function-tools-via-decorator