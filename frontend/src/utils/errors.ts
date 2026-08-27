import { AxiosError } from "axios";

/** Flattens a DRF error response ({field: [msg]} or {detail: msg}) into one readable string. */
export function extractErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof AxiosError && err.response?.data) {
    const data = err.response.data;
    if (typeof data === "string") return data;
    if (data.detail) return data.detail;

    const parts: string[] = [];
    for (const [field, messages] of Object.entries(data)) {
      const text = Array.isArray(messages) ? messages.join(" ") : String(messages);
      parts.push(field === "non_field_errors" ? text : `${field}: ${text}`);
    }
    if (parts.length) return parts.join(" | ");
  }
  return fallback;
}
