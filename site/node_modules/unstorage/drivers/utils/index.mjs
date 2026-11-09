export function defineDriver(factory) {
  return factory;
}
export function normalizeKey(key, sep = ":") {
  if (!key) {
    return "";
  }
  return key.replace(/[:/\\]/g, sep).replace(/^[:/\\]|[:/\\]$/g, "");
}
export function joinKeys(...keys) {
  return keys.map((key) => normalizeKey(key)).filter(Boolean).join(":");
}
export function encodeURLSegment(driver, segment, key = segment) {
  if (!segment || segment === "." || segment === "..") {
    throw createError(
      driver,
      `Invalid key: ${JSON.stringify(key)}. Empty, "." and ".." segments are not allowed`
    );
  }
  try {
    return encodeURIComponent(segment);
  } catch {
    throw createError(
      driver,
      `Invalid key: ${JSON.stringify(key)}. It contains malformed unicode`
    );
  }
}
export function encodeURLKey(driver, key) {
  return (key || "").split(/[:/\\]/).filter(Boolean).map((segment) => encodeURLSegment(driver, segment, key)).join("/");
}
export function assertURLPathKey(driver, key) {
  const invalid = (reason) => createError(driver, `Invalid key: ${JSON.stringify(key)}. ${reason}`);
  if (!key) {
    throw invalid("Empty keys are not allowed");
  }
  if (/[?#]/.test(key)) {
    throw invalid(`"?" and "#" are not allowed`);
  }
  if (/[\u0000-\u001F]|^ | $/.test(key)) {
    throw invalid(
      "Control characters and leading/trailing spaces are not allowed"
    );
  }
  const hasDotSegment = key.split(/[/\\]|%2f|%5c/i).some((segment) => {
    segment = segment.replace(/%2e/gi, ".");
    return segment === "." || segment === "..";
  });
  if (hasDotSegment) {
    throw invalid(`"." and ".." segments are not allowed`);
  }
  return key;
}
export function escapeRedisGlob(pattern) {
  return pattern.replace(/[*?[\]\\]/g, String.raw`\$&`);
}
export function createError(driver, message, opts) {
  const err = new Error(`[unstorage] [${driver}] ${message}`, opts);
  if (Error.captureStackTrace) {
    Error.captureStackTrace(err, createError);
  }
  return err;
}
export function createRequiredError(driver, name) {
  if (Array.isArray(name)) {
    return createError(
      driver,
      `Missing some of the required options ${name.map((n) => "`" + n + "`").join(", ")}`
    );
  }
  return createError(driver, `Missing required option \`${name}\`.`);
}
