---
description: Run a shell command with sourced aliases
---

Run the following bash command in the project directory:

```bash
clear
source aliases.csh && {{ARGS}}
```

Where {{ARGS}} are the parameters provided after /s.

If no arguments are provided, just source the aliases and show a success message.

the output should contain all shell output colored like it will be in shell without any other output. use ctrl+o so i will see all
