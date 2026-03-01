import type { AgentMessage } from "../../types/api";

export interface StrReplaceEdit {
  old: string;
  new: string;
}

export interface StrReplaceDiffLine {
  kind: "old" | "new";
  text: string;
}

export interface MediaOutputInfo {
  imagePath: string;
  format: string;
  size: string;
  dimensions: string;
  prettyDimensions: string;
  isImage: boolean;
  description: string;
}

export interface TerminalEntry {
  id: number;
  toolType:
    | "shell"
    | "write-file"
    | "read-file"
    | "glob"
    | "grep"
    | "search-web"
    | "fetch-url"
    | "set-todo"
    | "task"
    | "str-replace"
    | "read-media"
    | "other";
  toolName: string;
  command?: string;
  promptPath?: string;
  filePath?: string;
  rawArgs?: string;
  args?: Record<string, any>;
  systemLines: string[];
  outputText: string;
  hasErrorOutput: boolean;
  pending: boolean;
  success: boolean | null;
}

export interface ConversationRound {
  id: number;
  userMessage: AgentMessage | null;
  aiIntermediate: AgentMessage[];
  entries: TerminalEntry[];
  aiFinal: AgentMessage | null;
}
