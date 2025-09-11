For pydantic-AI agents, you can use register tools via either the `@agent.tool` decorator or via
```
    tools=[  
        Tool(roll_dice, takes_ctx=False),
        Tool(get_player_name, takes_ctx=True),
    ],
```
https://ai.pydantic.dev/tools/#registering-function-tools-via-decorator

Desired functionality:
* edit a topas .inp file -> access and edit a text file
* run the topas macro (>ta macro.inp)
* read macro.out and .dat files
* generate and read plot from .dat
* analyse how well input is fitting and adjust input accordingly
* condition for termination (good fit, impossible to get good fit, timeout)