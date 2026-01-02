# hyperclaude Architecture

Comprehensive architecture documentation with detailed diagrams for the hyperclaude swarm orchestration system.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Directory Structure](#directory-structure)
4. [Startup Sequence](#startup-sequence)
5. [Task Execution Flow](#task-execution-flow)
6. [Protocol System](#protocol-system)
7. [State Management](#state-management)
8. [Trigger System](#trigger-system)
9. [Protocol Workflows](#protocol-workflows)
   - [Default Protocol](#default-protocol-workflow)
   - [Git-Branch Protocol](#git-branch-protocol-workflow)
   - [Search Protocol](#search-protocol-workflow)
   - [Review Protocol](#review-protocol-workflow)
10. [Token Efficiency](#token-efficiency)
11. [Data Flow](#data-flow)
12. [Security Model](#security-model)

---

## System Overview

The hyperclaude system creates a coordinated swarm of Claude Code instances within a tmux session.

```mermaid
graph TB
    subgraph "Terminal Window"
        subgraph "tmux session: swarm"
            subgraph "Worker Panes"
                W0[Worker 0<br/>Claude CLI<br/>--dangerously-skip-permissions]
                W1[Worker 1<br/>Claude CLI<br/>--dangerously-skip-permissions]
                W2[Worker 2<br/>Claude CLI<br/>--dangerously-skip-permissions]
                W3[Worker 3<br/>Claude CLI<br/>--dangerously-skip-permissions]
                W4[Worker 4<br/>Claude CLI<br/>--dangerously-skip-permissions]
                W5[Worker 5<br/>Claude CLI<br/>--dangerously-skip-permissions]
            end

            subgraph "Manager Pane"
                M[Manager<br/>Claude CLI<br/>Normal Permissions]
            end
        end
    end

    subgraph "User"
        U[Human User]
    end

    subgraph "File System: ~/.hyperclaude/"
        P[protocols/]
        S[state/]
        T[triggers/]
        R[results/]
        L[locks/]
    end

    U -->|"Instructions"| M
    M -->|"hyperclaude send"| W0
    M -->|"hyperclaude send"| W1
    M -->|"hyperclaude send"| W2
    M -->|"hyperclaude send"| W3
    M -->|"hyperclaude send"| W4
    M -->|"hyperclaude send"| W5

    W0 -->|"hyperclaude done"| T
    W1 -->|"hyperclaude done"| T
    W2 -->|"hyperclaude done"| T
    W3 -->|"hyperclaude done"| T
    W4 -->|"hyperclaude done"| T
    W5 -->|"hyperclaude done"| T

    M -->|"hyperclaude await"| T
    M -->|"hyperclaude state"| S
    M -->|"hyperclaude results"| R

    W0 & W1 & W2 & W3 & W4 & W5 -->|"Read once"| P
    W0 & W1 & W2 & W3 & W4 & W5 -->|"hyperclaude lock/unlock"| L
```

---

## Component Architecture

```mermaid
graph TB
    subgraph "CLI Layer (cli.py)"
        CLI_MAIN[main<br/>Start swarm]
        CLI_STOP[stop<br/>Stop swarm]
        CLI_PROTO[protocol<br/>Set/get protocol]
        CLI_PHASE[phase<br/>Set/get phase]
        CLI_SEND[send<br/>Send to worker]
        CLI_BCAST[broadcast<br/>Send to all]
        CLI_AWAIT[await<br/>Wait for trigger]
        CLI_STATE[state<br/>View states]
        CLI_DONE[done<br/>Signal complete]
        CLI_LOCK[lock/unlock<br/>File locks]
    end

    subgraph "Launcher Layer (launcher.py)"
        L_START[start_swarm<br/>Create tmux session]
        L_STOP[stop_swarm<br/>Kill session]
        L_SEND[send_to_worker<br/>tmux send-keys]
        L_STATUS[get_swarm_status<br/>Token counts]
        L_CLEAR[clear_all_workers<br/>Send /clear]
        L_PREAMBLE[get_manager_preamble<br/>Manager init text]
    end

    subgraph "Protocol Layer (protocols.py)"
        P_LIST[list_protocols<br/>Available protocols]
        P_GET[get_protocol<br/>Read protocol file]
        P_SET[set_active_protocol<br/>Write state/protocol]
        P_PHASE[get/set_phase<br/>Phase management]
        P_STATE[get/set_worker_state<br/>JSON state]
        P_TRIG[create/await_trigger<br/>Trigger files]
        P_INSTALL[install_default_protocols<br/>Copy templates]
    end

    subgraph "Config Layer (config.py)"
        C_DIRS[ensure_directories<br/>Create ~/.hyperclaude/]
        C_LOAD[load_config<br/>Read config.yaml]
        C_PATHS[get_*_dir/file<br/>Path helpers]
    end

    subgraph "tmux"
        TMUX[tmux commands<br/>send-keys, capture-pane]
    end

    subgraph "File System"
        FS[~/.hyperclaude/*]
    end

    CLI_MAIN --> L_START
    CLI_STOP --> L_STOP
    CLI_SEND --> L_SEND
    CLI_SEND --> P_STATE
    CLI_PROTO --> P_SET
    CLI_PHASE --> P_PHASE
    CLI_AWAIT --> P_TRIG
    CLI_STATE --> P_STATE
    CLI_DONE --> P_TRIG
    CLI_DONE --> P_STATE

    L_START --> C_DIRS
    L_START --> P_INSTALL
    L_START --> TMUX
    L_SEND --> TMUX

    P_STATE --> FS
    P_TRIG --> FS
    P_GET --> FS
    C_DIRS --> FS
```

---

## Directory Structure

```mermaid
graph TD
    subgraph "~/.hyperclaude/"
        ROOT[~/.hyperclaude/]

        subgraph "Configuration"
            CONFIG[config.yaml]
            INIT[manager-init.txt]
        end

        subgraph "Protocols"
            PROTO_DIR[protocols/]
            PROTO_DEF[default.md]
            PROTO_GIT[git-branch.md]
            PROTO_SEARCH[search.md]
            PROTO_REVIEW[review.md]
        end

        subgraph "State"
            STATE_DIR[state/]
            STATE_PROTO[protocol<br/>Active protocol name]
            STATE_PHASE[phase<br/>Current phase]
            STATE_WORKERS[workers/]
            STATE_W0[0.json]
            STATE_W1[1.json]
            STATE_WN[N.json]
        end

        subgraph "Triggers"
            TRIG_DIR[triggers/]
            TRIG_W0[worker-0-done]
            TRIG_W1[worker-1-done]
            TRIG_ALL[all-done]
            TRIG_CONF[conflict]
        end

        subgraph "Results"
            RES_DIR[results/]
            RES_W0[worker-0.txt]
            RES_W1[worker-1.txt]
            RES_WN[worker-N.txt]
        end

        subgraph "Locks"
            LOCK_DIR[locks/]
            LOCK_W0[worker-0.lock]
            LOCK_W1[worker-1.lock]
        end

        subgraph "Logs"
            LOG_DIR[logs/]
            LOG_SESS[session-TIMESTAMP/]
        end
    end

    ROOT --> CONFIG
    ROOT --> INIT
    ROOT --> PROTO_DIR
    PROTO_DIR --> PROTO_DEF
    PROTO_DIR --> PROTO_GIT
    PROTO_DIR --> PROTO_SEARCH
    PROTO_DIR --> PROTO_REVIEW

    ROOT --> STATE_DIR
    STATE_DIR --> STATE_PROTO
    STATE_DIR --> STATE_PHASE
    STATE_DIR --> STATE_WORKERS
    STATE_WORKERS --> STATE_W0
    STATE_WORKERS --> STATE_W1
    STATE_WORKERS --> STATE_WN

    ROOT --> TRIG_DIR
    TRIG_DIR --> TRIG_W0
    TRIG_DIR --> TRIG_W1
    TRIG_DIR --> TRIG_ALL
    TRIG_DIR --> TRIG_CONF

    ROOT --> RES_DIR
    RES_DIR --> RES_W0
    RES_DIR --> RES_W1
    RES_DIR --> RES_WN

    ROOT --> LOCK_DIR
    LOCK_DIR --> LOCK_W0
    LOCK_DIR --> LOCK_W1

    ROOT --> LOG_DIR
    LOG_DIR --> LOG_SESS
```

---

## Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant CLI as cli.py
    participant Launcher as launcher.py
    participant Protocols as protocols.py
    participant Config as config.py
    participant tmux
    participant FS as File System
    participant Terminal

    User->>CLI: hyperclaude [--workers N]

    rect rgb(240, 248, 255)
        Note over CLI,Config: Initialization Phase
        CLI->>Config: init_hyperclaude()
        Config->>FS: Create ~/.hyperclaude/ directories
        FS-->>Config: Directories created

        CLI->>Protocols: install_default_protocols()
        Protocols->>FS: Copy templates/protocols/*.md to ~/.hyperclaude/protocols/
        FS-->>Protocols: Protocols installed

        CLI->>Protocols: reset_swarm_state()
        Protocols->>FS: Clear state/, triggers/
        FS-->>Protocols: State reset
    end

    rect rgb(255, 248, 240)
        Note over CLI,tmux: tmux Session Creation
        CLI->>Launcher: start_swarm(workspace, num_workers, model)
        Launcher->>tmux: kill-session -t swarm (if exists)
        Launcher->>tmux: new-session -d -s swarm -n main
        Launcher->>tmux: set-option mouse on
    end

    rect rgb(240, 255, 240)
        Note over Launcher,tmux: Worker Pane Creation

        loop For each worker 0 to N-1
            alt First worker (pane 0)
                Launcher->>tmux: send-keys "export HYPERCLAUDE_WORKER_ID=0"
                Launcher->>tmux: send-keys Enter
                Launcher->>tmux: send-keys "claude --dangerously-skip-permissions"
                Launcher->>tmux: send-keys Enter
            else Additional workers
                Launcher->>tmux: split-window -h
                Launcher->>tmux: send-keys "export HYPERCLAUDE_WORKER_ID={i}"
                Launcher->>tmux: send-keys Enter
                Launcher->>tmux: send-keys "claude --dangerously-skip-permissions"
                Launcher->>tmux: send-keys Enter
                Launcher->>tmux: select-layout tiled
            end
        end
    end

    rect rgb(255, 240, 255)
        Note over Launcher,tmux: Manager Pane Creation
        Launcher->>tmux: split-window -v
        Launcher->>tmux: select-layout tiled
        Launcher->>tmux: send-keys "claude [--continue]"
        Launcher->>tmux: send-keys Enter
    end

    rect rgb(255, 255, 240)
        Note over Launcher,tmux: Wait for Ready
        loop For each pane
            Launcher->>tmux: capture-pane -p
            tmux-->>Launcher: Pane content
            Note over Launcher: Check for ">" prompt or "tokens"
        end
    end

    rect rgb(240, 240, 255)
        Note over Launcher,tmux: Clear Workers
        loop For each worker
            Launcher->>tmux: send-keys "/clear"
            Launcher->>tmux: send-keys Enter
        end
    end

    rect rgb(255, 240, 240)
        Note over Launcher,FS: Initialize Manager
        Launcher->>FS: Write manager-init.txt (preamble)
        Launcher->>tmux: send-keys "Read ~/.hyperclaude/manager-init.txt..."
        Launcher->>tmux: send-keys Enter
    end

    rect rgb(240, 255, 255)
        Note over Launcher,Terminal: Open Terminal Window
        Launcher->>Terminal: osascript (macOS) or detect terminal (Linux)
        Terminal->>tmux: tmux attach -t swarm
    end

    Launcher-->>CLI: Swarm started
    CLI-->>User: "hyperclaude swarm started!"
```

---

## Task Execution Flow

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Manager as Manager Claude
    participant CLI as hyperclaude CLI
    participant FS as File System
    participant tmux
    participant Worker as Worker Claude
    participant Protocol as Protocol File

    User->>Manager: "Implement feature X with git branching"

    rect rgb(240, 248, 255)
        Note over Manager,CLI: Protocol Setup
        Manager->>CLI: hyperclaude protocol git-branch
        CLI->>FS: Write "git-branch" to state/protocol
        CLI-->>Manager: "Protocol set to: git-branch"

        Manager->>CLI: hyperclaude phase assign
        CLI->>FS: Write "assign" to state/phase
        CLI-->>Manager: "Phase set to: assign"
    end

    rect rgb(255, 248, 240)
        Note over Manager,Worker: Task Distribution
        Manager->>CLI: hyperclaude send 0 "Implement auth module"

        CLI->>FS: Read state/protocol → "git-branch"
        CLI->>FS: Read state/phase → "assign"
        CLI->>FS: Write state/workers/0.json
        Note over FS: {"status": "working", "assignment": "Implement auth module"}

        CLI->>tmux: send-keys to pane 0
        Note over tmux: "W0 | git-branch | assign<br/>Task: Implement auth module<br/>Protocol: ~/.hyperclaude/protocols/git-branch.md"
        tmux->>Worker: Message delivered

        CLI-->>Manager: "Task sent to worker 0"
    end

    rect rgb(240, 255, 240)
        Note over Worker,Protocol: Worker Execution
        Worker->>Protocol: Read ~/.hyperclaude/protocols/git-branch.md
        Protocol-->>Worker: Protocol instructions

        Note over Worker: 1. git checkout -b worker-0-auth
        Note over Worker: 2. Implement changes
        Note over Worker: 3. git add . && git commit
        Note over Worker: 4. git push -u origin worker-0-auth

        Worker->>CLI: hyperclaude done --branch worker-0-auth --files src/auth.py
        CLI->>FS: Update state/workers/0.json
        Note over FS: {"status": "complete", "branch": "worker-0-auth", "files": ["src/auth.py"]}
        CLI->>FS: Create triggers/worker-0-done
        CLI->>FS: Check all workers done → Create triggers/all-done
        CLI-->>Worker: "Worker 0 marked as complete"
    end

    rect rgb(255, 240, 255)
        Note over Manager,FS: Wait and Collect Results
        Manager->>CLI: hyperclaude await all-done

        loop Poll every 0.5s
            CLI->>FS: Check triggers/all-done exists?
        end

        FS-->>CLI: File exists!
        CLI-->>Manager: "Trigger 'all-done' received."

        Manager->>CLI: hyperclaude state
        CLI->>FS: Read state/workers/*.json
        CLI-->>Manager: Worker states display

        Manager->>CLI: hyperclaude results
        CLI->>FS: Read results/worker-*.txt
        CLI-->>Manager: Results display
    end

    rect rgb(255, 255, 240)
        Note over Manager,FS: Merge and Cleanup
        Note over Manager: git merge worker-0-auth
        Note over Manager: Resolve conflicts if any

        Manager->>CLI: hyperclaude phase done
        Manager->>CLI: hyperclaude clear
        CLI->>FS: Clear state/, triggers/
        CLI->>tmux: send-keys "/clear" to all workers
        CLI-->>Manager: "All workers and state cleared."
    end

    Manager-->>User: "Feature X implemented and merged"
```

---

## Protocol System

### Protocol Loading Flow

```mermaid
flowchart TD
    subgraph "Protocol Installation"
        A[hyperclaude start] --> B{protocols/ exists?}
        B -->|No| C[Copy templates/protocols/*.md<br/>to ~/.hyperclaude/protocols/]
        B -->|Yes| D[Skip installation]
        C --> D
    end

    subgraph "Protocol Selection"
        E[hyperclaude protocol git-branch] --> F{Protocol file exists?}
        F -->|Yes| G[Write 'git-branch' to state/protocol]
        F -->|No| H[Error: Protocol not found]
        G --> I[Protocol active]
    end

    subgraph "Protocol Usage"
        J[hyperclaude send 0 'task'] --> K[Read state/protocol]
        K --> L[Get protocol name]
        L --> M[Build minimal preamble]
        M --> N["W0 | {protocol} | {phase}<br/>Task: {task}<br/>Protocol: {path}"]
        N --> O[Send to worker via tmux]
    end

    subgraph "Worker Protocol Reading"
        P[Worker receives task] --> Q[Parse protocol path from preamble]
        Q --> R[Read ~/.hyperclaude/protocols/{name}.md]
        R --> S[Cache protocol instructions]
        S --> T[Execute according to protocol]
    end
```

### Protocol File Structure

```mermaid
graph TD
    subgraph "Protocol File Structure"
        TITLE["# Protocol Name"]

        subgraph "Overview Section"
            OVERVIEW[Description of workflow]
        end

        subgraph "Phases Section"
            PHASES["## Phases"]
            P1["- **phase1** - Description"]
            P2["- **phase2** - Description"]
            P3["- **phaseN** - Description"]
        end

        subgraph "Worker Actions Section"
            WORKER["## Worker Actions"]
            W_TASK["### On Task Receipt"]
            W_STEPS["1. Step 1<br/>2. Step 2<br/>3. hyperclaude done"]
            W_ERROR["### On Error"]
            W_ERR_STEPS["hyperclaude done --error 'msg'"]
        end

        subgraph "Manager Actions Section"
            MANAGER["## Manager Actions"]
            M_SETUP["### Setup"]
            M_SEND["### Send Tasks"]
            M_WAIT["### Wait and Process"]
        end

        subgraph "State Format Section"
            STATE["## State Format"]
            STATE_FIELDS["Worker state includes:<br/>- status<br/>- branch<br/>- files<br/>- error"]
        end
    end

    TITLE --> OVERVIEW
    OVERVIEW --> PHASES
    PHASES --> P1 --> P2 --> P3
    P3 --> WORKER
    WORKER --> W_TASK --> W_STEPS
    W_STEPS --> W_ERROR --> W_ERR_STEPS
    W_ERR_STEPS --> MANAGER
    MANAGER --> M_SETUP --> M_SEND --> M_WAIT
    M_WAIT --> STATE --> STATE_FIELDS
```

---

## State Management

### Worker State Lifecycle

```mermaid
stateDiagram-v2
    [*] --> ready: Swarm starts / clear

    ready --> working: hyperclaude send
    working --> complete: hyperclaude done
    working --> error: hyperclaude done --error

    complete --> ready: hyperclaude clear
    error --> ready: hyperclaude clear

    note right of ready
        state/workers/N.json:
        {"status": "ready"}
    end note

    note right of working
        state/workers/N.json:
        {"status": "working",
         "assignment": "task..."}
    end note

    note right of complete
        state/workers/N.json:
        {"status": "complete",
         "branch": "...",
         "files": [...]}
    end note

    note right of error
        state/workers/N.json:
        {"status": "error",
         "error": "message"}
    end note
```

### State File Interactions

```mermaid
flowchart TD
    subgraph "State Writers"
        SEND[hyperclaude send]
        DONE[hyperclaude done]
        CLEAR[hyperclaude clear]
        PROTO[hyperclaude protocol]
        PHASE[hyperclaude phase]
    end

    subgraph "State Files"
        PROTOCOL[state/protocol]
        PHASEFILE[state/phase]
        W0[state/workers/0.json]
        W1[state/workers/1.json]
        WN[state/workers/N.json]
    end

    subgraph "State Readers"
        STATE_CMD[hyperclaude state]
        AWAIT[hyperclaude await]
        SEND_READ[hyperclaude send<br/>reads protocol/phase]
    end

    SEND -->|"status: working"| W0
    SEND -->|"status: working"| W1
    SEND -->|"status: working"| WN

    DONE -->|"status: complete/error"| W0
    DONE -->|"status: complete/error"| W1
    DONE -->|"status: complete/error"| WN

    CLEAR -->|"delete all"| W0
    CLEAR -->|"delete all"| W1
    CLEAR -->|"delete all"| WN
    CLEAR -->|"delete"| PROTOCOL
    CLEAR -->|"delete"| PHASEFILE

    PROTO -->|"write"| PROTOCOL
    PHASE -->|"write"| PHASEFILE

    W0 & W1 & WN -->|"read"| STATE_CMD
    PROTOCOL & PHASEFILE -->|"read"| SEND_READ
```

---

## Trigger System

### Trigger Flow

```mermaid
flowchart TD
    subgraph "Trigger Creation"
        W0_DONE[Worker 0: hyperclaude done]
        W1_DONE[Worker 1: hyperclaude done]
        W2_DONE[Worker 2: hyperclaude done]
        WN_DONE[Worker N: hyperclaude done]
    end

    subgraph "Trigger Files"
        T0[triggers/worker-0-done]
        T1[triggers/worker-1-done]
        T2[triggers/worker-2-done]
        TN[triggers/worker-N-done]
        TALL[triggers/all-done]
    end

    subgraph "Trigger Checker"
        CHECK{All worker-*-done<br/>files exist?}
    end

    subgraph "Trigger Consumer"
        AWAIT[hyperclaude await all-done]
        POLL[Poll every 0.5s]
        FOUND[Trigger found!]
    end

    W0_DONE -->|"touch"| T0
    W1_DONE -->|"touch"| T1
    W2_DONE -->|"touch"| T2
    WN_DONE -->|"touch"| TN

    T0 & T1 & T2 & TN --> CHECK
    CHECK -->|Yes| TALL
    CHECK -->|No| CHECK

    AWAIT --> POLL
    POLL -->|"Check file exists"| TALL
    TALL -->|"exists"| FOUND
    POLL -->|"not found"| POLL
```

### Trigger Types

```mermaid
graph LR
    subgraph "Worker Triggers"
        WT0[worker-0-done]
        WT1[worker-1-done]
        WT2[worker-2-done]
        WTN[worker-N-done]
    end

    subgraph "Aggregate Triggers"
        ALL[all-done<br/>Auto-created when all workers done]
    end

    subgraph "Event Triggers"
        CONFLICT[conflict<br/>File edit conflict detected]
    end

    WT0 & WT1 & WT2 & WTN -->|"Check all exist"| ALL

    style ALL fill:#90EE90
    style CONFLICT fill:#FFB6C1
```

---

## Protocol Workflows

### Default Protocol Workflow

```mermaid
sequenceDiagram
    autonumber
    participant M as Manager
    participant CLI as hyperclaude
    participant W0 as Worker 0
    participant W1 as Worker 1
    participant FS as File System

    M->>CLI: hyperclaude protocol default
    M->>CLI: hyperclaude phase working

    par Send tasks
        M->>CLI: hyperclaude send 0 "Fix bug in parser"
        CLI->>W0: Task with protocol reference
        and
        M->>CLI: hyperclaude send 1 "Update documentation"
        CLI->>W1: Task with protocol reference
    end

    par Workers execute
        Note over W0: 1. Read protocol<br/>2. Fix bug<br/>3. Lock files if editing
        W0->>CLI: hyperclaude lock src/parser.py
        Note over W0: 4. Make changes
        W0->>CLI: hyperclaude unlock
        W0->>CLI: hyperclaude done --files src/parser.py
        CLI->>FS: Create worker-0-done

        and

        Note over W1: 1. Read protocol<br/>2. Update docs
        W1->>CLI: hyperclaude done --files README.md
        CLI->>FS: Create worker-1-done
    end

    CLI->>FS: Check all done → Create all-done

    M->>CLI: hyperclaude await all-done
    CLI-->>M: All workers done

    M->>CLI: hyperclaude results
    M->>CLI: hyperclaude clear
```

### Git-Branch Protocol Workflow

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant M as Manager
    participant CLI as hyperclaude
    participant W0 as Worker 0
    participant W1 as Worker 1
    participant W2 as Worker 2
    participant Git as Git Repository
    participant FS as File System

    U->>M: "Add auth, rate limiting, and tests"

    rect rgb(240, 248, 255)
        Note over M,CLI: Setup Phase
        M->>CLI: hyperclaude protocol git-branch
        M->>CLI: hyperclaude phase assign
    end

    rect rgb(255, 248, 240)
        Note over M,W2: Task Distribution
        M->>CLI: hyperclaude send 0 "Implement auth"
        M->>CLI: hyperclaude send 1 "Add rate limiting"
        M->>CLI: hyperclaude send 2 "Write integration tests"
        M->>CLI: hyperclaude phase working
    end

    rect rgb(240, 255, 240)
        Note over W0,Git: Worker 0: Auth
        W0->>Git: git checkout -b worker-0-auth
        Note over W0: Implement auth module
        W0->>Git: git add . && git commit -m "Add auth"
        W0->>Git: git push -u origin worker-0-auth
        W0->>CLI: hyperclaude done --branch worker-0-auth
        CLI->>FS: Create worker-0-done
    end

    rect rgb(255, 240, 255)
        Note over W1,Git: Worker 1: Rate Limiting
        W1->>Git: git checkout -b worker-1-ratelimit
        Note over W1: Implement rate limiting
        W1->>Git: git add . && git commit -m "Add rate limit"
        W1->>Git: git push -u origin worker-1-ratelimit
        W1->>CLI: hyperclaude done --branch worker-1-ratelimit
        CLI->>FS: Create worker-1-done
    end

    rect rgb(255, 255, 240)
        Note over W2,Git: Worker 2: Tests
        W2->>Git: git checkout -b worker-2-tests
        Note over W2: Write integration tests
        W2->>Git: git add . && git commit -m "Add tests"
        W2->>Git: git push -u origin worker-2-tests
        W2->>CLI: hyperclaude done --branch worker-2-tests
        CLI->>FS: Create worker-2-done
    end

    CLI->>FS: All done → Create all-done

    rect rgb(240, 240, 255)
        Note over M,Git: Merge Phase
        M->>CLI: hyperclaude await all-done
        CLI-->>M: Complete
        M->>CLI: hyperclaude phase merging

        M->>CLI: hyperclaude state
        Note over M: Review branches: worker-0-auth,<br/>worker-1-ratelimit, worker-2-tests

        M->>Git: git merge worker-0-auth
        M->>Git: git merge worker-1-ratelimit
        M->>Git: git merge worker-2-tests
        Note over M: Resolve any conflicts

        M->>CLI: hyperclaude phase done
        M->>CLI: hyperclaude clear
    end

    M-->>U: "All features implemented and merged"
```

### Search Protocol Workflow

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant M as Manager
    participant CLI as hyperclaude
    participant W0 as Worker 0
    participant W1 as Worker 1
    participant W2 as Worker 2
    participant W3 as Worker 3
    participant FS as File System

    U->>M: "Find all security vulnerabilities"

    rect rgb(240, 248, 255)
        Note over M,CLI: Setup
        M->>CLI: hyperclaude protocol search
        M->>CLI: hyperclaude phase searching
    end

    rect rgb(255, 248, 240)
        Note over M,W3: Divide Search Space
        M->>CLI: hyperclaude send 0 "Search src/api/ for SQL injection"
        M->>CLI: hyperclaude send 1 "Search src/auth/ for auth bypass"
        M->>CLI: hyperclaude send 2 "Search src/web/ for XSS"
        M->>CLI: hyperclaude send 3 "Search src/utils/ for command injection"
    end

    par Parallel Search
        rect rgb(240, 255, 240)
            W0->>W0: Search src/api/
            W0->>FS: Write results/worker-0.txt
            W0->>CLI: hyperclaude done
        end

        rect rgb(255, 240, 255)
            W1->>W1: Search src/auth/
            W1->>FS: Write results/worker-1.txt
            W1->>CLI: hyperclaude done
        end

        rect rgb(255, 255, 240)
            W2->>W2: Search src/web/
            W2->>FS: Write results/worker-2.txt
            W2->>CLI: hyperclaude done
        end

        rect rgb(240, 240, 255)
            W3->>W3: Search src/utils/
            W3->>FS: Write results/worker-3.txt
            W3->>CLI: hyperclaude done
        end
    end

    CLI->>FS: Create all-done

    rect rgb(255, 240, 240)
        Note over M,FS: Aggregation Phase
        M->>CLI: hyperclaude await all-done
        M->>CLI: hyperclaude phase aggregating

        M->>CLI: hyperclaude results
        CLI->>FS: Read all results/worker-*.txt
        CLI-->>M: Display all findings

        Note over M: Synthesize findings:<br/>- 3 SQL injection in api/<br/>- 1 auth bypass in auth/<br/>- 5 XSS in web/<br/>- 0 issues in utils/

        M->>CLI: hyperclaude phase done
        M->>CLI: hyperclaude clear
    end

    M-->>U: "Found 9 vulnerabilities across 3 directories"
```

### Review Protocol Workflow

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant M as Manager
    participant CLI as hyperclaude
    participant W0 as Worker 0<br/>(Implementer)
    participant W1 as Worker 1<br/>(Reviewer)
    participant W2 as Worker 2<br/>(Reviewer)
    participant FS as File System

    U->>M: "Implement and review payment processing"

    rect rgb(240, 248, 255)
        Note over M,CLI: Setup
        M->>CLI: hyperclaude protocol review
        M->>CLI: hyperclaude phase implement
    end

    rect rgb(255, 248, 240)
        Note over M,W0: Implementation Phase
        M->>CLI: hyperclaude send 0 "Implement payment processing"
        Note over W0: Implement payment module
        W0->>CLI: hyperclaude done --files src/payment.py src/stripe.py
        CLI->>FS: Create worker-0-done
    end

    M->>CLI: hyperclaude await worker-0-done
    M->>CLI: hyperclaude state
    Note over M: Worker 0 modified: src/payment.py, src/stripe.py

    rect rgb(240, 255, 240)
        Note over M,W2: Review Phase
        M->>CLI: hyperclaude phase review
        M->>CLI: hyperclaude send 1 "Review src/payment.py and src/stripe.py for security"
        M->>CLI: hyperclaude send 2 "Review src/payment.py and src/stripe.py for correctness"
    end

    par Parallel Review
        Note over W1: Security Review
        W1->>W1: Check input validation
        W1->>W1: Check for PCI compliance
        W1->>CLI: hyperclaude done --result "LGTM - no security issues"
        CLI->>FS: Create worker-1-done

        and

        Note over W2: Correctness Review
        W2->>W2: Check error handling
        W2->>W2: Check edge cases
        W2->>CLI: hyperclaude done --error "Missing null check line 45"
        CLI->>FS: Create worker-2-done
    end

    CLI->>FS: Create all-done

    rect rgb(255, 240, 255)
        Note over M,W0: Revision Phase
        M->>CLI: hyperclaude await all-done
        M->>CLI: hyperclaude state
        Note over M: W1: approved, W2: changes requested

        M->>CLI: hyperclaude phase revise
        M->>CLI: hyperclaude results
        Note over M: Feedback: "Missing null check line 45"

        M->>CLI: hyperclaude clear
        M->>CLI: hyperclaude send 0 "Fix: Add null check at line 45 in src/payment.py"

        Note over W0: Fix the issue
        W0->>CLI: hyperclaude done --files src/payment.py
    end

    rect rgb(255, 255, 240)
        Note over M,W1: Re-review
        M->>CLI: hyperclaude phase review
        M->>CLI: hyperclaude send 2 "Re-review the fix in src/payment.py"

        Note over W2: Verify fix
        W2->>CLI: hyperclaude done --result "LGTM - fix verified"
    end

    rect rgb(240, 240, 255)
        Note over M: Approval
        M->>CLI: hyperclaude phase approved
        M->>CLI: hyperclaude phase done
        M->>CLI: hyperclaude clear
    end

    M-->>U: "Payment processing implemented and reviewed"
```

---

## Token Efficiency

### Before vs After Comparison

```mermaid
graph TB
    subgraph "BEFORE: Verbose Preamble (~150 tokens per task)"
        B1["You are Worker 0 in a HyperClaude swarm."]
        B2["CRITICAL PROTOCOL - Follow these steps:"]
        B3["1. Execute the task below autonomously"]
        B4["2. When complete, run: hyperclaude report --worker 0 'summary'"]
        B5["3. Before editing files, run: hyperclaude lock file1.py"]
        B6["4. After editing, run: hyperclaude unlock --worker 0"]
        B7["5. If another worker has locked a file, report conflict"]
        B8["TASK: Search for TODO comments"]

        B1 --> B2 --> B3 --> B4 --> B5 --> B6 --> B7 --> B8
    end

    subgraph "AFTER: Minimal Preamble (~30 tokens per task)"
        A1["W0 | git-branch | working"]
        A2["Task: Search for TODO comments"]
        A3["Protocol: ~/.hyperclaude/protocols/git-branch.md"]

        A1 --> A2 --> A3
    end

    style B1 fill:#FFB6C1
    style B2 fill:#FFB6C1
    style B3 fill:#FFB6C1
    style B4 fill:#FFB6C1
    style B5 fill:#FFB6C1
    style B6 fill:#FFB6C1
    style B7 fill:#FFB6C1
    style B8 fill:#FFB6C1

    style A1 fill:#90EE90
    style A2 fill:#90EE90
    style A3 fill:#90EE90
```

### Token Flow Comparison

```mermaid
flowchart LR
    subgraph "OLD: Per-Task Token Cost"
        O_PREAMBLE[Preamble<br/>~120 tokens]
        O_TASK[Task<br/>~30 tokens]
        O_TOTAL[Total: ~150 tokens<br/>per task]

        O_PREAMBLE --> O_TASK --> O_TOTAL
    end

    subgraph "NEW: Per-Task Token Cost"
        N_HEADER[Header<br/>~10 tokens]
        N_TASK[Task<br/>~15 tokens]
        N_PATH[Protocol path<br/>~5 tokens]
        N_TOTAL[Total: ~30 tokens<br/>per task]

        N_HEADER --> N_TASK --> N_PATH --> N_TOTAL
    end

    subgraph "Protocol Read: One-Time Cost"
        P_READ[Read protocol file<br/>~200 tokens]
        P_CACHE[Cached for session]

        P_READ --> P_CACHE
    end

    style O_TOTAL fill:#FFB6C1
    style N_TOTAL fill:#90EE90
    style P_CACHE fill:#87CEEB
```

### Savings Calculation

```mermaid
pie title Token Savings Per 10 Tasks
    "Old System (1500 tokens)" : 1500
    "New System (500 tokens)" : 500
```

```mermaid
graph TD
    subgraph "10 Task Comparison"
        OLD["OLD SYSTEM<br/>10 tasks × 150 tokens = 1500 tokens"]
        NEW["NEW SYSTEM<br/>1 protocol read (200) + 10 tasks × 30 = 500 tokens"]
        SAVE["SAVINGS: 67% reduction"]
    end

    OLD --> SAVE
    NEW --> SAVE

    style OLD fill:#FFB6C1
    style NEW fill:#90EE90
    style SAVE fill:#FFD700
```

---

## Data Flow

### Complete Data Flow Diagram

```mermaid
flowchart TD
    subgraph "User Layer"
        USER[Human User]
    end

    subgraph "Manager Layer"
        MANAGER[Manager Claude<br/>Interactive Mode]
    end

    subgraph "CLI Layer"
        CLI_SEND[hyperclaude send]
        CLI_AWAIT[hyperclaude await]
        CLI_STATE[hyperclaude state]
        CLI_DONE[hyperclaude done]
        CLI_LOCK[hyperclaude lock]
    end

    subgraph "tmux Layer"
        TMUX_SEND[send-keys]
        TMUX_CAPTURE[capture-pane]
    end

    subgraph "Worker Layer"
        W0[Worker 0]
        W1[Worker 1]
        WN[Worker N]
    end

    subgraph "File System Layer"
        subgraph "Protocols"
            PROTO[protocols/*.md]
        end

        subgraph "State"
            STATE_P[state/protocol]
            STATE_PH[state/phase]
            STATE_W[state/workers/*.json]
        end

        subgraph "Triggers"
            TRIG[triggers/*-done]
        end

        subgraph "Results"
            RES[results/worker-*.txt]
        end

        subgraph "Locks"
            LOCKS[locks/worker-*.lock]
        end
    end

    USER -->|"Instructions"| MANAGER
    MANAGER -->|"hyperclaude send"| CLI_SEND
    CLI_SEND -->|"Update"| STATE_W
    CLI_SEND -->|"send-keys"| TMUX_SEND
    TMUX_SEND -->|"Message"| W0 & W1 & WN

    W0 & W1 & WN -->|"Read once"| PROTO
    W0 & W1 & WN -->|"hyperclaude done"| CLI_DONE
    CLI_DONE -->|"Update"| STATE_W
    CLI_DONE -->|"Create"| TRIG
    CLI_DONE -->|"Write"| RES

    W0 & W1 & WN -->|"hyperclaude lock"| CLI_LOCK
    CLI_LOCK -->|"Create"| LOCKS

    MANAGER -->|"hyperclaude await"| CLI_AWAIT
    CLI_AWAIT -->|"Poll"| TRIG
    TRIG -->|"Exists"| CLI_AWAIT
    CLI_AWAIT -->|"Complete"| MANAGER

    MANAGER -->|"hyperclaude state"| CLI_STATE
    CLI_STATE -->|"Read"| STATE_W
    CLI_STATE -->|"Display"| MANAGER
```

---

## Security Model

```mermaid
graph TB
    subgraph "Permission Levels"
        subgraph "Manager (Interactive)"
            M[Manager Claude]
            M_PERM[Normal Claude permissions<br/>User approval for sensitive ops]
        end

        subgraph "Workers (Autonomous)"
            W[Worker Claudes]
            W_PERM[--dangerously-skip-permissions<br/>Full autonomous execution]
        end
    end

    subgraph "Rationale"
        M_WHY["Manager: User interacts directly<br/>Needs approval for safety"]
        W_WHY["Workers: Execute delegated tasks<br/>Already approved by manager"]
    end

    subgraph "File Lock Safety"
        LOCK_CHECK{Check for conflicts}
        LOCK_OK[Proceed with edit]
        LOCK_FAIL[Report conflict]
    end

    M --> M_PERM
    W --> W_PERM

    M_PERM --> M_WHY
    W_PERM --> W_WHY

    W -->|"hyperclaude lock"| LOCK_CHECK
    LOCK_CHECK -->|"No conflict"| LOCK_OK
    LOCK_CHECK -->|"File locked"| LOCK_FAIL

    style M_PERM fill:#90EE90
    style W_PERM fill:#FFD700
    style LOCK_FAIL fill:#FFB6C1
```

### Environment Variable Security

```mermaid
flowchart TD
    subgraph "Worker Environment Setup"
        START[Pane created]
        EXPORT["export HYPERCLAUDE_WORKER_ID=N"]
        CLAUDE["claude --dangerously-skip-permissions"]
        READY[Worker ready]
    end

    subgraph "Auto-Detection"
        CMD[hyperclaude done / lock / unlock]
        CHECK{HYPERCLAUDE_WORKER_ID<br/>set?}
        USE_ENV[Use environment value]
        ERROR[Error: Worker ID required]
    end

    START --> EXPORT --> CLAUDE --> READY

    CMD --> CHECK
    CHECK -->|Yes| USE_ENV
    CHECK -->|No| ERROR

    style EXPORT fill:#87CEEB
    style USE_ENV fill:#90EE90
    style ERROR fill:#FFB6C1
```

---

## Command Reference Diagram

```mermaid
graph TD
    subgraph "Swarm Lifecycle"
        START[hyperclaude]
        STOP[hyperclaude stop]
    end

    subgraph "Protocol Management"
        PROTO_SET[hyperclaude protocol NAME]
        PROTO_GET[hyperclaude protocol]
        PROTO_LIST[hyperclaude protocols]
        PHASE_SET[hyperclaude phase NAME]
        PHASE_GET[hyperclaude phase]
    end

    subgraph "Task Management"
        SEND[hyperclaude send N TASK]
        BROADCAST[hyperclaude broadcast TASK]
        AWAIT[hyperclaude await TRIGGER]
        STATE[hyperclaude state]
        RESULTS[hyperclaude results]
        CLEAR[hyperclaude clear]
    end

    subgraph "Worker Commands"
        DONE[hyperclaude done]
        LOCK[hyperclaude lock FILES]
        UNLOCK[hyperclaude unlock]
        LOCKS[hyperclaude locks]
    end

    START -->|"Creates swarm"| PROTO_SET
    PROTO_SET -->|"Set protocol"| SEND
    SEND -->|"Workers execute"| DONE
    DONE -->|"Triggers"| AWAIT
    AWAIT -->|"Check"| STATE
    STATE -->|"Review"| RESULTS
    RESULTS -->|"Reset"| CLEAR
    CLEAR -->|"Next batch"| SEND
    STOP -->|"End session"| START

    style START fill:#90EE90
    style STOP fill:#FFB6C1
    style DONE fill:#FFD700
    style AWAIT fill:#87CEEB
```

---

## Summary

hyperclaude achieves efficient swarm coordination through:

1. **Token Efficiency**: Minimal preambles with protocol file references
2. **Event-Driven**: Trigger files instead of polling
3. **State Management**: JSON-based worker state for extensibility
4. **Security**: Manager with normal permissions, workers with bypass
5. **Flexibility**: Four built-in protocols, custom protocols supported
6. **Simplicity**: File-based coordination, no external dependencies

The architecture prioritizes reducing token usage while maintaining clear coordination between manager and workers.
