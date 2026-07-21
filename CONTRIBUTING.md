# Contributing to Pricing Intelligence

## Style Guides

### Git Commit Messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/#specification) specification to write commit messages.

The following commit types are defined:
- `feat`: Use this type if you are adding features, changing code behavior or deleting functionality, etc...
- `fix`: Use this type if you are correcting bugs.
- `docs`: Use this type if you are changing any type of documentation.
- `refactor`: Use this type if you are refactoring code (i.e., not changing the behaviour of a feature).
- `chore`: Use this type if you are correcting typos, adding new line characters to files, deleting unnecessary files, etc...

> [!IMPORTANT]
> Each commit should contain the smallest possible set of changes. If a change spans multiple
> types, stage fewer files and split it into smaller separate commits.

You can combine `feat` and `fix` types with the following scopes:
- `harvey`: Use this scope if you made changes inside `harvey/` folder.
- `mcp`: Use this scope if you made changes inside `mcp_server/` folder.
- `prime`: Use this scope if you made changes inside `analysis_api/` folder.
- `csp`: Use this scope if you made changes inside `csp` folder.
- `amint`: Use this scope if you made changes inside `src/` folder.
- `ui`: Use this scope if you made changes inside `frontend/` folder.

Here are some valid git commit messages examples:
```txt
feat(prime): remove default values from minizinc model
fix(amint): disable temperature if using `high` reasoning effort in OpenAI models
refactor(harvey): extract FileManager class
```

To enforce these commit conventions we are using [Husky](https://typicode.github.io/husky/) with [commitlint](https://commitlint.js.org/). You will not
be able to commit if you write an invalid commit message; the tool will display an error in that situation.

> [!NOTE]
> If you are making changes outside of the folders listed above, you are allowed to drop the scope and bypass the git hook, i.e, `git commit -m "feat: add some module" -n`.
