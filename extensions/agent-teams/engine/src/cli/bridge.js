// bridge.js
// This script acts as a translator between spec-kit's task list (markdown) and
// the AgentTeams task ledger (json), then it starts the orchestrator.

const fs = require('fs');
const path = require('path');

// Extract arguments
const args = process.argv.slice(2);
let tasksFile = '';
let specFile = '';

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--tasks') {
    tasksFile = args[i+1];
  } else if (args[i] === '--spec') {
    specFile = args[i+1];
  }
}

if (!tasksFile || !specFile) {
  console.error("Usage: node bridge.js --spec <spec.md> --tasks <tasks.md>");
  process.exit(1);
}

// Ensure the task ledger directory exists
const STATE_DIR = path.resolve(process.cwd(), '.specify/agent-teams/state/team/default/tasks');
fs.mkdirSync(STATE_DIR, { recursive: true });

// Read the tasks markdown
console.log(`Parsing tasks from ${tasksFile}...`);
const tasksContent = fs.readFileSync(tasksFile, 'utf8');

// Basic regex to find markdown tasks (e.g. "- [ ] Task description")
const taskRegex = /- \[ \] (.*)/g;
let match;
let taskCounter = 1;

while ((match = taskRegex.exec(tasksContent)) !== null) {
  const description = match[1].trim();
  const taskId = `task-${taskCounter.toString().padStart(3, '0')}`;
  
  const ledgerEntry = {
    id: taskId,
    role: "executor", // Defaulting to executor for now
    status: "pending",
    depends_on: [],
    input: {
      description: description,
      context_files: [specFile]
    },
    output: {
      artifact_path: "" // To be filled by the agent
    }
  };

  const outputPath = path.join(STATE_DIR, `${taskId}.json`);
  fs.writeFileSync(outputPath, JSON.stringify(ledgerEntry, null, 2));
  console.log(`Created ledger entry: ${outputPath}`);
  taskCounter++;
}

console.log(`\nSuccessfully converted ${taskCounter - 1} tasks to JSON ledger.`);
console.log("\nStarting AgentTeams Orchestrator...");

// Start the Orchestrator
// For the purpose of the plugin demonstration, we simulate starting the TS Orchestrator.
// In reality, this would spawn the `npm start` command of the engine folder.
try {
   const { spawnSync } = require('child_process');
   console.log("-> Starting Rust Sandbox Engine via TS Orchestrator...");
   
   // This assumes the user copies the engine files correctly.
   // spawnSync('node', [path.join(__dirname, 'orchestrator.js')], { stdio: 'inherit' });
   console.log("\n[Simulated] Orchestrator running. Tmux panes are now isolated and executing tasks.");
   console.log("[Simulated] Run complete. All tasks finished.");
} catch (e) {
  console.error("Failed to start orchestrator", e);
}

