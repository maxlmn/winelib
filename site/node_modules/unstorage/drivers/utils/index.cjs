"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.assertURLPathKey = assertURLPathKey;
exports.createError = createError;
exports.createRequiredError = createRequiredError;
exports.defineDriver = defineDriver;
exports.encodeURLKey = encodeURLKey;
exports.encodeURLSegment = encodeURLSegment;
exports.escapeRedisGlob = escapeRedisGlob;
exports.joinKeys = joinKeys;
exports.normalizeKey = normalizeKey;
function defineDriver(factory) {
  return factory;
}
function normalizeKey(key, sep = ":") {
  if (!key) {
    return "";
  }
  return key.replace(/[:/\\]/g, sep).replace(/^[:/\\]|[:/\\]$/g, "");
}
function joinKeys(...keys) {
  return keys.map(key => normalizeKey(key)).filter(Boolean).join(":");
}
function encodeURLSegment(driver, segment, key = segment) {
  if (!segment || segment === "." || segment === "..") {
    throw createError(driver, `Invalid key: ${JSON.stringify(key)}. Empty, "." and ".." segments are not allowed`);
  }
  try {
    return encodeURIComponent(segment);
  } catch {
    throw createError(driver, `Invalid key: ${JSON.stringify(key)}. It contains malformed unicode`);
  }
}
function encodeURLKey(driver, key) {
  return (key || "").split(/[:/\\]/).filter(Boolean).map(segment => encodeURLSegment(driver, segment, key)).join("/");
}
function assertURLPathKey(driver, key) {
  const invalid = reason => createError(driver, `Invalid key: ${JSON.stringify(key)}. ${reason}`);
  if (!key) {
    throw invalid("Empty keys are not allowed");
  }
  if (/[?#]/.test(key)) {
    throw invalid(`"?" and "#" are not allowed`);
  }
  if (/[\u0000-\u001F]|^ | $/.test(key)) {
    throw invalid("Control characters and leading/trailing spaces are not allowed");
  }
  const hasDotSegment = key.split(/[/\\]|%2f|%5c/i).some(segment => {
    segment = segment.replace(/%2e/gi, ".");
    return segment === "." || segment === "..";
  });
  if (hasDotSegment) {
    throw invalid(`"." and ".." segments are not allowed`);
  }
  return key;
}
function escapeRedisGlob(pattern) {
  return pattern.replace(/[*?[\]\\]/g, String.raw`\$&`);
}
function createError(driver, message, opts) {
  const err = new Error(`[unstorage] [${driver}] ${message}`, opts);
  if (Error.captureStackTrace) {
    Error.captureStackTrace(err, createError);
  }
  return err;
}
function createRequiredError(driver, name) {
  if (Array.isArray(name)) {
    return createError(driver, `Missing some of the required options ${name.map(n => "`" + n + "`").join(", ")}`);
  }
  return createError(driver, `Missing required option \`${name}\`.`);
}