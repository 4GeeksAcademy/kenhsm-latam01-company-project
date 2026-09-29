import { authenticatedFetch, UnauthorizedError } from "@/lib/auth-fetch";
import { clearStoredToken, getStoredToken, setStoredToken } from "@/lib/auth";
import { parseJsonResponse } from "@/lib/api";

function response(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: jest.fn().mockResolvedValue(body),
  } as unknown as Response;
}

describe("token storage helpers", () => {
  beforeEach(() => localStorage.clear());

  it("stores, reads and clears a token", () => {
    expect(getStoredToken()).toBeNull();
    setStoredToken("token-123");
    expect(getStoredToken()).toBe("token-123");
    clearStoredToken();
    expect(getStoredToken()).toBeNull();
  });
});

describe("parseJsonResponse", () => {
  it("returns JSON for a successful response", async () => {
    await expect(parseJsonResponse(response(200, { ok: true }), "Nope")).resolves.toEqual({ ok: true });
  });

  it("rejects an unsuccessful response with the supplied context", async () => {
    await expect(parseJsonResponse(response(500, {}), "No se pudo cargar")).rejects.toThrow("No se pudo cargar: 500");
  });
});

describe("authenticatedFetch", () => {
  it("attaches the stored bearer token", async () => {
    setStoredToken("token-123");
    const fetchMock = jest.fn().mockResolvedValue(response(200, {}));
    global.fetch = fetchMock as unknown as typeof fetch;
    await authenticatedFetch("/private");
    expect(fetchMock).toHaveBeenCalledWith("/private", expect.objectContaining({ headers: expect.any(Headers) }));
    expect((fetchMock.mock.calls[0][1]?.headers as Headers).get("Authorization")).toBe("Bearer token-123");
  });

  it("clears the token and rejects unauthorized responses", async () => {
    setStoredToken("expired-token");
    const fetchMock = jest.fn().mockResolvedValue(response(401, {}));
    global.fetch = fetchMock as unknown as typeof fetch;
    await expect(authenticatedFetch("/private")).rejects.toBeInstanceOf(UnauthorizedError);
    expect(getStoredToken()).toBeNull();
  });
});