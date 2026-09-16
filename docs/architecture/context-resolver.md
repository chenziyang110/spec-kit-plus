# Context Resolver

Context Resolver is the first stage of Runtime Context Compiler.

Flow:

```
Task Input
    |
    v
Context Resolver
    |
    v
Resolved Context
    |
    v
Context Compiler
    |
    v
Context Packet
```

Resolver responsibilities:

- preserve explicit task intent
- collect bounded artifact references
- carry acceptance requirements supplied by runtime
- carry workflow constraints
- preserve runtime state references

Resolver does not:

- grant permissions
- modify artifacts
- decide completion
- replace review or acceptance
- infer repository truth from filenames

Future runtime adapters may provide task state, artifact resolution and policy
rules. Those adapters must keep source-of-truth ownership inside runtime.
