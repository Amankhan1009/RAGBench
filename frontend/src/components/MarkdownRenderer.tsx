"use client";

import React, { useMemo } from "react";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/**
 * Format inline markdown tokens: **bold**, *italic*, `code`, and [links](url).
 */
function renderInlineFormatted(text: string): React.ReactNode[] {
  // Regex to match **bold**, `code`, *italic*, and standard text
  const tokens: React.ReactNode[] = [];
  const regex = /(\*\*.*?\*\*|`.*?`|\*.*?\*)/g;
  const parts = text.split(regex);

  parts.forEach((part, idx) => {
    if (!part) return;

    if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
      tokens.push(
        <strong key={idx} className="text-slate-100 font-semibold">
          {part.slice(2, -2)}
        </strong>
      );
    } else if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
      tokens.push(
        <code
          key={idx}
          className="bg-slate-800/90 text-indigo-300 px-1.5 py-0.5 rounded text-[11px] font-mono border border-slate-700/60"
        >
          {part.slice(1, -1)}
        </code>
      );
    } else if (part.startsWith("*") && part.endsWith("*") && part.length >= 2) {
      tokens.push(
        <em key={idx} className="text-slate-300 italic">
          {part.slice(1, -1)}
        </em>
      );
    } else {
      tokens.push(<React.Fragment key={idx}>{part}</React.Fragment>);
    }
  });

  return tokens;
}

export default function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  const renderedElements = useMemo(() => {
    if (!content) return null;

    const lines = content.split("\n");
    const elements: React.ReactNode[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];
      const trimmed = line.trim();

      // 1. Code Blocks (``` ... ```)
      if (trimmed.startsWith("```")) {
        const lang = trimmed.slice(3).trim();
        const codeLines: string[] = [];
        i++;
        while (i < lines.length && !lines[i].trim().startsWith("```")) {
          codeLines.push(lines[i]);
          i++;
        }
        i++; // skip closing ```
        elements.push(
          <div key={`code-${i}`} className="my-3 rounded-lg overflow-hidden border border-slate-800 bg-slate-950">
            {lang && (
              <div className="bg-slate-900 px-3 py-1 text-[10px] font-mono text-slate-400 border-b border-slate-800 uppercase tracking-wider">
                {lang}
              </div>
            )}
            <pre className="p-3 text-xs font-mono text-indigo-300 overflow-x-auto leading-relaxed">
              {codeLines.join("\n")}
            </pre>
          </div>
        );
        continue;
      }

      // 2. Markdown Tables (| Col 1 | Col 2 |)
      if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
        const tableLines: string[] = [];
        while (i < lines.length && lines[i].trim().startsWith("|") && lines[i].trim().endsWith("|")) {
          tableLines.push(lines[i].trim());
          i++;
        }

        if (tableLines.length >= 2) {
          const headerCells = tableLines[0]
            .split("|")
            .map((c) => c.trim())
            .filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);

          // Find separator line index (e.g. |---|---|)
          let hasSeparator = false;
          let rowStartIdx = 1;
          if (tableLines[1].replace(/[-| :]/g, "") === "") {
            hasSeparator = true;
            rowStartIdx = 2;
          }

          const bodyRows = tableLines.slice(rowStartIdx).map((rowLine) => {
            return rowLine
              .split("|")
              .map((c) => c.trim())
              .filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
          });

          elements.push(
            <div key={`table-${i}`} className="my-4 overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/60 shadow-inner">
              <table className="w-full text-xs text-left border-collapse">
                {hasSeparator && (
                  <thead>
                    <tr className="bg-slate-800/90 text-indigo-300 font-semibold border-b border-slate-700/80">
                      {headerCells.map((h, hIdx) => (
                        <th key={hIdx} className="p-3 font-medium">
                          {renderInlineFormatted(h)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                )}
                <tbody className="divide-y divide-slate-800/60">
                  {bodyRows.map((row, rIdx) => (
                    <tr
                      key={rIdx}
                      className={rIdx % 2 === 0 ? "bg-slate-900/40 hover:bg-slate-850/60 transition" : "bg-slate-950/40 hover:bg-slate-850/60 transition"}
                    >
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className="p-3 text-slate-300 leading-relaxed">
                          {renderInlineFormatted(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
          continue;
        }
      }

      // 3. Headers (#, ##, ###)
      if (trimmed.startsWith("# ")) {
        elements.push(
          <h1 key={`h1-${i}`} className="text-lg font-bold text-slate-100 mt-5 mb-2 pb-1 border-b border-slate-800 flex items-center gap-2">
            <span>🔹</span>
            {renderInlineFormatted(trimmed.slice(2))}
          </h1>
        );
        i++;
        continue;
      }

      if (trimmed.startsWith("## ")) {
        elements.push(
          <h2 key={`h2-${i}`} className="text-base font-bold text-indigo-300 mt-5 mb-2 pb-1 border-b border-slate-800/70 flex items-center gap-2">
            <span className="text-indigo-400 text-sm">▶</span>
            {renderInlineFormatted(trimmed.slice(3))}
          </h2>
        );
        i++;
        continue;
      }

      if (trimmed.startsWith("### ")) {
        elements.push(
          <h3 key={`h3-${i}`} className="text-sm font-semibold text-slate-200 mt-4 mb-1">
            {renderInlineFormatted(trimmed.slice(4))}
          </h3>
        );
        i++;
        continue;
      }

      // 4. Horizontal Rules (--- or ***)
      if (trimmed === "---" || trimmed === "***" || trimmed === "___") {
        elements.push(<hr key={`hr-${i}`} className="border-slate-800 my-4" />);
        i++;
        continue;
      }

      // 5. Bullet Lists (- Item or * Item)
      if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
        const listItems: string[] = [];
        while (i < lines.length && (lines[i].trim().startsWith("- ") || lines[i].trim().startsWith("* "))) {
          listItems.push(lines[i].trim().slice(2));
          i++;
        }
        elements.push(
          <ul key={`ul-${i}`} className="my-2 space-y-1.5 pl-2 text-xs text-slate-300">
            {listItems.map((item, lIdx) => (
              <li key={lIdx} className="flex items-start gap-2">
                <span className="text-indigo-400 mt-0.5">•</span>
                <span className="leading-relaxed">{renderInlineFormatted(item)}</span>
              </li>
            ))}
          </ul>
        );
        continue;
      }

      // 6. Numbered Lists (1. Item)
      if (/^\d+\.\s/.test(trimmed)) {
        const numItems: { num: string; text: string }[] = [];
        while (i < lines.length && /^\d+\.\s/.test(lines[i].trim())) {
          const match = lines[i].trim().match(/^(\d+\.)\s(.*)$/);
          if (match) {
            numItems.push({ num: match[1], text: match[2] });
          }
          i++;
        }
        elements.push(
          <ol key={`ol-${i}`} className="my-2 space-y-1.5 pl-2 text-xs text-slate-300">
            {numItems.map((item, nIdx) => (
              <li key={nIdx} className="flex items-start gap-2">
                <span className="text-indigo-400 font-mono text-[11px] font-semibold">{item.num}</span>
                <span className="leading-relaxed">{renderInlineFormatted(item.text)}</span>
              </li>
            ))}
          </ol>
        );
        continue;
      }

      // 7. Empty line
      if (trimmed === "") {
        i++;
        continue;
      }

      // 8. Regular Paragraph
      elements.push(
        <p key={`p-${i}`} className="text-xs text-slate-200 leading-relaxed my-1.5">
          {renderInlineFormatted(line)}
        </p>
      );
      i++;
    }

    return elements;
  }, [content]);

  return <div className={`space-y-1 text-slate-200 ${className}`}>{renderedElements}</div>;
}
