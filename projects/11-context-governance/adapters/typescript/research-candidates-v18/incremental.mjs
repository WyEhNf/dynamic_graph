// Virtual-source compiler API worker. Source input is parsed, never executed.
import ts from 'typescript';
import path from 'node:path';
import readline from 'node:readline';
import {performance} from 'node:perf_hooks';

const normalize = value => path.posix.normalize(value.replaceAll('\\', '/'));
const virtualName = value => normalize('/snapshot/' + value);
let previousKey, previousResult;
let previousCompileSession;

function analyze(request) {
  const started = performance.now();
  if (!request.files || typeof request.files !== 'object' || Array.isArray(request.files)) throw Error('files must be a filename-to-source mapping');
  const files = new Map();
  for (const [name, text] of Object.entries(request.files)) {
    if (typeof text !== 'string' || name.startsWith('/') || name.includes('\\') || name.includes(':') || name.includes('\u0000') || normalize(name) !== name || name.startsWith('../')) throw Error('source paths must be normalized relative paths');
    if (!/\.(?:ts|tsx|ets|mts|cts)$/.test(name)) throw Error('unsupported source extension');
    files.set(virtualName(name), text);
  }
  if (request.pinned_files !== undefined && !Array.isArray(request.pinned_files)) throw Error('pinned_files must be an array');
  const pins = new Set(request.pinned_files ?? []);
  for (const name of pins) if (!files.has(virtualName(name))) throw Error('pinned source missing');
  const sourceFiles = new Map();
  const imports = new Map();
  const warnings = [];
  let fallback = false;
  function resolve(specifier, containing) {
    if (!specifier.startsWith('.')) return undefined;
    const base = normalize(path.posix.join(path.posix.dirname(containing), specifier));
    const candidates = [base, ...['.ts','.tsx','.ets','.mts','.cts','.d.ts','/index.ts','/index.tsx'].map(extension => base + extension)];
    if (/\.(?:js|jsx|mjs|cjs)$/.test(base)) {
      const stem = base.replace(/\.(?:js|jsx|mjs|cjs)$/, '');
      candidates.push(...['.ts','.tsx','.mts','.cts','.d.ts'].map(extension => stem + extension));
    }
    return candidates.find(candidate => files.has(candidate));
  }
  const host = {
    getSourceFile(name, languageVersion, onError, shouldCreateNewSourceFile) {
      name = normalize(name);
      if (!files.has(name)) return undefined;
      if (!sourceFiles.has(name)) {
        const prior = previousCompileSession;
        const reused = !shouldCreateNewSourceFile && prior?.files.get(name) === files.get(name) ? prior.sourceFiles.get(name) : undefined;
        sourceFiles.set(name, reused ?? ts.createSourceFile(name, files.get(name), languageVersion, true, name.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS));
      }
      return sourceFiles.get(name);
    },
    hasInvalidatedResolutions: () => true, // Resolve every import against the new virtual snapshot.
    getDefaultLibFileName: () => '/snapshot/lib.d.ts',
    writeFile: () => {throw Error('worker must not emit files');},
    getCurrentDirectory: () => '/snapshot', getDirectories: () => [],
    directoryExists: name => [...files.keys()].some(file => file.startsWith(normalize(name).replace(/\/$/, '') + '/')),
    fileExists: name => files.has(normalize(name)), readFile: name => files.get(normalize(name)),
    getCanonicalFileName: name => normalize(name), useCaseSensitiveFileNames: () => true,
    getNewLine: () => '\n',
    resolveModuleNames(names, containing) {
      return names.map(name => {
        const resolved = resolve(name, containing);
        if (resolved) return {resolvedFileName: resolved, extension: resolved.endsWith('.tsx') ? ts.Extension.Tsx : ts.Extension.Ts};
        return undefined;
      });
    }
  };
  const program = ts.createProgram([...files.keys()], {target: ts.ScriptTarget.ESNext, module: ts.ModuleKind.ESNext,
    noLib: true, noEmit: true, allowNonTsExtensions: true, moduleResolution: ts.ModuleResolutionKind.Bundler}, host, previousCompileSession?.program);
  for (const filename of files.keys()) sourceFiles.set(filename, program.getSourceFile(filename));
  const checker = program.getTypeChecker();
  function harmlessTypeModule(filename) {
    const source = program.getSourceFile(filename);
    return source && source.statements.every(statement => ts.isInterfaceDeclaration(statement) || ts.isTypeAliasDeclaration(statement)
      || ts.isFunctionDeclaration(statement) || (ts.isImportDeclaration(statement) && statement.importClause?.isTypeOnly)
      || (ts.isExportDeclaration(statement) && statement.isTypeOnly));
  }
  const items = [], statementIds = new Map(), fileIds = new Map(), initializers = new Map();
  for (const [filename, text] of files) {
    const source = program.getSourceFile(filename);
    if (!source) throw Error('compiler omitted source: ' + filename);
    const relative = filename.slice('/snapshot/'.length);
    const errors = source.parseDiagnostics.map(diagnostic => ({code: diagnostic.code, offset: diagnostic.start,
      message: ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n')}));
    if (errors.length) {fallback = true; warnings.push({file: relative, kind: 'syntax_fallback', diagnostics: errors});}
    const ids = [], initialization = [];
    if (pins.has(relative) || errors.length || !source.statements.length) {
      items.push({id: relative, kind: 'code', text, protected: pins.has(relative), utility: 0});
      ids.push(relative);
      for (const statement of source.statements) statementIds.set(statement, relative);
      initialization.push(relative);
    } else {
      for (let index = 0; index < source.statements.length; index++) {
        const statement = source.statements[index];
        const start = statement.getFullStart();
        const end = index + 1 === source.statements.length ? text.length : statement.end;
        const id = relative + ':' + start + '-' + end;
        items.push({id, kind: 'code', text: text.slice(start, end), protected: false, utility: 0});
        ids.push(id); statementIds.set(statement, id);
        // Conservatively keep executable initialization, declarations with
        // possible initialization, classes/static blocks, and module exports.
        if (!ts.isFunctionDeclaration(statement) && !ts.isInterfaceDeclaration(statement) && !ts.isTypeAliasDeclaration(statement)) initialization.push(id);
      }
    }
    fileIds.set(filename, ids); initializers.set(filename, initialization);
    const moduleImports = [];
    const visit = node => {
      let specifier;
      if ((ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) && node.moduleSpecifier) specifier = node.moduleSpecifier;
      if (ts.isImportEqualsDeclaration(node) && ts.isExternalModuleReference(node.moduleReference)) specifier = node.moduleReference.expression;
      if (ts.isImportTypeNode(node) && ts.isLiteralTypeNode(node.argument)) specifier = node.argument.literal;
      if (ts.isCallExpression(node) && (node.expression.kind === ts.SyntaxKind.ImportKeyword || (ts.isIdentifier(node.expression) && ['require','eval'].includes(node.expression.text)))) {
        if (node.expression.kind === ts.SyntaxKind.ImportKeyword || node.expression.text === 'require') specifier = node.arguments[0];
        else {fallback = true; warnings.push({file: relative, kind: 'eval_fallback'});}
      }
      if (specifier) {
        if (ts.isStringLiteralLike(specifier)) {
          const target = resolve(specifier.text, filename);
          if (target) {
            const typeOnly = (ts.isImportDeclaration(node) && node.importClause?.isTypeOnly && !ts.isNamespaceImport(node.importClause.namedBindings ?? node))
              || (ts.isExportDeclaration(node) && node.isTypeOnly && node.exportClause && ts.isNamedExports(node.exportClause));
            moduleImports.push({target, full: !(typeOnly && harmlessTypeModule(target))});
          }
          else {
            warnings.push({file: relative, kind: specifier.text.startsWith('.') ? 'unresolved_relative_module' : 'external_module', module: specifier.text});
            if (specifier.text.startsWith('.')) fallback = true;
          }
        } else {fallback = true; warnings.push({file: relative, kind: 'dynamic_module_fallback'});}
      }
      ts.forEachChild(node, visit);
    };
    visit(source); imports.set(filename, moduleImports);
  }
  function declarationId(declaration) {
    let node = declaration;
    while (node && !statementIds.has(node)) node = node.parent;
    return node ? statementIds.get(node) : undefined;
  }
  const dependencies = Object.fromEntries(items.map(item => [item.id, new Set()]));
  const globals = [...sourceFiles].filter(([name, source]) => !ts.isExternalModule(source)).flatMap(([name]) => initializers.get(name) ?? []);
  for (const [filename, source] of sourceFiles) {
    for (const statement of source.statements) {
      const id = statementIds.get(statement); if (!id) continue;
      const required = dependencies[id];
      for (const dependency of [...initializers.get(filename), ...globals]) required.add(dependency);
      for (const imported of imports.get(filename)) if (imported.full) for (const dependency of fileIds.get(imported.target)) required.add(dependency);
      const visit = node => {
        if (ts.isIdentifier(node)) {
          let symbol = checker.getSymbolAtLocation(node);
          for (const declaration of symbol?.declarations ?? []) {
            const dependency = declarationId(declaration); if (dependency) required.add(dependency);
          }
          if (symbol && (symbol.flags & ts.SymbolFlags.Alias)) {
            symbol = checker.getAliasedSymbol(symbol);
            for (const declaration of symbol?.declarations ?? []) {
              const dependency = declarationId(declaration); if (dependency) required.add(dependency);
            }
          }
        }
        ts.forEachChild(node, visit);
      };
      visit(statement);
    }
  }
  if (fallback) for (const required of Object.values(dependencies)) for (const item of items) required.add(item.id);
  const result = {items, dependencies: Object.fromEntries(Object.entries(dependencies).map(([id, required]) => [id, [...required].filter(x => x !== id).sort()])),
    warnings, conservative_full_project_fallback: fallback, compiler_version: ts.version,
    scope: 'Compiler AST/symbol references plus conservative full imported modules and initialization. External packages, path aliases, reflection and full ArkTS grammar require separate integration.',
    analysis_ms: performance.now() - started, cache_hit: false, worker_resident_bytes: process.memoryUsage().rss};
  previousCompileSession = {files, sourceFiles, program};
  return result;
}

const lines = readline.createInterface({input: process.stdin, crlfDelay: Infinity});
for await (const line of lines) {
  try {
    const request = JSON.parse(line);
    const key = JSON.stringify({files: request.files, pinned_files: request.pinned_files ?? []});
    const cacheEnabled = request.use_cache !== false;
    const lookupStarted = performance.now();
    let result;
    if (cacheEnabled && key === previousKey) result = {...previousResult, cache_hit: true, analysis_ms: performance.now() - lookupStarted, worker_resident_bytes: process.memoryUsage().rss};
    else {
      result = analyze(request);
      if (cacheEnabled) {previousKey = key; previousResult = result;}
    }
    console.log(JSON.stringify({ok: true, result}));
  }
  catch (error) {console.log(JSON.stringify({ok: false, error: String(error.message)}));}
}
