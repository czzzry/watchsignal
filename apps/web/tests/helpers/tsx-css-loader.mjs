import { access, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import ts from "../../node_modules/typescript/lib/typescript.js";

export async function resolve(specifier, context, nextResolve) {
  if (specifier.startsWith(".") && context.parentURL) {
    const baseUrl = new URL(specifier, context.parentURL);
    if (!/\.[a-z]+$/i.test(baseUrl.pathname)) {
      for (const extension of [".ts", ".tsx"]) {
        const candidate = new URL(`${baseUrl.href}${extension}`);
        try {
          await access(fileURLToPath(candidate));
          return { url: candidate.href, shortCircuit: true };
        } catch {
          // Try the next supported source extension.
        }
      }
    }
  }

  return nextResolve(specifier, context);
}

export async function load(url, context, nextLoad) {
  if (url.endsWith(".css")) {
    return {
      format: "module",
      source: "export default {};",
      shortCircuit: true,
    };
  }

  if (url.endsWith(".ts") || url.endsWith(".tsx")) {
    const source = await readFile(fileURLToPath(url), "utf8");
    const output = ts.transpileModule(source, {
      fileName: fileURLToPath(url),
      compilerOptions: {
        jsx: ts.JsxEmit.ReactJSX,
        module: ts.ModuleKind.ESNext,
        target: ts.ScriptTarget.ES2022,
        verbatimModuleSyntax: true,
      },
    });
    return { format: "module", source: output.outputText, shortCircuit: true };
  }

  return nextLoad(url, context);
}
