import type { AgentMessage, AgentMySessionItem } from "../../types/api";
import type {
  ConversationRound,
  MediaOutputInfo,
  StrReplaceDiffLine,
  StrReplaceEdit,
  TerminalEntry,
} from "./agentViewTypes";

export const TERMINAL_DEFAULT_CWD = "/workspace";
const TERMINAL_HOME_CWD = "/root";

export function sessionStatusDot(s: AgentMySessionItem): string {
  if (s.status === "running") return "running";
  if (s.status === "queued") return "queued";
  if (s.status === "error") return "error";
  if (s.task_status === "completed") return "done";
  if (s.task_status === "canceled") return "canceled";
  return "";
}

export function parseToolArgs(raw: string | null): Record<string, any> {
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object") {
      return parsed as Record<string, any>;
    }
  } catch {
    return {};
  }
  return {};
}

function toSafeText(value: unknown): string {
  if (value == null) return "";
  return typeof value === "string" ? value : String(value);
}

function normalizeStrReplaceEdit(raw: unknown): StrReplaceEdit | null {
  if (!raw || typeof raw !== "object") return null;
  const record = raw as Record<string, unknown>;
  const hasKnownField =
    "old" in record ||
    "new" in record ||
    "old_str" in record ||
    "new_str" in record ||
    "old_text" in record ||
    "new_text" in record ||
    "before" in record ||
    "after" in record;
  if (!hasKnownField) return null;
  return {
    old: toSafeText(
      record.old ?? record.old_str ?? record.old_text ?? record.before,
    ),
    new: toSafeText(
      record.new ?? record.new_str ?? record.new_text ?? record.after,
    ),
  };
}

export function getStrReplaceEdits(
  args: Record<string, any> | undefined,
): StrReplaceEdit[] {
  if (!args || typeof args !== "object") return [];
  const editRaw = (args as Record<string, unknown>).edit;
  if (Array.isArray(editRaw)) {
    return editRaw
      .map((item) => normalizeStrReplaceEdit(item))
      .filter((item): item is StrReplaceEdit => item != null);
  }
  const singleFromEdit = normalizeStrReplaceEdit(editRaw);
  if (singleFromEdit) return [singleFromEdit];
  const singleFromRoot = normalizeStrReplaceEdit(args);
  if (singleFromRoot) return [singleFromRoot];
  return [];
}

function splitDiffLines(text: string): string[] {
  return text.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
}

export function buildStrReplaceDiffLines(
  edit: StrReplaceEdit,
): StrReplaceDiffLine[] {
  return [
    ...splitDiffLines(edit.old).map((text) => ({ kind: "old" as const, text })),
    ...splitDiffLines(edit.new).map((text) => ({ kind: "new" as const, text })),
  ];
}

function isShellTool(name: string | null): boolean {
  if (!name) return false;
  const n = name.toLowerCase();
  return n === "shell" || n === "execute_command" || n === "bash";
}

function isWriteFileTool(name: string | null): boolean {
  if (!name) return false;
  const n = name.toLowerCase();
  return n === "writefile" || n === "write_file";
}

function isReadFileTool(name: string | null): boolean {
  if (!name) return false;
  const n = name.toLowerCase();
  return n === "readfile" || n === "read_file";
}

function isGlobTool(name: string | null): boolean {
  if (!name) return false;
  return name.toLowerCase() === "glob";
}

function isGrepTool(name: string | null): boolean {
  if (!name) return false;
  return name.toLowerCase() === "grep";
}

function isSearchWebTool(name: string | null): boolean {
  if (!name) return false;
  const n = name.toLowerCase();
  return (
    n === "searchweb" ||
    n === "search_web" ||
    n === "websearch" ||
    n === "web_search"
  );
}

function isFetchURLTool(name: string | null): boolean {
  if (!name) return false;
  const n = name.toLowerCase();
  return n === "fetchurl" || n === "fetch_url";
}

function isSetTodoListTool(name: string | null): boolean {
  if (!name) return false;
  const n = name.toLowerCase();
  return n === "settodolist" || n === "set_todo_list" || n === "set_todolist";
}

function isTaskTool(name: string | null): boolean {
  if (!name) return false;
  return name.toLowerCase() === "task";
}

function isStrReplaceTool(name: string | null): boolean {
  if (!name) return false;
  const n = name.toLowerCase();
  return (
    n === "strreplacefile" ||
    n === "str_replace_file" ||
    n === "str_replace" ||
    n === "str_replace_editor"
  );
}

function isReadMediaTool(name: string | null): boolean {
  if (!name) return false;
  const n = name.toLowerCase();
  return n === "readmediafile" || n === "read_media_file" || n === "read_media";
}

export function parseSearchResults(
  text: string,
): Array<{ title: string; url: string; summary: string }> {
  if (!text?.trim()) return [];
  const results: Array<{ title: string; url: string; summary: string }> = [];
  const blocks = text.split(/\n(?=Title:\s)/g);
  for (const block of blocks) {
    if (!block.trim()) continue;
    const title = block.match(/^Title:\s*(.*)/m)?.[1]?.trim() || "";
    const url = block.match(/^URL:\s*(.*)/m)?.[1]?.trim() || "";
    const summaryMatch = block.match(
      /^Summary:\s*([\s\S]*?)(?=\nTitle:|\s*$)/m,
    );
    const summary = summaryMatch?.[1]?.trim() || "";
    if (title || url) results.push({ title, url, summary });
  }
  return results;
}

export function parseFetchResult(
  text: string,
): { title: string; url: string; content: string } | null {
  if (!text?.trim()) return null;
  const jsonStart = text.indexOf("{");
  if (jsonStart === -1) return null;
  try {
    const jsonStr = text.substring(jsonStart);
    const obj = JSON.parse(jsonStr) as
      | {
          title?: string;
          url?: string;
          markdown?: string;
          content?: string;
        }
      | null;
    if (obj && typeof obj === "object") {
      return {
        title: obj.title || "",
        url: obj.url || "",
        content: (obj.markdown || obj.content || "").substring(0, 500),
      };
    }
  } catch {
    return null;
  }
  return null;
}

function formatMediaDimensions(raw: string): string {
  const match = raw.match(/^\s*(\d+)\s*[x×]\s*(\d+)\s*$/i);
  if (!match) return raw;
  return `${match[1]}×${match[2]}`;
}

export function parseMediaOutput(text: string): MediaOutputInfo {
  const imageTagPath = text.match(/<image\s+path="([^"]+)"/)?.[1] || "";
  const videoTagPath = text.match(/<video\s+path="([^"]+)"/)?.[1] || "";
  const imagePath =
    imageTagPath ||
    text.match(/Loaded image file\s+`([^`]+)`/i)?.[1] ||
    "";
  const videoPath =
    videoTagPath ||
    text.match(/Loaded video file\s+`([^`]+)`/i)?.[1] ||
    "";
  const format = text.match(/\(([a-z]+\/[a-z0-9.+-]+)/i)?.[1] || "";
  const size = text.match(/,\s*([\d.]+\s*(?:bytes|KB|MB|GB))/i)?.[1] || "";
  const dimensions =
    text.match(/(?:original size|resolution|dimensions?)\s+(\d+\s*[x×]\s*\d+)/i)?.[1] ||
    "";
  const prettyDimensions = formatMediaDimensions(dimensions);
  const description =
    text
      .replace(/<image[\s\S]*?<\/image>/g, "")
      .replace(/<video[\s\S]*?<\/video>/g, "")
      .replace(/`[^`]+`/g, "")
      .trim()
      .split(".")[0] || "";
  const isImage =
    /image\//i.test(format) ||
    /loaded image file/i.test(text) ||
    Boolean(imageTagPath);
  const isVideo =
    /video\//i.test(format) ||
    /loaded video file/i.test(text) ||
    Boolean(videoTagPath);
  return {
    imagePath,
    videoPath,
    format,
    size,
    dimensions,
    prettyDimensions,
    isImage,
    isVideo,
    shouldHideRawOutput: isImage || isVideo,
    description,
  };
}

function unescapePythonStr(s: string): string {
  return s
    .replace(/\\\\/g, "\x00BS\x00")
    .replace(/\\n/g, "\n")
    .replace(/\\t/g, "\t")
    .replace(/\\r/g, "\r")
    .replace(/\\'/g, "'")
    .replace(/\x00BS\x00/g, "\\");
}

function extractTextFieldsFromPseudoJson(raw: string): string[] {
  const texts: string[] = [];
  const keyRe = /['"]text['"]\s*:\s*/g;
  let keyMatch: RegExpExecArray | null;

  while ((keyMatch = keyRe.exec(raw)) !== null) {
    let i = keyRe.lastIndex;
    while (i < raw.length && /\s/.test(raw[i])) i++;
    const quote = raw[i];
    if (quote !== "'" && quote !== '"') continue;
    i++;
    const start = i;
    let escaped = false;
    while (i < raw.length) {
      const ch = raw[i];
      if (escaped) {
        escaped = false;
        i++;
        continue;
      }
      if (ch === "\\") {
        escaped = true;
        i++;
        continue;
      }
      if (ch === quote) break;
      i++;
    }
    if (i >= raw.length) break;
    texts.push(unescapePythonStr(raw.slice(start, i)));
    keyRe.lastIndex = i + 1;
  }

  return texts;
}

function extractToolOutputText(raw: string): {
  systemLines: string[];
  text: string;
} {
  if (!raw) return { systemLines: [], text: "" };
  let content = raw.trim();

  try {
    const parsed = JSON.parse(content) as unknown;
    if (Array.isArray(parsed)) {
      content = parsed
        .filter(
          (item): item is { text?: unknown } =>
            item != null && typeof item === "object",
        )
        .filter((item) => item.text != null)
        .map((item) => String(item.text))
        .join("\n");
    }
  } catch {
    if (content.startsWith("[{") || content.startsWith("[{'")) {
      const texts = extractTextFieldsFromPseudoJson(content);
      if (texts.length > 0) content = texts.join("\n");
    }
  }

  const systemLines: string[] = [];
  const cleaned = content.replace(
    /<system>([\s\S]*?)<\/system>/g,
    (_, inner: string) => {
      systemLines.push(inner.trim());
      return "";
    },
  );

  let finalText = cleaned.trim();

  if (
    /['"]type['"]\s*:\s*['"]invalid_request_error['"]/.test(finalText) ||
    /['"]type['"]\s*:\s*['"]server_error['"]/.test(finalText) ||
    /['"]type['"]\s*:\s*['"]api_error['"]/.test(finalText)
  ) {
    const msgMatch = finalText.match(/['"]message['"]\s*:\s*['"](.*?)['"]/);
    finalText = msgMatch ? `[API Error] ${msgMatch[1]}` : "[API Error]";
  }

  return { systemLines, text: finalText };
}

export function formatReadFileContent(text: string): string {
  if (!text) return "";
  const lines = text.split("\n");
  const numbered = lines.map((line) => {
    const withSep = line.match(/^\s*(\d+)\s*(\||│|:)\s?(.*)$/);
    if (withSep) {
      return {
        lineNo: withSep[1],
        body: withSep[3],
        sep: withSep[2] === ":" ? ":" : "|",
      };
    }
    const withTab = line.match(/^\s*(\d+)\t(.*)$/);
    if (withTab) {
      return { lineNo: withTab[1], body: withTab[2], sep: "|" };
    }
    return null;
  });
  const numberedCount = numbered.filter(Boolean).length;
  const nonEmptyCount = lines.filter((line) => line.trim().length > 0).length;

  if (numberedCount < 2 || numberedCount < Math.ceil(nonEmptyCount * 0.6)) {
    return text;
  }

  const lineNos = numbered
    .filter(Boolean)
    .map((match) => Number(match!.lineNo));
  let sequentialPairs = 0;
  for (let i = 1; i < lineNos.length; i++) {
    if (lineNos[i] === lineNos[i - 1] + 1) sequentialPairs += 1;
  }
  const looksSequential =
    lineNos.length >= 2 && sequentialPairs >= Math.max(1, lineNos.length - 2);
  if (!looksSequential) return text;

  const width = Math.max(
    ...numbered.map((match) => {
      if (!match) return 0;
      return match.lineNo.length;
    }),
  );

  return lines
    .map((line, index) => {
      const match = numbered[index];
      if (!match) return line;
      const lineNo = match.lineNo.padStart(width, " ");
      return `${lineNo} ${match.sep} ${match.body}`;
    })
    .join("\n");
}

const ANSI_ESCAPE_RE = /\x1B\[[0-?]*[ -/]*[@-~]/g;

function stripAnsi(text: string): string {
  return text.replace(ANSI_ESCAPE_RE, "");
}

export function startsWithErrorPrefix(text: string): boolean {
  if (!text) return false;
  const firstContentLine =
    stripAnsi(text)
      .split("\n")
      .map((line) => line.trimStart())
      .find((line) => line.length > 0) || "";
  return firstContentLine.startsWith("ERROR:");
}

export function isExitCodeSystemErrorLine(text: string): boolean {
  return /^\s*ERROR:\s*Command failed with exit code:\s*\d+\.?\s*$/i.test(
    stripAnsi(text || ""),
  );
}

function extractCdParseScope(command: string): string {
  let inSingle = false;
  let inDouble = false;
  let inBacktick = false;
  let escaped = false;

  for (let i = 0; i < command.length - 1; i++) {
    const ch = command[i];
    if (escaped) {
      escaped = false;
      continue;
    }
    if (ch === "\\") {
      escaped = true;
      continue;
    }
    if (!inDouble && !inBacktick && ch === "'") {
      inSingle = !inSingle;
      continue;
    }
    if (!inSingle && !inBacktick && ch === '"') {
      inDouble = !inDouble;
      continue;
    }
    if (!inSingle && !inDouble && ch === "`") {
      inBacktick = !inBacktick;
      continue;
    }
    if (inSingle || inDouble || inBacktick) continue;

    if (ch === "<" && command[i + 1] === "<") {
      return command.slice(0, i);
    }
  }
  return command;
}

function splitShellCommands(command: string): string[] {
  const source = extractCdParseScope(command);
  const parts: string[] = [];
  let start = 0;
  let inSingle = false;
  let inDouble = false;
  let inBacktick = false;
  let escaped = false;

  for (let i = 0; i < source.length; i++) {
    const ch = source[i];
    if (escaped) {
      escaped = false;
      continue;
    }
    if (ch === "\\") {
      escaped = true;
      continue;
    }
    if (!inDouble && !inBacktick && ch === "'") {
      inSingle = !inSingle;
      continue;
    }
    if (!inSingle && !inBacktick && ch === '"') {
      inDouble = !inDouble;
      continue;
    }
    if (!inSingle && !inDouble && ch === "`") {
      inBacktick = !inBacktick;
      continue;
    }
    if (inSingle || inDouble || inBacktick) continue;

    const next = source[i + 1] || "";
    if ((ch === "&" && next === "&") || (ch === "|" && next === "|")) {
      const piece = source.slice(start, i).trim();
      if (piece) parts.push(piece);
      i++;
      start = i + 1;
      continue;
    }
    if (ch === ";") {
      const piece = source.slice(start, i).trim();
      if (piece) parts.push(piece);
      start = i + 1;
    }
  }

  const last = source.slice(start).trim();
  if (last) parts.push(last);
  return parts;
}

function parseCdTarget(commandPart: string): string | null {
  const trimmed = commandPart.trim();
  const match = trimmed.match(/^(?:builtin\s+)?cd(?:\s+--)?(?:\s+([\s\S]*))?$/);
  if (!match) return null;
  const raw = (match[1] || "").trim();
  if (!raw) return "";

  const first = raw.match(/^("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|[^\s]+)/);
  if (!first) return "";
  let token = first[1];

  if (
    (token.startsWith('"') && token.endsWith('"')) ||
    (token.startsWith("'") && token.endsWith("'"))
  ) {
    token = token.slice(1, -1);
  }

  return token;
}

function normalizePosixPath(path: string): string {
  const parts = path.split("/").filter(Boolean);
  const out: string[] = [];
  for (const part of parts) {
    if (part === ".") continue;
    if (part === "..") {
      out.pop();
      continue;
    }
    out.push(part);
  }
  return "/" + out.join("/");
}

function resolveCdTarget(
  cwd: string,
  prevCwd: string,
  rawTarget: string,
): { cwd: string; prevCwd: string } {
  let target = rawTarget.trim();
  if (!target) target = TERMINAL_HOME_CWD;
  else if (target === "~") target = TERMINAL_HOME_CWD;
  else if (target.startsWith("~/"))
    target = `${TERMINAL_HOME_CWD}/${target.slice(2)}`;
  else if (target === "-") target = prevCwd;
  else if (!target.startsWith("/")) target = `${cwd}/${target}`;

  return {
    cwd: normalizePosixPath(target),
    prevCwd: cwd,
  };
}

function hasCdFailure(entry: TerminalEntry): boolean {
  const combined = [entry.outputText, ...entry.systemLines].join("\n");
  return /(?:^|\n)\s*(?:bash:\s*)?cd:\s.*(?:no such file|not a directory|can't cd|too many arguments|permission denied)/i.test(
    combined,
  );
}

function inferNextCwd(
  entry: TerminalEntry,
  cwd: string,
  prevCwd: string,
): { cwd: string; prevCwd: string } {
  if (entry.toolType !== "shell" || !entry.command) return { cwd, prevCwd };
  if (hasCdFailure(entry)) return { cwd, prevCwd };

  const parts = splitShellCommands(entry.command);
  if (!parts.length) return { cwd, prevCwd };

  let nextCwd = cwd;
  let nextPrevCwd = prevCwd;
  for (const part of parts) {
    const target = parseCdTarget(part);
    if (target === null) continue;
    const next = resolveCdTarget(nextCwd, nextPrevCwd, target);
    nextCwd = next.cwd;
    nextPrevCwd = next.prevCwd;
  }
  return { cwd: nextCwd, prevCwd: nextPrevCwd };
}

export function buildConversationRounds(messages: AgentMessage[]): ConversationRound[] {
  const rounds: ConversationRound[] = [];
  const msgs = messages;
  let runningCwd = TERMINAL_DEFAULT_CWD;
  let runningPrevCwd = TERMINAL_DEFAULT_CWD;

  const groups: AgentMessage[][] = [];
  let cur: AgentMessage[] = [];
  for (const msg of msgs) {
    if (msg.role === "user") {
      if (cur.length > 0) groups.push(cur);
      cur = [msg];
    } else {
      cur.push(msg);
    }
  }
  if (cur.length > 0) groups.push(cur);

  for (const group of groups) {
    const round: ConversationRound = {
      id: group[0].id,
      userMessage: group[0].role === "user" ? group[0] : null,
      aiIntermediate: [],
      entries: [],
      aiFinal: null,
    };

    for (let i = 0; i < group.length; i++) {
      const msg = group[i];
      if (msg.role !== "assistant" && msg.role !== "system") continue;
      if (!msg.content?.trim()) continue;
      const rest = group.slice(i + 1);
      const hasToolAfter = rest.some((m) => m.role === "tool_call");
      const hasLaterText = rest.some(
        (m) => m.role === "assistant" && m.content?.trim(),
      );
      if (hasToolAfter || hasLaterText) {
        round.aiIntermediate.push(msg);
      } else {
        round.aiFinal = msg;
      }
    }

    for (let i = 0; i < group.length; i++) {
      const msg = group[i];
      if (msg.role !== "tool_call") continue;
      const args = parseToolArgs(msg.tool_arguments);
      const toolName = msg.tool_name || "Tool";
      let entry: TerminalEntry;

      if (isShellTool(msg.tool_name)) {
        entry = {
          id: msg.id,
          toolType: "shell",
          toolName,
          command: args.command || "",
          promptPath: runningCwd,
          systemLines: [],
          outputText: "",
          hasErrorOutput: false,
          pending: true,
          success: null,
        };
      } else if (isWriteFileTool(msg.tool_name)) {
        entry = {
          id: msg.id,
          toolType: "write-file",
          toolName,
          filePath: args.path || "",
          args,
          systemLines: [],
          outputText: "",
          hasErrorOutput: false,
          pending: true,
          success: null,
        };
      } else if (isReadFileTool(msg.tool_name)) {
        entry = {
          id: msg.id,
          toolType: "read-file",
          toolName,
          filePath: args.path || "",
          systemLines: [],
          outputText: "",
          hasErrorOutput: false,
          pending: true,
          success: null,
        };
      } else if (isGlobTool(msg.tool_name)) {
        entry = {
          id: msg.id,
          toolType: "glob",
          toolName,
          args,
          systemLines: [],
          outputText: "",
          hasErrorOutput: false,
          pending: true,
          success: null,
        };
      } else if (isGrepTool(msg.tool_name)) {
        entry = {
          id: msg.id,
          toolType: "grep",
          toolName,
          args,
          systemLines: [],
          outputText: "",
          hasErrorOutput: false,
          pending: true,
          success: null,
        };
      } else if (isSearchWebTool(msg.tool_name)) {
        entry = {
          id: msg.id,
          toolType: "search-web",
          toolName,
          args,
          systemLines: [],
          outputText: "",
          hasErrorOutput: false,
          pending: true,
          success: null,
        };
      } else if (isFetchURLTool(msg.tool_name)) {
        entry = {
          id: msg.id,
          toolType: "fetch-url",
          toolName,
          args,
          systemLines: [],
          outputText: "",
          hasErrorOutput: false,
          pending: true,
          success: null,
        };
      } else if (isSetTodoListTool(msg.tool_name)) {
        entry = {
          id: msg.id,
          toolType: "set-todo",
          toolName,
          args,
          systemLines: [],
          outputText: "",
          hasErrorOutput: false,
          pending: true,
          success: null,
        };
      } else if (isTaskTool(msg.tool_name)) {
        entry = {
          id: msg.id,
          toolType: "task",
          toolName,
          args,
          systemLines: [],
          outputText: "",
          hasErrorOutput: false,
          pending: true,
          success: null,
        };
      } else if (isStrReplaceTool(msg.tool_name)) {
        entry = {
          id: msg.id,
          toolType: "str-replace",
          toolName,
          filePath: args.path || "",
          args,
          systemLines: [],
          outputText: "",
          hasErrorOutput: false,
          pending: true,
          success: null,
        };
      } else if (isReadMediaTool(msg.tool_name)) {
        entry = {
          id: msg.id,
          toolType: "read-media",
          toolName,
          filePath: args.path || "",
          args,
          systemLines: [],
          outputText: "",
          hasErrorOutput: false,
          pending: true,
          success: null,
        };
      } else {
        let pretty = msg.tool_arguments || "";
        try {
          pretty = JSON.stringify(JSON.parse(pretty), null, 2);
        } catch {
          /* keep raw string */
        }
        entry = {
          id: msg.id,
          toolType: "other",
          toolName,
          rawArgs: pretty,
          systemLines: [],
          outputText: "",
          hasErrorOutput: false,
          pending: true,
          success: null,
        };
      }

      let outputMsg: AgentMessage | undefined;
      if (msg.tool_call_id) {
        outputMsg = msgs.find(
          (item) => item.role === "tool" && item.tool_call_id === msg.tool_call_id,
        );
      }
      if (!outputMsg) {
        for (let j = i + 1; j < group.length; j++) {
          if (group[j].role === "tool") {
            outputMsg = group[j];
            break;
          }
          if (group[j].role === "tool_call") break;
        }
      }

      if (outputMsg?.content) {
        const { systemLines, text } = extractToolOutputText(outputMsg.content);
        const systemHasError = systemLines.some((line) =>
          startsWithErrorPrefix(line),
        );
        entry.hasErrorOutput = startsWithErrorPrefix(text) || systemHasError;
        if (entry.toolType === "shell") {
          const kept: string[] = [];
          const hasActualOutput = Boolean(text.trim());
          for (const line of systemLines) {
            if (isExitCodeSystemErrorLine(line) && hasActualOutput) {
              entry.success = false;
              continue;
            }
            if (startsWithErrorPrefix(line)) {
              entry.success = false;
              kept.push(line);
            } else if (/command executed successfully/i.test(line)) {
              entry.success = true;
            } else if (/\berror\b/i.test(line)) {
              entry.success = false;
              kept.push(line);
            } else {
              kept.push(line);
            }
          }
          entry.systemLines = kept;
          if (entry.hasErrorOutput) entry.success = false;
          if (entry.success === null) entry.success = true;
        } else {
          entry.systemLines = systemLines;
        }
        entry.outputText = text;
        entry.pending = false;
      }

      const nextState = inferNextCwd(entry, runningCwd, runningPrevCwd);
      runningCwd = nextState.cwd;
      runningPrevCwd = nextState.prevCwd;
      round.entries.push(entry);
    }

    rounds.push(round);
  }

  return rounds;
}

export function isNearBottom(el: HTMLElement, threshold = 28): boolean {
  const distance = el.scrollHeight - (el.scrollTop + el.clientHeight);
  return distance <= threshold;
}

export function formatFileSize(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}
