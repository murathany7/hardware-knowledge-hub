#!/usr/bin/env node
const { cpSync, existsSync } = require("node:fs");
const { join } = require("node:path");
const [command, directory, ...extra] = process.argv.slice(2);
if (command !== "init" || !directory || extra.length || existsSync(directory)) {
  console.error("Usage: hardware-knowledge-hub init <new-directory>");
  process.exit(1);
}
cpSync(join(__dirname, "hub_package", "template"), directory, { recursive: true });
console.log(`Open ${directory} and run python3 hardware/knowledge/kb.py serve`);
