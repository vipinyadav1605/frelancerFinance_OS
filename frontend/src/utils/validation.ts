const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const GSTIN_PATTERN = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
const PAN_PATTERN = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/;

export function requiredError(value: string, label = "This field"): string {
  return value.trim() ? "" : `${label} is required.`;
}

export function emailError(value: string, required = true): string {
  if (!value.trim()) return required ? "Email is required." : "";
  return EMAIL_PATTERN.test(value.trim()) ? "" : "Enter a valid email address.";
}

export function passwordError(value: string, minLength = 8): string {
  if (!value) return "Password is required.";
  if (value.length < minLength) return `Password must be at least ${minLength} characters.`;
  return "";
}

export function confirmPasswordError(password: string, confirm: string): string {
  if (!confirm) return "Please confirm your password.";
  return password === confirm ? "" : "Passwords do not match.";
}

export function gstinError(value: string, required = false): string {
  if (!value.trim()) return required ? "GSTIN is required." : "";
  return GSTIN_PATTERN.test(value.trim().toUpperCase()) ? "" : "Not a valid GSTIN (e.g. 27AAAAA0000A1Z5).";
}

export function panError(value: string, required = false): string {
  if (!value.trim()) return required ? "PAN is required." : "";
  return PAN_PATTERN.test(value.trim().toUpperCase()) ? "" : "Not a valid PAN (e.g. ABCDE1234F).";
}

export function positiveNumberError(value: string, label = "Amount"): string {
  if (!value.trim()) return `${label} is required.`;
  const num = Number(value);
  if (Number.isNaN(num)) return `${label} must be a number.`;
  return num > 0 ? "" : `${label} must be greater than zero.`;
}

export function dateOrderError(startDate: string, endDate: string, label = "End date"): string {
  if (!startDate || !endDate) return "";
  return new Date(endDate) < new Date(startDate) ? `${label} cannot be before the start date.` : "";
}

/** Returns true if every value in the errors map is an empty string. */
export function isValid(errors: Record<string, string>): boolean {
  return Object.values(errors).every((e) => !e);
}
